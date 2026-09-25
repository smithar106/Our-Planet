"""Command-line entrypoints for PLANET backend.

Usage:
    python -m app.cli initdb          # create tables (local dev)
    python -m app.cli worker          # run the scheduled worker
    python -m app.cli once            # run one full pipeline pass
    python -m app.cli seed            # load fixture data (no network)
"""

from __future__ import annotations

import argparse
import asyncio

from app.logging import setup_logging


async def _initdb() -> None:
    from app.db import init_db

    await init_db()
    print("database tables created")


async def _worker() -> None:
    from app.worker.scheduler import start_scheduler

    start_scheduler()
    while True:
        await asyncio.sleep(3600)


async def _once() -> None:
    from app.worker.jobs import run_full_pipeline_job

    await run_full_pipeline_job()
    print("pipeline pass complete")


async def _seed() -> None:
    from app.db import init_db
    from app.scripts.seed import seed_fixtures

    await init_db()
    await seed_fixtures()
    print("fixtures loaded")


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="PLANET backend CLI")
    parser.add_argument("command", choices=["initdb", "worker", "once", "seed"])
    args = parser.parse_args()

    if args.command == "initdb":
        asyncio.run(_initdb())
    elif args.command == "worker":
        asyncio.run(_worker())
    elif args.command == "once":
        asyncio.run(_once())
    elif args.command == "seed":
        asyncio.run(_seed())


if __name__ == "__main__":
    main()
