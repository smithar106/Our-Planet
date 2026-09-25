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
