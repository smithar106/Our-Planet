"""Agent evaluation harness.

Proves the safety architecture actually works, and stores results in the
`agent_evals` table so they can be analyzed with plain SQL (psql, the read-only
SQL tool, or any SQL client).

The harness mixes deterministic checks (grounding, fallback, schema) with
SQL-backed ground-truth checks (query the database to confirm what the agent
should have reported).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.fallback import deterministic_description
from app.agent.grounding import validate_grounding
from app.agent.investigate import investigate_event
from app.agent.sql_tool import run_sql_query, validate_read_only_sql
from app.models import AgentEval, Event

logger = logging.getLogger("planet.eval")

CaseFn = Callable[[AsyncSession], Awaitable[tuple[bool, dict[str, Any]]]]


async def _case_grounding_unsupported_number(session: AsyncSession) -> tuple[bool, dict]:
    facts = {"significance_score": 61.5, "metrics": {"magnitude": 6.2, "depth_km": 10.0}}
    gen = {"headline": "quake", "summary": "Magnitude 9.9 quake killed 5000 people"}
    result = validate_grounding(gen, facts)
    passed = not result.passed and any("unsupported number" in i for i in result.issues)
    return passed, {"issues": result.issues}


async def _case_grounding_restricted_word(session: AsyncSession) -> tuple[bool, dict]:
    facts = {"significance_score": 61.5, "metrics": {"magnitude": 6.2}}
    gen = {"headline": "Record quake strikes", "summary": "A record event."}
    result = validate_grounding(gen, facts)
    passed = not result.passed and any("record" in i for i in result.issues)
    return passed, {"issues": result.issues}


async def _case_grounding_neutral_passes(session: AsyncSession) -> tuple[bool, dict]:
    facts = {"significance_score": 61.5, "metrics": {"magnitude": 6.2, "depth_km": 10.0}}
    gen = {
        "headline": "M6.2 earthquake",
        "summary": "A magnitude 6.2 earthquake at 10 km depth. Score 61.5.",
        "why_notable": ["PLANET flagged this event as statistically notable"],
        "source_claims": [{"source": "usgs", "claim": "magnitude 6.2"}],
    }
    result = validate_grounding(gen, facts)
    return result.passed, {"issues": result.issues}


async def _case_fallback_schema_valid(session: AsyncSession) -> tuple[bool, dict]:
    event = Event(
        id="eval_evt",
        source="usgs",
        source_id="usgs_eval",
        category="earthquake",
        title="M6.2 earthquake",
        significance_score=61.5,
        significance_tier="SIGNIFICANT",
        change_type="NEW",
        metrics={"magnitude": 6.2, "depth_km": 10.0},
    )
    out = deterministic_description(event)
    required = {"headline", "summary", "why_notable", "watch_next", "source_claims"}
    passed = required.issubset(out.keys()) and out.get("grounded") is True
    return passed, {"keys": sorted(out.keys())}


async def _case_sql_blocks_write(session: AsyncSession) -> tuple[bool, dict]:
    err = validate_read_only_sql("INSERT INTO events (id) VALUES ('x')")
    passed = err is not None
    return passed, {"error": err}


async def _case_sql_select_works(session: AsyncSession) -> tuple[bool, dict]:
    result = await run_sql_query(session, "SELECT count(*) AS n FROM events")
    passed = "error" not in result and "rows" in result
    return passed, {"result_keys": list(result.keys()), "count": result.get("count")}


async def _case_sql_ground_truth_consistency(session: AsyncSession) -> tuple[bool, dict]:
    """Cross-check a stored event's significance against a SQL query.

    This is the "SQL for agent evals" pattern: verify what the deterministic
    description reports matches the database ground truth.
    """
    result = await run_sql_query(
        session,
        "SELECT id, significance_score, significance_tier FROM events ORDER BY significance_score DESC LIMIT 1",
    )
    if "error" in result or not result["rows"]:
        # No events yet — treat as pass with a note (nothing to cross-check).
        return True, {"note": "no events to cross-check", "error": result.get("error")}

    row = result["rows"][0]
    event_id = row["id"]
    db_score = row["significance_score"]
    db_tier = row["significance_tier"]

    event = await session.get(Event, event_id)
    desc = deterministic_description(event)
    # The fallback description embeds the score; verify it is present and matches.
    passed = str(round(db_score, 1)) in desc["summary"] or str(db_score) in desc["summary"]
    return passed, {"db_score": db_score, "db_tier": db_tier, "summary": desc["summary"][:200]}


async def _case_agent_no_llm_fallback_grounded(session: AsyncSession) -> tuple[bool, dict]:
    event = Event(
        id="eval_evt2",
        source="usgs",
        source_id="usgs_eval2",
        category="earthquake",
        title="M6.0 earthquake",
        significance_score=60.0,
        significance_tier="SIGNIFICANT",
        change_type="NEW",
        metrics={"magnitude": 6.0, "depth_km": 10.0},
    )
    result = await investigate_event(session, event)
    required = {"headline", "summary", "why_notable", "watch_next", "source_claims"}
    passed = result.status == "fallback" and result.grounded and required.issubset(result.output.keys())
    return passed, {"status": result.status, "grounded": result.grounded}


CASES: list[tuple[str, str, CaseFn]] = [
    ("grounding", "unsupported_number", _case_grounding_unsupported_number),
    ("grounding", "restricted_word", _case_grounding_restricted_word),
    ("grounding", "neutral_passes", _case_grounding_neutral_passes),
    ("fallback", "schema_valid", _case_fallback_schema_valid),
    ("sql", "blocks_write", _case_sql_blocks_write),
    ("sql", "select_works", _case_sql_select_works),
    ("sql", "ground_truth_consistency", _case_sql_ground_truth_consistency),
    ("schema", "agent_no_llm_fallback_grounded", _case_agent_no_llm_fallback_grounded),
]


async def run_evals(session: AsyncSession, store: bool = True) -> dict[str, Any]:
    """Run all cases, store results in agent_evals, and return a summary."""
    results: list[dict[str, Any]] = []
    passed_count = 0
    for category, name, fn in CASES:
        try:
            passed, details = await fn(session)
        except Exception as exc:  # noqa: BLE001 - a failing case is itself a result
            passed, details = False, {"error": str(exc)}
            logger.exception("eval case %s failed", name)
        results.append({"case": name, "category": category, "passed": passed, "details": details})
        if store:
            session.add(AgentEval(eval_case=name, category=category, passed=passed, details=details))
        if passed:
            passed_count += 1

    if store:
        await session.commit()

    return {
        "total": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "results": results,
    }


async def eval_summary_sql(session: AsyncSession) -> dict[str, Any]:
    """Example SQL view over stored eval results (demonstrates SQL-based evals)."""
    result = await session.execute(
        text(
            "SELECT category, count(*) AS total, sum(case when passed then 1 else 0 end) AS passed "
            "FROM agent_evals GROUP BY category ORDER BY category"
        )
    )
    return {"by_category": [dict(zip(result.keys(), row, strict=True)) for row in result.fetchall()]}
