"""Deduplication tests: duplicate source records must not create duplicate events."""

import pytest
from sqlalchemy import func, select

from app.models import Event
from app.pipeline.normalize import normalize_usgs
from app.pipeline.orchestrate import _upsert_event
from app.pipeline.scoring import score_event


@pytest.fixture
def usgs_record(make_usgs_record):
    return make_usgs_record(mag=6.0, source_id="usgs_dup_001")


async def test_duplicate_records_create_one_event(session, usgs_record):
    normalized = normalize_usgs(usgs_record)
    score = score_event(normalized.category, normalized.metrics, normalized.raw_severity)
    from app.constants import tier_for_score

    tier = tier_for_score(score)

    event1, change1 = await _upsert_event(session, normalized, score, tier)
    await session.commit()
    event2, change2 = await _upsert_event(session, normalized, score, tier)
    await session.commit()

    count = (await session.execute(select(func.count()).select_from(Event))).scalar_one()
    assert count == 1
    assert change1 == "NEW"
    assert event1.id == event2.id
