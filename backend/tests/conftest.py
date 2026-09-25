"""Pytest fixtures for PLANET backend.

Configures an isolated SQLite test database and disables the LLM so tests are
deterministic and offline.
"""

from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="planet_test_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/test.db"
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_BASE_URL"] = ""
os.environ["LLM_PROVIDER"] = "deepseek"
os.environ["TRACING_BACKEND"] = "memory"
os.environ["NASA_FIRMS_MAP_KEY"] = ""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.config import settings
from app.db import Base, reset_engine


@pytest.fixture
async def session():
    reset_engine()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def make_usgs_record():
    def _make(
        mag: float = 6.0,
        source_id: str = "usgs_test_001",
        depth: float = 20.0,
        alert: str | None = None,
        tsunami: int = 0,
        felt: int | None = None,
        sig: int | None = None,
    ) -> dict:
        return {
            "id": source_id,
            "properties": {
                "mag": mag,
                "place": "Test region",
                "time": 1700000000000,
                "updated": 1700000001000,
                "magType": "mww",
                "felt": felt,
                "cdi": None,
                "mmi": None,
                "alert": alert,
                "tsunami": tsunami,
                "sig": sig,
                "url": f"https://earthquake.usgs.gov/eventpage/{source_id}",
            },
            "geometry": {"type": "Point", "coordinates": [100.0, 10.0, depth]},
            "longitude": 100.0,
            "latitude": 10.0,
            "depth_km": depth,
        }

    return _make
