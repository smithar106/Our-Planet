"""Load deterministic fixtures into the database (offline, no network)."""

from __future__ import annotations

from app.agent.runner import run_investigations
from app.db import get_session_factory
from app.ingest.fixtures import (
    FixtureEonetProvider,
    FixtureFirmsProvider,
    FixtureUsgsProvider,
)
from app.pipeline.orchestrate import ingest_eonet, ingest_firms, ingest_usgs


async def seed_fixtures() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await ingest_usgs(session, FixtureUsgsProvider())
        await ingest_eonet(session, FixtureEonetProvider())
        await ingest_firms(session, FixtureFirmsProvider())
        await session.commit()
    async with factory() as session:
        await run_investigations(session)


async def reset_fixtures() -> None:
    """Purge all ingested data and reseed with deterministic synthetic fixtures.

    Production-only (Postgres): truncates every data table with CASCADE, then
    runs VACUUM FULL to return physical disk space, and reseeds the small
    synthetic dataset. Intended to reclaim space consumed by unbounded live
    ingestion.
    """
    from sqlalchemy import text

    from app.db import get_engine

    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE source_records, event_snapshots, fire_clusters, "
                "agent_investigations, daily_briefs, provider_runs, pipeline_runs, "
                "agent_evals, events RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

    # VACUUM FULL must run outside a transaction to reclaim disk space.
    async with get_engine().connect() as conn:
        autocommit = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await autocommit.execute(text("VACUUM (FULL, ANALYZE)"))

    await seed_fixtures()

