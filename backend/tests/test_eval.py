"""Evaluation harness tests — the safety architecture must actually pass its own evals."""

from sqlalchemy import func, select

from app.eval.harness import CASES, run_evals
from app.models import AgentEval


def test_all_cases_defined():
    assert len(CASES) >= 8
    names = [c[1] for c in CASES]
    assert "unsupported_number" in names
    assert "blocks_write" in names


async def test_run_evals_stores_results(session):
    summary = await run_evals(session)
    assert summary["total"] == len(CASES)
    assert summary["passed"] == summary["total"]  # all safety cases pass

    count = (await session.execute(select(func.count()).select_from(AgentEval))).scalar_one()
    assert count == len(CASES)


async def test_evals_are_sql_queryable(session):
    await run_evals(session)
    from app.agent.sql_tool import run_sql_query

    result = await run_sql_query(
        session,
        "SELECT category, count(*) AS total, "
        "sum(case when passed then 1 else 0 end) AS passed "
        "FROM agent_evals GROUP BY category ORDER BY category",
    )
    assert "error" not in result
    assert len(result["rows"]) >= 3  # grounding, fallback, sql, schema categories
