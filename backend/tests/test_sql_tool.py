"""Read-only SQL tool tests — the safety path must block writes."""

from app.agent.sql_tool import run_sql_query, validate_read_only_sql


def test_rejects_insert():
    assert validate_read_only_sql("INSERT INTO events (id) VALUES ('x')") is not None


def test_rejects_update():
    assert validate_read_only_sql("UPDATE events SET title='x'") is not None


def test_rejects_delete():
    assert validate_read_only_sql("DELETE FROM events") is not None


def test_rejects_drop():
    assert validate_read_only_sql("DROP TABLE events") is not None


def test_rejects_multiple_statements():
    assert validate_read_only_sql("SELECT 1; SELECT 2") is not None


def test_rejects_comments():
    assert validate_read_only_sql("SELECT 1 -- comment") is not None


def test_rejects_non_select():
    assert validate_read_only_sql("EXPLAIN SELECT 1") is not None


def test_accepts_select():
    assert validate_read_only_sql("SELECT * FROM events") is None


def test_accepts_with_cte():
    assert validate_read_only_sql("WITH x AS (SELECT 1) SELECT * FROM x") is None


async def test_run_sql_returns_rows(session):
    from datetime import UTC, datetime

    from app.models import Event

    session.add(
        Event(
            id="sql_evt_1",
            source="usgs",
            source_id="usgs_sql_1",
            category="earthquake",
            title="M5 earthquake",
            significance_score=40.0,
            significance_tier="NOTABLE",
            change_type="NEW",
            first_observed_at=datetime.now(UTC),
            last_observed_at=datetime.now(UTC),
            metrics={"magnitude": 5.0},
        )
    )
    await session.commit()

    result = await run_sql_query(session, "SELECT count(*) AS n FROM events")
    assert "error" not in result
    assert result["rows"][0]["n"] == 1


async def test_run_sql_blocks_write(session):
    result = await run_sql_query(session, "INSERT INTO events (id) VALUES ('hack')")
    assert "error" in result
