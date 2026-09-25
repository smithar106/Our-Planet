"""Daily Earth Brief generation.

Statistics are ALWAYS calculated in deterministic code — never by the LLM.
The LLM may only explain the calculated results. Each brief is stored so
historical briefs can be viewed later.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm import LLMClient, LLMUnavailable, llm_available
from app.models import DailyBrief, Event
from app.serialize import json_safe

logger = logging.getLogger("planet.brief")

BRIEF_PROMPT = """\
You are summarizing PLANET's daily Earth brief. Below are deterministic
statistics already computed by code. Write a short (2-3 sentence) neutral intro
for a public audience that explains the counts. Do NOT invent numbers — use only
the numbers provided. Do not use sensational language. Return only the intro text.
"""


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


async def _compute_stats(session: AsyncSession, since: datetime) -> dict[str, Any]:
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

    most_significant = [_event_brief(e) for e in events if e.significance_tier in ("SIGNIFICANT", "MAJOR")][:5]
    new_developments = [_event_brief(e) for e in events if e.change_type == "NEW"][:10]
    escalating = [_event_brief(e) for e in events if e.change_type == "ESCALATING"][:10]
    major = [e for e in events if e.significance_tier == "MAJOR"]
    significant = [e for e in events if e.significance_tier in ("SIGNIFICANT", "MAJOR")]

    return {
        "total_events": len(events),
        "major_events": len(major),
        "significant_developments": len(significant),
        "new_events": sum(1 for e in events if e.change_type == "NEW"),
        "escalating_events": len(escalating),
        "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
        "most_significant": most_significant,
        "new_developments": new_developments,
        "escalating": escalating,
    }


async def _deterministic_intro(stats: dict[str, Any]) -> str:
    return (
        f"PLANET detected {stats['major_events']} major events and "
        f"{stats['significant_developments']} significant developments during the last 24 hours."
    )


async def generate_brief(session: AsyncSession, brief_date: date | None = None) -> DailyBrief:
    brief_date = brief_date or date.today()
    since = datetime.combine(brief_date, datetime.min.time(), tzinfo=UTC) - timedelta(hours=24)
    stats = await _compute_stats(session, since)

    intro = await _deterministic_intro(stats)
    watching: list[str] = []

    if llm_available():
        client = LLMClient()
        try:
            prompt = (
                BRIEF_PROMPT
                + "\n\nStatistics:\n"
                + f"total={stats['total_events']}, major={stats['major_events']}, "
                + f"significant={stats['significant_developments']}, new={stats['new_events']}, "
                + f"escalating={stats['escalating_events']}, by_category={stats['by_category']}"
            )
            resp = await client.chat([{"role": "user", "content": prompt}], tools=None, temperature=0.2)
            if resp.content and resp.content.strip():
                intro = resp.content.strip()
            # Watching list: deterministic fallback to top categories.
            watching = [c for c, _ in list(stats["by_category"].items())[:3]]
        except (LLMUnavailable, Exception) as exc:  # noqa: BLE001 - brief must never fail
            logger.warning("brief LLM unavailable: %s", exc)
        finally:
            await client.close()
    else:
        watching = [c for c, _ in list(stats["by_category"].items())[:3]]

    content = {
        "title": f"Daily Earth Brief — {brief_date.strftime('%B %-d') if brief_date else ''}",
        "intro": intro,
        "most_significant": stats["most_significant"],
        "new_developments": stats["new_developments"],
        "escalating": stats["escalating"],
        "by_category": stats["by_category"],
        "watching": watching,
        "total_events": stats["total_events"],
        "major_events": stats["major_events"],
        "significant_developments": stats["significant_developments"],
    }

    brief = DailyBrief(brief_date=brief_date, content=json_safe(content))
    session.add(brief)
    await session.commit()
    return brief
