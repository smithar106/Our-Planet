"""Scheduler: runs provider jobs on configurable, independent cadences.

Uses APScheduler with an async executor. Overlap is avoided via a per-job
asyncio lock (in-process) plus the pipeline_runs table as a record of prior
runs. Cadences are read from environment configuration.
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.worker import jobs

logger = logging.getLogger("planet.worker.scheduler")

_job_locks: dict[str, asyncio.Lock] = {}


def _lock(name: str) -> asyncio.Lock:
    if name not in _job_locks:
        _job_locks[name] = asyncio.Lock()
    return _job_locks[name]


async def _guarded(name: str, coro_fn):
    lock = _lock(name)
    if lock.locked():
        logger.info("job %s skipped: previous run still in progress", name)
        return
    async with lock:
        try:
            await coro_fn()
        except Exception:  # noqa: BLE001 - never kill the scheduler
            logger.exception("job %s failed", name)


async def _run_usgs() -> None:
    await _guarded("usgs", jobs.run_usgs_job)


async def _run_eonet() -> None:
    await _guarded("eonet", jobs.run_eonet_job)


async def _run_firms() -> None:
    await _guarded("firms", jobs.run_firms_job)


async def _run_agent() -> None:
    await _guarded("agent", jobs.run_agent_job)


async def _run_brief() -> None:
    await _guarded("brief", jobs.run_brief_job)


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        _run_usgs,
        trigger=IntervalTrigger(seconds=settings.usgs_interval_seconds),
        id="usgs",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_eonet,
        trigger=IntervalTrigger(seconds=settings.eonet_interval_seconds),
        id="eonet",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_firms,
        trigger=IntervalTrigger(seconds=settings.firms_interval_seconds),
        id="firms",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_agent,
        trigger=IntervalTrigger(seconds=settings.firms_interval_seconds),
        id="agent",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_brief,
        trigger=IntervalTrigger(seconds=settings.brief_interval_seconds),
        id="brief",
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info(
        "scheduler started: usgs=%ss eonet=%ss firms=%ss brief=%ss",
        settings.usgs_interval_seconds,
        settings.eonet_interval_seconds,
        settings.firms_interval_seconds,
        settings.brief_interval_seconds,
    )
    return scheduler
