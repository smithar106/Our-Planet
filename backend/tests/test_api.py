"""API endpoint tests (read-only, no network)."""

import httpx
import pytest

from app.db import get_session_factory, init_db, reset_engine
from app.pipeline.normalize import normalize_usgs
from app.pipeline.orchestrate import _upsert_event
from app.pipeline.scoring import score_event


@pytest.fixture
async def client(make_usgs_record):
    reset_engine()
    await init_db()

    factory = get_session_factory()
    async with factory() as session:
        for mag, sid in [(6.0, "usgs_api_001"), (7.0, "usgs_api_002")]:
            record = make_usgs_record(mag=mag, source_id=sid)
            normalized = normalize_usgs(record)
            score = score_event(normalized.category, normalized.metrics, normalized.raw_severity)
            from app.constants import tier_for_score

            tier = tier_for_score(score)
            await _upsert_event(session, normalized, score, tier)
        await session.commit()

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    from app.db import Base, get_engine

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    reset_engine()


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_list_events(client):
    resp = await client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert data[0]["category"] == "earthquake"


async def test_event_detail(client):
    resp = await client.get("/api/events")
    event_id = resp.json()[0]["id"]
    detail = await client.get(f"/api/events/{event_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert "explanation" in body
    assert "significance_score" in body


async def test_event_not_found(client):
    resp = await client.get("/api/events/nonexistent")
    assert resp.status_code == 404


async def test_filter_by_category(client):
    resp = await client.get("/api/events", params={"category": "earthquake"})
    assert resp.status_code == 200
    assert all(e["category"] == "earthquake" for e in resp.json())


async def test_status_endpoint(client):
    resp = await client.get("/api/status")
    assert resp.status_code == 200
    assert "pipeline" in resp.json()


async def test_summary_endpoint(client):
    resp = await client.get("/api/summary")
    assert resp.status_code == 200
    assert "last_24h" in resp.json()
