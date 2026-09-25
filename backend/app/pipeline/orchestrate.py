"""Pipeline orchestration.

Runs the INGEST → NORMALIZE → COMPARE → SCORE → SELECT → PERSIST cycle for all
providers. Each provider is isolated: a failed provider never blocks others.

The agent investigation step is intentionally separate (see app.agent) so the
core pipeline remains fully functional with no LLM configured.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import PROVIDERS
from app.ingest.base import FetchResult, ProviderUnavailable
from app.ingest.eonet import EonetProvider
from app.ingest.firms import FirmsProvider
from app.ingest.usgs import UsgsProvider
from app.models import (
    Event,
    EventSnapshot,
    FireCluster,
    PipelineRun,
    ProviderRun,
    SourceRecord,
)
from app.observability import span
from app.pipeline.clustering import cluster_fire_detections, haversine_km
from app.pipeline.normalize import NormalizedEvent, normalize_eonet, normalize_usgs
from app.pipeline.scoring import score_event
from app.pipeline.state import detect_change
from app.serialize import json_safe

logger = logging.getLogger("planet.pipeline")


def _norm_to_event_dict(n: NormalizedEvent, change_type: str, score: float, tier: str) -> dict[str, Any]:
    return {
        "source": n.source,
        "source_id": n.source_id,
        "category": n.category,
        "subtype": n.subtype,
        "title": n.title,
        "latitude": n.latitude,
        "longitude": n.longitude,
        "geometry": json_safe(n.geometry),
        "first_observed_at": n.first_observed_at,
        "last_observed_at": n.last_observed_at,
        "status": n.status,
        "raw_severity": json_safe(n.raw_severity),
        "confidence": n.confidence,
        "metrics": json_safe(n.metrics),
        "source_url": n.source_url,
        "raw_payload": json_safe(n.raw_payload),
        "significance_score": score,
        "significance_tier": tier,
        "change_type": change_type,
    }


async def _upsert_event(
    session: AsyncSession,
    n: NormalizedEvent,
    score: float,
    tier: str,
) -> tuple[Event, str]:
    """Create or update the event row and return (event, change_type)."""
    existing = await session.execute(select(Event).where(Event.source == n.source, Event.source_id == n.source_id))
    event = existing.scalar_one_or_none()

    if event is None:
        change_type = "NEW"
        data = _norm_to_event_dict(n, change_type, score, tier)
        event = Event(**data)
        session.add(event)
        await session.flush()
    else:
        prior = {
            "status": event.status,
            "significance_score": event.significance_score,
            "significance_tier": event.significance_tier,
            "metrics": event.metrics,
            "geometry": event.geometry,
            "last_observed_at": event.last_observed_at,
            "title": event.title,
        }
        new_state = {
            "status": n.status,
            "significance_score": score,
            "significance_tier": tier,
            "metrics": n.metrics,
            "geometry": n.geometry,
            "last_observed_at": n.last_observed_at,
            "title": n.title,
        }
        change_type = detect_change(prior, new_state)

        event.title = n.title
        event.subtype = n.subtype
        event.latitude = n.latitude
        event.longitude = n.longitude
        event.geometry = json_safe(n.geometry)
        event.last_observed_at = n.last_observed_at
        event.status = n.status
        event.raw_severity = json_safe(n.raw_severity)
        event.significance_score = score
        event.significance_tier = tier
        event.confidence = n.confidence
        event.metrics = json_safe(n.metrics)
        event.source_url = n.source_url
        event.raw_payload = json_safe(n.raw_payload)
        event.change_type = change_type

    # Snapshot the state for history/audit.
    session.add(
        EventSnapshot(
            event_id=event.id,
            significance_score=score,
            significance_tier=tier,
            change_type=change_type,
            status=n.status,
            geometry=json_safe(n.geometry),
            metrics=json_safe(n.metrics),
            last_observed_at=n.last_observed_at,
        )
    )
    return event, change_type


async def _save_source_record(
    session: AsyncSession, source: str, source_id: str, payload: dict, event_id: str | None
) -> None:
    session.add(SourceRecord(source=source, source_id=source_id, payload=json_safe(payload), event_id=event_id))


async def ingest_usgs(session: AsyncSession, provider: UsgsProvider) -> dict[str, int]:
    stats = {"fetched": 0, "created": 0, "updated": 0, "escalated": 0}
    result: FetchResult = await provider.fetch()
    stats["fetched"] = len(result.records)
    for record in result.records:
        normalized = normalize_usgs(record)
        if normalized is None:
            continue
        score, tier = _score(normalized)
        event, change = await _upsert_event(session, normalized, score, tier)
        if change == "NEW":
            stats["created"] += 1
        elif change == "ESCALATING":
            stats["escalated"] += 1
        else:
            stats["updated"] += 1
        await _save_source_record(session, "usgs", normalized.source_id, record, event.id)
    return stats


async def ingest_eonet(session: AsyncSession, provider: EonetProvider) -> dict[str, int]:
    stats = {"fetched": 0, "created": 0, "updated": 0, "escalated": 0}
    result: FetchResult = await provider.fetch()
    stats["fetched"] = len(result.records)
    for record in result.records:
        normalized = normalize_eonet(record)
        if normalized is None:
            continue
        score, tier = _score(normalized)
        event, change = await _upsert_event(session, normalized, score, tier)
        if change == "NEW":
            stats["created"] += 1
        elif change == "ESCALATING":
            stats["escalated"] += 1
        else:
            stats["updated"] += 1
        await _save_source_record(session, "eonet", normalized.source_id, record, event.id)
    return stats


async def ingest_firms(session: AsyncSession, provider: FirmsProvider) -> dict[str, int]:
    """Fetch FIRMS detections, cluster, and upsert clusters as wildfire events."""
    stats = {"fetched": 0, "clusters": 0, "created": 0, "updated": 0, "escalated": 0}
    result: FetchResult = await provider.fetch()
    detections = result.records
    stats["fetched"] = len(detections)

    clusters = cluster_fire_detections(detections, radius_km=settings.fire_cluster_radius_km)
    stats["clusters"] = len(clusters)

    existing_clusters = (await session.execute(select(FireCluster))).scalars().all()

    for cluster in clusters:
        matched = _match_existing_cluster(cluster, existing_clusters, settings.fire_cluster_radius_km)
        if matched is None:
            # New cluster -> new event
            event = await _create_fire_event(session, cluster, growth_ratio=1.0)
            await _save_fire_cluster(session, cluster, event.id)
            stats["created"] += 1
        else:
            growth_ratio = _growth_ratio(cluster, matched)
            event = await _update_fire_event(session, matched.event_id, cluster, growth_ratio)
            await _update_fire_cluster(session, matched, cluster)
            if growth_ratio >= 1.5:
                stats["escalated"] += 1
            else:
                stats["updated"] += 1
    return stats


def _score(n: NormalizedEvent) -> tuple[float, str]:
    from app.pipeline.scoring import score_and_tier

    return score_and_tier(n.category, n.metrics, n.raw_severity)


def _match_existing_cluster(
    cluster: dict[str, Any], existing: list[FireCluster], radius_km: float
) -> FireCluster | None:
    for ex in existing:
        if (
            haversine_km(
                cluster["centroid_lat"],
                cluster["centroid_lon"],
                ex.centroid_lat,
                ex.centroid_lon,
            )
            <= radius_km * 2
        ):
            return ex
    return None


def _growth_ratio(cluster: dict[str, Any], existing: FireCluster) -> float:
    if existing.detection_count <= 0:
        return 1.0
    return cluster["detection_count"] / existing.detection_count


async def _create_fire_event(session: AsyncSession, cluster: dict[str, Any], growth_ratio: float) -> Event:
    metrics = {
        "detection_count": cluster["detection_count"],
        "mean_frp": cluster["mean_frp"],
        "max_frp": cluster["max_frp"],
        "confidence": cluster["confidence"],
        "confidence_distribution": cluster["confidence_distribution"],
        "growth_ratio": growth_ratio,
    }
    n = NormalizedEvent(
        source="firms",
        source_id=cluster["cluster_key"],
        category="wildfire",
        subtype="thermal-anomaly-cluster",
        title=_fire_title(cluster),
        latitude=cluster["centroid_lat"],
        longitude=cluster["centroid_lon"],
        geometry=cluster["geometry"],
        first_observed_at=cluster["first_detected_at"] or datetime.now(UTC),
        last_observed_at=cluster["last_detected_at"] or datetime.now(UTC),
        status="open",
        raw_severity={"max_frp": cluster["max_frp"], "detections": cluster["detection_count"]},
        confidence=cluster["confidence"],
        metrics=metrics,
        source_url=None,
        raw_payload=cluster,
    )
    score, tier = _score(n)
    event, _ = await _upsert_event(session, n, score, tier)
    return event


async def _update_fire_event(
    session: AsyncSession, event_id: str | None, cluster: dict[str, Any], growth_ratio: float
) -> Event | None:
    if event_id is None:
        return None
    event = await session.get(Event, event_id)
    if event is None:
        return None
    prior = {
        "status": event.status,
        "significance_score": event.significance_score,
        "significance_tier": event.significance_tier,
        "metrics": event.metrics,
        "geometry": event.geometry,
        "last_observed_at": event.last_observed_at,
        "title": event.title,
    }
    metrics = {
        "detection_count": cluster["detection_count"],
        "mean_frp": cluster["mean_frp"],
        "max_frp": cluster["max_frp"],
        "confidence": cluster["confidence"],
        "confidence_distribution": cluster["confidence_distribution"],
        "growth_ratio": growth_ratio,
    }
    event.metrics = metrics
    event.geometry = cluster["geometry"]
    event.latitude = cluster["centroid_lat"]
    event.longitude = cluster["centroid_lon"]
    event.last_observed_at = cluster["last_detected_at"] or event.last_observed_at
    event.raw_severity = {"max_frp": cluster["max_frp"], "detections": cluster["detection_count"]}
    score = score_event("wildfire", metrics)
    from app.constants import tier_for_score

    tier = tier_for_score(score)
    new_state = {
        "status": event.status,
        "significance_score": score,
        "significance_tier": tier,
        "metrics": metrics,
        "geometry": cluster["geometry"],
        "last_observed_at": event.last_observed_at,
        "title": event.title,
    }
    change_type = detect_change(prior, new_state)
    event.significance_score = score
    event.significance_tier = tier
    event.change_type = change_type
    event.updated_at = datetime.now(UTC)
    session.add(
        EventSnapshot(
            event_id=event.id,
            significance_score=score,
            significance_tier=tier,
            change_type=change_type,
            status=event.status,
            geometry=cluster["geometry"],
            metrics=metrics,
            last_observed_at=event.last_observed_at,
        )
    )
    return event


async def _save_fire_cluster(session: AsyncSession, cluster: dict[str, Any], event_id: str | None) -> None:
    session.add(
        FireCluster(
            cluster_key=cluster["cluster_key"],
            centroid_lat=cluster["centroid_lat"],
            centroid_lon=cluster["centroid_lon"],
            geometry=cluster["geometry"],
            bbox=cluster["bbox"],
            detection_count=cluster["detection_count"],
            mean_frp=cluster["mean_frp"],
            max_frp=cluster["max_frp"],
            confidence_distribution=cluster["confidence_distribution"],
            first_detected_at=cluster["first_detected_at"] or datetime.now(UTC),
            last_detected_at=cluster["last_detected_at"] or datetime.now(UTC),
            event_id=event_id,
        )
    )


async def _update_fire_cluster(session: AsyncSession, existing: FireCluster, cluster: dict[str, Any]) -> None:
    existing.centroid_lat = cluster["centroid_lat"]
    existing.centroid_lon = cluster["centroid_lon"]
    existing.geometry = cluster["geometry"]
    existing.bbox = cluster["bbox"]
    existing.detection_count = cluster["detection_count"]
    existing.mean_frp = cluster["mean_frp"]
    existing.max_frp = cluster["max_frp"]
    existing.confidence_distribution = cluster["confidence_distribution"]
    existing.last_detected_at = cluster["last_detected_at"] or existing.last_detected_at
    existing.updated_at = datetime.now(UTC)


def _fire_title(cluster: dict[str, Any]) -> str:
    return (
        f"Thermal anomaly cluster ({cluster['detection_count']} detections) "
        f"near {round(cluster['centroid_lat'], 2)}, {round(cluster['centroid_lon'], 2)}"
    )


async def run_provider(session: AsyncSession, provider_name: str) -> dict[str, Any]:
    """Run a single provider with isolation and tracing. Returns stats."""
    provider = None
    try:
        with span(f"provider.{provider_name}"):
            if provider_name == "usgs":
                provider = UsgsProvider()
                stats = await ingest_usgs(session, provider)
            elif provider_name == "eonet":
                provider = EonetProvider()
                stats = await ingest_eonet(session, provider)
            elif provider_name == "firms":
                provider = FirmsProvider()
                stats = await ingest_firms(session, provider)
            else:
                raise ValueError(f"unknown provider {provider_name}")
            stats["status"] = "succeeded"
            return stats
    except ProviderUnavailable as exc:
        logger.warning("provider %s unavailable: %s", provider_name, exc)
        return {"status": "failed", "error": str(exc), "fetched": 0}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("provider %s failed: %s", provider_name, exc)
        return {"status": "failed", "error": str(exc), "fetched": 0}
    finally:
        if provider is not None:
            await provider.close()


async def run_pipeline(session: AsyncSession, providers: list[str] | None = None) -> PipelineRun:
    """Run the full ingestion pipeline for the given (or all) providers."""
    providers = providers or list(PROVIDERS)
    run = PipelineRun(status="running", started_at=datetime.now(UTC), stats={})
    session.add(run)
    await session.flush()

    totals: dict[str, Any] = {"events_created": 0, "events_updated": 0, "events_escalated": 0}
    for provider_name in providers:
        started = time.perf_counter()
        stats = await run_provider(session, provider_name)
        elapsed = time.perf_counter() - started
        await session.flush()
        session.add(
            ProviderRun(
                pipeline_run_id=run.id,
                provider=provider_name,
                status=stats.get("status", "failed"),
                records_fetched=stats.get("fetched", 0),
                events_created=stats.get("created", 0),
                events_updated=stats.get("updated", 0),
                error=stats.get("error"),
            )
        )
        totals["events_created"] += stats.get("created", 0)
        totals["events_updated"] += stats.get("updated", 0)
        totals["events_escalated"] += stats.get("escalated", 0)
        logger.info("provider=%s status=%s %.3fs", provider_name, stats.get("status"), elapsed)

    run.ended_at = datetime.now(UTC)
    run.status = "succeeded"
    run.stats = totals
    await session.commit()

    from app.observability import mlflow_log_run

    mlflow_log_run(
        run_name=f"pipeline:{','.join(providers)}",
        metrics={
            "events_created": float(totals["events_created"]),
            "events_updated": float(totals["events_updated"]),
            "events_escalated": float(totals["events_escalated"]),
        },
        params={"providers": ",".join(providers)},
    )
    return run
