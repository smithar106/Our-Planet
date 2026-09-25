"""Scheduled worker jobs.

Each job opens its own session and is isolated so a failure in one provider
never prevents others from running. Jobs use advisory locking via the
pipeline_runs table (a job that is already running is skipped) — implemented
in the scheduler layer rather than here to keep jobs simple.
"""

from __future__ import annotations

import logging

from app.agent.runner import run_investigations
from app.brief.generator import generate_brief
from app.db import get_session_factory
from app.observability import span
from app.pipeline.orchestrate import run_pipeline

logger = logging.getLogger("planet.worker")


async def run_usgs_job() -> None:
    with span("job.usgs"):
        factory = get_session_factory()
        async with factory() as session:
            await run_pipeline(session, providers=["usgs"])


async def run_eonet_job() -> None:
    with span("job.eonet"):
        factory = get_session_factory()
        async with factory() as session:
            await run_pipeline(session, providers=["eonet"])


async def run_firms_job() -> None:
    with span("job.firms"):
        factory = get_session_factory()
        async with factory() as session:
            await run_pipeline(session, providers=["firms"])


async def run_agent_job() -> None:
    with span("job.agent"):
        factory = get_session_factory()
        async with factory() as session:
            stats = await run_investigations(session)
            logger.info("agent job stats: %s", stats)


async def run_brief_job() -> None:
    with span("job.brief"):
        factory = get_session_factory()
        async with factory() as session:
            await generate_brief(session)


async def run_full_pipeline_job() -> None:
    """Run everything once (used for local dev / manual trigger)."""
    with span("job.full"):
        factory = get_session_factory()
        async with factory() as session:
            await run_pipeline(session)
        async with factory() as session:
            await run_investigations(session)
        async with factory() as session:
            await generate_brief(session)
