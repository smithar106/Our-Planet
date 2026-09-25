"""Fire-noise filtering tests — isolated thermal anomalies must not become events."""

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models import Event
from app.pipeline.orchestrate import _prune_noise_wildfire


def _fire_event(sid: str, detections: int) -> Event:
    return Event(
        id=sid,
        source="firms",
        source_id=sid,
        category="wildfire",
        subtype="thermal-anomaly-cluster",
        title=f"Cluster {sid}",
        latitude=0.0,
        longitude=0.0,
        status="open",
        significance_score=10.0,
        significance_tier="ROUTINE",
        confidence=50.0,
        change_type="NEW",
        first_observed_at=datetime.now(UTC),
        last_observed_at=datetime.now(UTC),
        metrics={"detection_count": detections, "max_frp": 10.0},
    )


async def test_prune_removes_noise_clusters(session):
    session.add(_fire_event("fire_noise_1", detections=1))
    session.add(_fire_event("fire_noise_2", detections=2))
    session.add(_fire_event("fire_real", detections=50))
    await session.commit()

    pruned = await _prune_noise_wildfire(session, min_detections=3)
    await session.commit()

    assert pruned == 2
    remaining = (
        await session.execute(select(Event.id).where(Event.category == "wildfire"))
    ).scalars().all()
    assert remaining == ["fire_real"]


async def test_prune_ignores_eonet_wildfires_without_detection_count(session):
    session.add(
        Event(
            id="eonet_fire",
            source="eonet",
            source_id="eonet_fire_1",
            category="wildfire",
            title="EONET wildfire",
            status="open",
            significance_score=30.0,
            significance_tier="NOTABLE",
            change_type="NEW",
            first_observed_at=datetime.now(UTC),
            last_observed_at=datetime.now(UTC),
            metrics={"description": "reported wildfire"},
        )
    )
    await session.commit()

    pruned = await _prune_noise_wildfire(session, min_detections=3)
    await session.commit()

    assert pruned == 0
    count = (await session.execute(select(func.count()).select_from(Event))).scalar_one()
    assert count == 1
