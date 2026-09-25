"""ORM models for PLANET.

Design notes:
- Events are the normalized, deduplicated public view.
- Source records preserve raw provider payloads verbatim for audit.
- Event snapshots capture state over time so we can express change
  (NEW / UPDATED / ESCALATING / ...) without re-deriving history.
- Fire clusters are a deterministic rollup of FIRMS detections.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base

# JSONB on Postgres, plain JSON elsewhere (SQLite).
JSONType = JSON().with_variant(JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    source: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)

    category: Mapped[str] = mapped_column(String(32), index=True)
    subtype: Mapped[str | None] = mapped_column(String(64), nullable=True)

    title: Mapped[str] = mapped_column(String(512))

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    status: Mapped[str] = mapped_column(String(16), default="open")  # open | closed

    raw_severity: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    significance_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    significance_tier: Mapped[str] = mapped_column(String(16), default="ROUTINE", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    change_type: Mapped[str] = mapped_column(String(16), default="NEW", index=True)
    metrics: Mapped[dict] = mapped_column(JSONType, default=dict)

    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    snapshots: Mapped[list[EventSnapshot]] = relationship(back_populates="event", cascade="all, delete-orphan")
    investigations: Mapped[list[AgentInvestigation]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_events_source_sourceid", "source", "source_id", unique=True),
        Index("ix_events_category_score", "category", "significance_score"),
    )


class EventSnapshot(Base):
    __tablename__ = "event_snapshots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    significance_score: Mapped[float] = mapped_column(Float, default=0.0)
    significance_tier: Mapped[str] = mapped_column(String(16), default="ROUTINE")
    change_type: Mapped[str] = mapped_column(String(16), default="UNCHANGED")
    status: Mapped[str] = mapped_column(String(16), default="open")
    geometry: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONType, default=dict)
    last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped[Event] = relationship(back_populates="snapshots")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    source: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    event_id: Mapped[str | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_source_records_source_sourceid", "source", "source_id"),)


class FireCluster(Base):
    __tablename__ = "fire_clusters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    cluster_key: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(32), default="firms")

    centroid_lat: Mapped[float] = mapped_column(Float)
    centroid_lon: Mapped[float] = mapped_column(Float)
    geometry: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    bbox: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    detection_count: Mapped[int] = mapped_column(Integer, default=0)
    mean_frp: Mapped[float] = mapped_column(Float, default=0.0)
    max_frp: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_distribution: Mapped[dict] = mapped_column(JSONType, default=dict)

    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    event_id: Mapped[str | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AgentInvestigation(Base):
    __tablename__ = "agent_investigations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/running/completed/fallback/failed

    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_notable: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    watch_next: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    source_claims: Mapped[list | None] = mapped_column(JSONType, nullable=True)

    grounded: Mapped[bool] = mapped_column(Boolean, default=False)
    grounding_result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped[Event] = relationship(back_populates="investigations")


class DailyBrief(Base):
    __tablename__ = "daily_briefs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    brief_date: Mapped[date] = mapped_column(Date, index=True, unique=True)
    content: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running/succeeded/failed
    stats: Mapped[dict] = mapped_column(JSONType, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider_runs: Mapped[list[ProviderRun]] = relationship(back_populates="pipeline_run", cascade="all, delete-orphan")


class ProviderRun(Base):
    __tablename__ = "provider_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    pipeline_run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running/succeeded/failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_normalized: Mapped[int] = mapped_column(Integer, default=0)
    events_created: Mapped[int] = mapped_column(Integer, default=0)
    events_updated: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    pipeline_run: Mapped[PipelineRun] = relationship(back_populates="provider_runs")
