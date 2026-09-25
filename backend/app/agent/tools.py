"""Read-only agent tools.

The agent may only read from the database. There are NO write tools here, and
no tool receives write access. Each tool returns plain JSON-serializable dicts.

Tool names mirror the product spec:
  get_event, get_event_history, get_recent_events, get_nearby_events,
  get_source_record, get_fire_cluster_history, compare_event_to_recent_activity,
  get_global_summary
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, EventSnapshot, FireCluster, SourceRecord
from app.pipeline.clustering import haversine_km

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_event",
            "description": "Fetch a single normalized event by id.",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_history",
            "description": "Fetch the snapshot/change history of an event.",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_events",
            "description": "List recent events, optionally filtered by category and hours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "hours": {"type": "number"},
                    "limit": {"type": "number"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nearby_events",
            "description": "List events within a radius (km) of a point.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "radius_km": {"type": "number"},
                },
                "required": ["latitude", "longitude", "radius_km"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_source_record",
            "description": "Fetch the raw provider record for an event.",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fire_cluster_history",
            "description": "Fetch history of a fire/thermal-anomaly cluster.",
            "parameters": {
                "type": "object",
                "properties": {"cluster_id": {"type": "string"}},
                "required": ["cluster_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_event_to_recent_activity",
            "description": "Compare an event against recent activity in the same category.",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_global_summary",
            "description": "Deterministic global statistics for the last N hours.",
            "parameters": {
                "type": "object",
                "properties": {"hours": {"type": "number"}},
                "required": [],
            },
        },
    },
]


def _event_dict(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "source": event.source,
        "source_id": event.source_id,
        "category": event.category,
        "subtype": event.subtype,
        "title": event.title,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "status": event.status,
        "significance_score": event.significance_score,
        "significance_tier": event.significance_tier,
        "change_type": event.change_type,
        "confidence": event.confidence,
        "metrics": event.metrics,
        "first_observed_at": event.first_observed_at.isoformat() if event.first_observed_at else None,
        "last_observed_at": event.last_observed_at.isoformat() if event.last_observed_at else None,
        "source_url": event.source_url,
    }


async def get_event(session: AsyncSession, event_id: str) -> dict[str, Any]:
    event = await session.get(Event, event_id)
    if event is None:
        return {"error": "event not found"}
    return _event_dict(event)


async def get_event_history(session: AsyncSession, event_id: str) -> dict[str, Any]:
    rows = (
        (
            await session.execute(
                select(EventSnapshot).where(EventSnapshot.event_id == event_id).order_by(EventSnapshot.snapshot_at)
            )
        )
        .scalars()
        .all()
    )
    return {
        "event_id": event_id,
        "snapshots": [
            {
                "at": s.snapshot_at.isoformat() if s.snapshot_at else None,
                "score": s.significance_score,
                "tier": s.significance_tier,
                "change_type": s.change_type,
                "status": s.status,
                "metrics": s.metrics,
            }
            for s in rows
        ],
    }


async def get_recent_events(
    session: AsyncSession, category: str | None = None, hours: float = 24.0, limit: int = 20
) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    query = select(Event).where(Event.last_observed_at >= since)
    if category:
        query = query.where(Event.category == category)
    query = query.order_by(Event.significance_score.desc()).limit(min(limit, 50))
    rows = (await session.execute(query)).scalars().all()
    return {"count": len(rows), "events": [_event_dict(e) for e in rows]}


async def get_nearby_events(
    session: AsyncSession, latitude: float, longitude: float, radius_km: float
) -> dict[str, Any]:
    rows = (await session.execute(select(Event))).scalars().all()
    nearby = []
    for event in rows:
        if event.latitude is None or event.longitude is None:
            continue
        dist = haversine_km(latitude, longitude, event.latitude, event.longitude)
        if dist <= radius_km:
            d = _event_dict(event)
            d["distance_km"] = round(dist, 2)
            nearby.append(d)
    nearby.sort(key=lambda e: e["distance_km"])
    return {"count": len(nearby), "events": nearby[:20]}


async def get_source_record(session: AsyncSession, event_id: str) -> dict[str, Any]:
    event = await session.get(Event, event_id)
    if event is None:
        return {"error": "event not found"}
    row = (
        await session.execute(
            select(SourceRecord)
            .where(SourceRecord.source == event.source, SourceRecord.source_id == event.source_id)
            .order_by(SourceRecord.fetched_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return {"event_id": event_id, "raw": None}
    return {
        "event_id": event_id,
        "source": row.source,
        "source_id": row.source_id,
        "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
        "payload": row.payload,
    }


async def get_fire_cluster_history(session: AsyncSession, cluster_id: str) -> dict[str, Any]:
    rows = (await session.execute(select(FireCluster).where(FireCluster.cluster_key == cluster_id))).scalars().all()
    return {
        "cluster_id": cluster_id,
        "clusters": [
            {
                "centroid": [c.centroid_lat, c.centroid_lon],
                "detection_count": c.detection_count,
                "mean_frp": c.mean_frp,
                "max_frp": c.max_frp,
                "first_detected_at": c.first_detected_at.isoformat() if c.first_detected_at else None,
                "last_detected_at": c.last_detected_at.isoformat() if c.last_detected_at else None,
            }
            for c in rows
        ],
    }


async def compare_event_to_recent_activity(session: AsyncSession, event_id: str) -> dict[str, Any]:
    event = await session.get(Event, event_id)
    if event is None:
        return {"error": "event not found"}
    since = datetime.now(UTC) - timedelta(hours=168)
    rows = (
        (await session.execute(select(Event).where(Event.category == event.category, Event.last_observed_at >= since)))
        .scalars()
        .all()
    )
    scores = [e.significance_score for e in rows if e.id != event_id]
    scores.sort(reverse=True)
    rank = 1
    for s in scores:
        if event.significance_score < s:
            rank += 1
    return {
        "event_id": event_id,
        "category": event.category,
        "peer_count": len(scores),
        "peer_rank": rank,
        "max_peer_score": scores[0] if scores else None,
        "median_peer_score": _median(scores),
    }


async def get_global_summary(session: AsyncSession, hours: float = 24.0) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    total = (
        await session.execute(select(func.count()).select_from(Event).where(Event.last_observed_at >= since))
    ).scalar_one()
    by_category = dict(
        (
            await session.execute(
                select(Event.category, func.count()).where(Event.last_observed_at >= since).group_by(Event.category)
            )
        ).all()
    )
    significant = (
        await session.execute(
            select(func.count())
            .select_from(Event)
            .where(
                Event.last_observed_at >= since,
                Event.significance_tier.in_(["SIGNIFICANT", "MAJOR"]),
            )
        )
    ).scalar_one()
    return {
        "hours": hours,
        "total_events": total,
        "significant_events": significant,
        "by_category": {k: v for k, v in by_category},
    }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    n = len(values)
    mid = n // 2
    if n % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


_TOOL_FUNCS = {
    "get_event": get_event,
    "get_event_history": get_event_history,
    "get_recent_events": get_recent_events,
    "get_nearby_events": get_nearby_events,
    "get_source_record": get_source_record,
    "get_fire_cluster_history": get_fire_cluster_history,
    "compare_event_to_recent_activity": compare_event_to_recent_activity,
    "get_global_summary": get_global_summary,
}


async def execute_tool(session: AsyncSession, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    func = _TOOL_FUNCS.get(name)
    if func is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return await func(session, **arguments)
    except TypeError as exc:
        return {"error": f"invalid arguments: {exc}"}
