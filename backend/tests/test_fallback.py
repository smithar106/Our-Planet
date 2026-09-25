"""Deterministic fallback tests."""

from app.agent.fallback import deterministic_description
from app.models import Event


def test_fallback_is_source_grounded():
    event = Event(
        id="evt1",
        source="usgs",
        source_id="usgs_1",
        category="earthquake",
        subtype="mww",
        title="M6.2 earthquake — Test region",
        latitude=10.0,
        longitude=100.0,
        status="open",
        significance_score=61.5,
        significance_tier="SIGNIFICANT",
        confidence=50.0,
        change_type="NEW",
        metrics={"magnitude": 6.2, "depth_km": 10.0},
        source_url="https://earthquake.usgs.gov/eventpage/usgs_1",
    )
    out = deterministic_description(event)
    assert out["grounded"] is True
    assert "6.2" in out["summary"]
    assert "significance" in out["summary"].lower()


def test_fallback_fire_notes_not_confirmed_wildfire():
    event = Event(
        id="evt2",
        source="firms",
        source_id="cluster_1",
        category="wildfire",
        title="Thermal anomaly cluster",
        significance_score=40.0,
        significance_tier="NOTABLE",
        confidence=80.0,
        change_type="NEW",
        metrics={"detection_count": 120, "max_frp": 55.0},
    )
    out = deterministic_description(event)
    assert "not a confirmed wildfire" in out["summary"]
