"""Agent selection + persistence.

Selects events that cross the configurable threshold (significance score, or
escalation, or tsunami trigger), runs investigations, and persists structured
results with grounding status.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.investigate import investigate_event
from app.config import settings
from app.models import AgentInvestigation, Event
from app.observability import span

logger = logging.getLogger("planet.agent.runner")


def _should_investigate(event: Event) -> bool:
    if event.significance_score >= settings.agent_threshold:
        return True
    if event.change_type == "ESCALATING":
        return True
    metrics = event.metrics or {}
    if event.category == "earthquake" and metrics.get("tsunami") == 1:
        return True
    return False


async def select_candidates(session: AsyncSession, limit: int = 20) -> list[Event]:
    rows = (
        (
            await session.execute(
                select(Event).where(Event.status == "open").order_by(Event.significance_score.desc()).limit(limit * 5)
            )
        )
        .scalars()
        .all()
    )
    return [e for e in rows if _should_investigate(e)][:limit]


async def run_investigations(session: AsyncSession, limit: int = 20) -> dict[str, int]:
    stats = {"selected": 0, "completed": 0, "fallbacks": 0, "failed": 0}
    candidates = await select_candidates(session, limit=limit)
    stats["selected"] = len(candidates)

    for event in candidates:
        with span("agent.investigate") as s:
            # Skip if a recent completed investigation already exists.
            existing = (
                await session.execute(
                    select(AgentInvestigation)
                    .where(AgentInvestigation.event_id == event.id)
                    .order_by(AgentInvestigation.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existing is not None and existing.status == "completed" and not event.change_type == "ESCALATING":
                continue

            result = await investigate_event(session, event)
            s.set(status=result.status, grounded=result.grounded)

            investigation = AgentInvestigation(
                event_id=event.id,
                status=result.status,
                headline=result.output.get("headline"),
                summary=result.output.get("summary"),
                why_notable=result.output.get("why_notable") or [],
                watch_next=result.output.get("watch_next") or [],
                source_claims=result.output.get("source_claims") or [],
                grounded=result.grounded,
                grounding_result={"issues": result.error} if result.error else {},
                provider=settings.llm_provider,
                model=settings.llm_model,
                token_usage=result.usage or None,
                completed_at=datetime.now(UTC) if result.status in ("completed", "fallback") else None,
            )
            session.add(investigation)
            await session.flush()

            if result.status == "completed":
                stats["completed"] += 1
            elif result.status == "fallback":
                stats["fallbacks"] += 1
            else:
                stats["failed"] += 1

    await session.commit()

    from app.observability import mlflow_log_run

    mlflow_log_run(
        run_name="agent:investigate",
        metrics={
            "selected": float(stats["selected"]),
            "completed": float(stats["completed"]),
            "fallbacks": float(stats["fallbacks"]),
            "failed": float(stats["failed"]),
        },
    )
    return stats
