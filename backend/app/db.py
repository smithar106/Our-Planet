"""Database engine and session management.

Supports PostgreSQL (production) and SQLite (tests/local dev) through a single
SQLAlchemy 2.0 async interface.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine(url: str | None = None) -> AsyncEngine:
    url = url or settings.database_url
    if url.startswith("sqlite"):
        return create_async_engine(url, echo=False, future=True)
    return create_async_engine(url, echo=False, future=True, pool_pre_ping=True)


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def reset_engine() -> None:
    """Drop cached engine (used by tests to swap databases)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def init_db() -> None:
    """Create all tables for local development (production uses Alembic)."""
    from app import models  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    if _engine is not None:
        await _engine.dispose()
        reset_engine()
