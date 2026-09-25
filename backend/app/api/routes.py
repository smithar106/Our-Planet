"""Public read-only API endpoints.

Every endpoint here is READ-ONLY. There are no mutation endpoints exposed to
the public. Inputs are validated and expensive paths rate-aware by design.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.agent.fallback import deterministic_description
from app.db import get_session
from app.models import (
    AgentInvestigation,
    DailyBrief,
    Event,
    EventSnapshot,
    PipelineRun,
    ProviderRun,
)
from app.schemas import (
    BriefOut,
    EventBrief,
    EventDetail,
    HealthOut,
    StatusOut,
    SummaryOut,
)

router = APIRouter(prefix="/api")


def _event_brief(e: Event) -> dict[str, Any]:
    return {
        "id": e.id,
        "source": e.source,
        "source_id": e.source_id,
        "category": e.category,
        "subtype": e.subtype,
        "title": e.title,
        "latitude": e.latitude,
        "longitude": e.longitude,
        "status": e.status,
        "significance_score": e.significance_score,
        "significance_tier": e.significance_tier,
        "change_type": e.change_type,
        "first_observed_at": e.first_observed_at,
        "last_observed_at": e.last_observed_at,
        "source_url": e.source_url,
    }


async def _latest_investigation(session: AsyncSession, event_id: str) -> dict[str, Any] | None:
    row = (
        await session.execute(
            select(AgentInvestigation)
            .where(AgentInvestigation.event_id == event_id)
            .order_by(AgentInvestigation.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return {
        "status": row.status,
        "headline": row.headline,
        "summary": row.summary,
        "why_notable": row.why_notable or [],
        "watch_next": row.watch_next or [],
        "source_claims": row.source_claims or [],
        "grounded": row.grounded,
        "deterministic": row.status == "fallback",
    }


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__)


@router.get("/events/recent")
async def recent_events(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EventBrief]:
    rows = (await session.execute(select(Event).order_by(Event.last_observed_at.desc()).limit(limit))).scalars().all()
    return [_event_brief(e) for e in rows]


@router.get("/events/significant")
async def significant_events(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EventBrief]:
    rows = (
        (
            await session.execute(
                select(Event)
                .where(Event.significance_tier.in_(["SIGNIFICANT", "MAJOR"]))
                .order_by(Event.significance_score.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [_event_brief(e) for e in rows]


@router.get("/events")
async def list_events(
    session: AsyncSession = Depends(get_session),
    category: str | None = Query(default=None),
    significance: str | None = Query(default=None),
    hours: int | None = Query(default=None, ge=1, le=24 * 30),
    bbox: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EventBrief]:
    query = select(Event)
    if category:
        query = query.where(Event.category == category)
    if significance:
        query = query.where(Event.significance_tier == significance.upper())
    if hours:
        since = datetime.now(UTC) - timedelta(hours=hours)
        query = query.where(Event.last_observed_at >= since)
    rows = (await session.execute(query.order_by(Event.significance_score.desc()).limit(limit))).scalars().all()
    events = [_event_brief(e) for e in rows]
    if bbox:
        events = _filter_bbox(events, bbox)
    return events


def _filter_bbox(events: list[dict[str, Any]], bbox: str) -> list[dict[str, Any]]:
    try:
        min_lon, min_lat, max_lon, max_lat = (float(x) for x in bbox.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox must be minLon,minLat,maxLon,maxLat") from exc
    result = []
    for e in events:
        if e["latitude"] is None or e["longitude"] is None:
            continue
        if min_lon <= e["longitude"] <= max_lon and min_lat <= e["latitude"] <= max_lat:
            result.append(e)
    return result


@router.get("/events/{event_id}")
async def event_detail(event_id: str, session: AsyncSession = Depends(get_session)) -> EventDetail:
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")

    snapshots = (
        (
            await session.execute(
                select(EventSnapshot)
                .where(EventSnapshot.event_id == event_id)
                .order_by(EventSnapshot.snapshot_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )

    explanation = await _latest_investigation(session, event_id)
    if explanation is None:
        explanation = deterministic_description(event)

    detail = _event_brief(event)
    detail.update(
        {
            "geometry": event.geometry,
            "raw_severity": event.raw_severity,
            "confidence": event.confidence,
            "metrics": event.metrics,
            "explanation": explanation,
            "change_history": [
                {
                    "at": s.snapshot_at,
                    "score": s.significance_score,
                    "tier": s.significance_tier,
                    "change_type": s.change_type,
                    "status": s.status,
                }
                for s in snapshots
            ],
            "updated_at": event.updated_at,
        }
    )
    return EventDetail(**detail)


@router.get("/summary")
async def summary(session: AsyncSession = Depends(get_session)) -> SummaryOut:
    since = datetime.now(UTC) - timedelta(hours=24)
    events = (
        (
            await session.execute(
                select(Event).where(Event.last_observed_at >= since).order_by(Event.significance_score.desc())
            )
        )
        .scalars()
        .all()
    )
    by_category: dict[str, int] = {}
    for e in events:
        by_category[e.category] = by_category.get(e.category, 0) + 1
    most_significant = [_event_brief(e) for e in events if e.significance_tier in ("SIGNIFICANT", "MAJOR")][:10]
    escalating = [_event_brief(e) for e in events if e.change_type == "ESCALATING"][:10]
    return SummaryOut(
        generated_at=datetime.now(UTC),
        last_24h={
            "total_events": len(events),
            "earthquakes": by_category.get("earthquake", 0),
            "fire_clusters": by_category.get("wildfire", 0),
            "other_active": sum(v for k, v in by_category.items() if k not in ("earthquake", "wildfire")),
            "significant": len(most_significant),
            "new": sum(1 for e in events if e.change_type == "NEW"),
            "escalating": len(escalating),
        },
        most_significant=most_significant,
        escalating=escalating,
    )


@router.get("/brief/latest")
async def latest_brief(session: AsyncSession = Depends(get_session)) -> BriefOut:
    row = (
        await session.execute(select(DailyBrief).order_by(DailyBrief.brief_date.desc()).limit(1))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="no brief available")
    return _brief_out(row)


@router.get("/brief/{brief_date}")
async def brief_by_date(brief_date: date, session: AsyncSession = Depends(get_session)) -> BriefOut:
    row = (await session.execute(select(DailyBrief).where(DailyBrief.brief_date == brief_date))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="brief not found")
    return _brief_out(row)


def _brief_out(row: DailyBrief) -> BriefOut:
    c = row.content or {}
    return BriefOut(
        brief_date=row.brief_date.isoformat(),
        title=c.get("title", ""),
        intro=c.get("intro", ""),
        most_significant=c.get("most_significant", []),
        new_developments=c.get("new_developments", []),
        escalating=c.get("escalating", []),
        by_category=c.get("by_category", {}),
        watching=c.get("watching", []),
        generated_at=row.created_at,
    )


@router.get("/status")
async def status(session: AsyncSession = Depends(get_session)) -> StatusOut:
    latest_run = (
        await session.execute(select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1))
    ).scalar_one_or_none()

    provider_runs = (
        (await session.execute(select(ProviderRun).order_by(ProviderRun.started_at.desc()).limit(50))).scalars().all()
    )

    providers_status = []
    seen: set[str] = set()
    for pr in provider_runs:
        if pr.provider in seen:
            continue
        seen.add(pr.provider)
        providers_status.append(
            {
                "provider": pr.provider,
                "last_successful_fetch": pr.ended_at if pr.status == "succeeded" else None,
                "status": pr.status if pr.status in ("succeeded", "failed") else "degraded",
                "last_error": pr.error,
                "records_last_fetch": pr.records_fetched,
            }
        )

    investigations_completed = (
        await session.execute(
            select(func.count())
            .select_from(AgentInvestigation)
            .where(AgentInvestigation.status.in_(["completed", "fallback"]))
        )
    ).scalar_one()
    fallbacks = (
        await session.execute(
            select(func.count()).select_from(AgentInvestigation).where(AgentInvestigation.status == "fallback")
        )
    ).scalar_one()
    events_processed = (await session.execute(select(func.count()).select_from(Event))).scalar_one()

    pipeline_health = "healthy"
    if latest_run is None:
        pipeline_health = "unknown"
    elif any(p["status"] == "failed" for p in providers_status):
        pipeline_health = "degraded"

    duration_ms = None
    if latest_run and latest_run.ended_at and latest_run.started_at:
        duration_ms = (latest_run.ended_at - latest_run.started_at).total_seconds() * 1000

    from app.config import settings

    return StatusOut(
        pipeline=pipeline_health,
        agent="healthy" if settings.llm_configured else "disabled",
        last_pipeline_duration_ms=duration_ms,
        events_processed=events_processed,
        events_selected_for_investigation=(
            await session.execute(select(func.count()).select_from(AgentInvestigation))
        ).scalar_one(),
        investigations_completed=investigations_completed,
        fallbacks=fallbacks,
        providers=providers_status,
        llm_configured=settings.llm_configured,
    )
