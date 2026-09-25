"""Fire clustering tests."""

from datetime import UTC, datetime

from app.pipeline.clustering import cluster_fire_detections, haversine_km


def _det(lat, lon, frp=10.0, confidence="high", dt=None):
    return {
        "latitude": lat,
        "longitude": lon,
        "frp": frp,
        "confidence": confidence,
        "acquired_at": dt or datetime(2026, 9, 25, 8, 0, tzinfo=UTC),
    }


def test_haversine():
    # Roughly 111 km per degree of latitude.
    d = haversine_km(0.0, 0.0, 1.0, 0.0)
    assert 110 < d < 112


def test_nearby_detections_form_one_cluster():
    detections = [_det(34.05, -118.25), _det(34.06, -118.24), _det(34.07, -118.26)]
    clusters = cluster_fire_detections(detections, radius_km=5.0)
    assert len(clusters) == 1
    assert clusters[0]["detection_count"] == 3


def test_far_detections_form_separate_clusters():
    detections = [_det(34.05, -118.25), _det(50.0, 10.0)]
    clusters = cluster_fire_detections(detections, radius_km=5.0)
    assert len(clusters) == 2


def test_cluster_derives_properties():
    detections = [
        _det(34.05, -118.25, frp=10.0, confidence="high"),
        _det(34.06, -118.24, frp=30.0, confidence="nominal"),
    ]
    clusters = cluster_fire_detections(detections, radius_km=5.0)
    c = clusters[0]
    assert c["max_frp"] == 30.0
    assert c["mean_frp"] == 20.0
    assert c["confidence_distribution"] == {"high": 1, "nominal": 1}
    assert "centroid_lat" in c


def test_empty_detections():
    assert cluster_fire_detections([]) == []
