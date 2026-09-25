"""Pydantic schemas for API input/output.

Public API endpoints are READ-ONLY. There are no write schemas here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventBrief(BaseModel):
    id: str
    source: str
    source_id: str
    category: str
    subtype: str | None = None
    title: str
    latitude: float | None = None
    longitude: float | None = None
    status: str
    significance_score: float
    significance_tier: str
    change_type: str
    first_observed_at: datetime
    last_observed_at: datetime
    source_url: str | None = None


class EventDetail(EventBrief):
    geometry: dict | None = None
    raw_severity: dict | None = None
    confidence: float = 0.0
    metrics: dict = Field(default_factory=dict)
    explanation: dict | None = None
    change_history: list[dict] = Field(default_factory=list)
    updated_at: datetime


class InvestigationOut(BaseModel):
    status: str
    headline: str | None = None
    summary: str | None = None
    why_notable: list[str] = Field(default_factory=list)
    watch_next: list[str] = Field(default_factory=list)
    source_claims: list[dict] = Field(default_factory=list)
    grounded: bool = False


class SummaryOut(BaseModel):
    generated_at: datetime
    last_24h: dict[str, Any] = Field(default_factory=dict)
    most_significant: list[EventBrief] = Field(default_factory=list)
    escalating: list[EventBrief] = Field(default_factory=list)


class BriefOut(BaseModel):
    brief_date: str
    title: str
    intro: str
    most_significant: list[EventBrief] = Field(default_factory=list)
    new_developments: list[EventBrief] = Field(default_factory=list)
    escalating: list[EventBrief] = Field(default_factory=list)
    by_category: dict[str, int] = Field(default_factory=dict)
    watching: list[str] = Field(default_factory=list)
    generated_at: datetime


class ProviderStatus(BaseModel):
    provider: str
    last_successful_fetch: datetime | None = None
    status: str  # healthy | degraded | failed | disabled
    last_error: str | None = None
    records_last_fetch: int = 0


class StatusOut(BaseModel):
    pipeline: str  # healthy | degraded | failed
    agent: str  # healthy | degraded | disabled
    last_pipeline_duration_ms: float | None = None
    events_processed: int = 0
    events_selected_for_investigation: int = 0
    investigations_completed: int = 0
    fallbacks: int = 0
    providers: list[ProviderStatus] = Field(default_factory=list)
    llm_configured: bool = False


class HealthOut(BaseModel):
    status: str
    version: str
