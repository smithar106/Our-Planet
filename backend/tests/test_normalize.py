"""Normalization tests."""

from app.pipeline.normalize import normalize_eonet, normalize_usgs


def test_usgs_normalization_preserves_fields():
    record = {
        "id": "usgs_abc",
        "properties": {
            "mag": 5.8,
            "place": "Somewhere",
            "time": 1700000000000,
            "updated": 1700000001000,
            "magType": "mww",
            "felt": 20,
            "cdi": 4.0,
            "mmi": 5.0,
            "alert": "green",
            "tsunami": 0,
            "sig": 300,
            "url": "https://earthquake.usgs.gov/eventpage/usgs_abc",
        },
        "geometry": {"type": "Point", "coordinates": [-120.0, 35.0, 15.0]},
        "longitude": -120.0,
        "latitude": 35.0,
        "depth_km": 15.0,
    }
    n = normalize_usgs(record)
    assert n is not None
    assert n.category == "earthquake"
    assert n.source == "usgs"
    assert n.source_id == "usgs_abc"
    assert n.metrics["magnitude"] == 5.8
    assert n.metrics["depth_km"] == 15.0
    assert n.source_url == "https://earthquake.usgs.gov/eventpage/usgs_abc"


def test_usgs_missing_values_stay_none():
    record = {
        "id": "usgs_empty",
        "properties": {"mag": None, "place": None, "time": 1700000000000, "updated": 1700000001000},
        "geometry": None,
        "longitude": None,
        "latitude": None,
        "depth_km": None,
    }
    n = normalize_usgs(record)
    assert n is not None
    # Missing magnitude stays missing, not zero.
    assert n.metrics["magnitude"] is None


def test_eonet_category_mapping():
    record = {
        "id": "eonet_1",
        "title": "Wildfire",
        "categories": [{"id": "wildfires"}],
        "geometry": [{"type": "Point", "coordinates": [-118.0, 34.0]}],
        "created": "2026-09-25T00:00:00Z",
    }
    n = normalize_eonet(record)
    assert n is not None
    assert n.category == "wildfire"
    assert n.source == "eonet"


def test_eonet_unknown_category_maps_to_other():
    record = {
        "id": "eonet_2",
        "title": "Mystery",
        "categories": [{"id": "somethingNew"}],
        "geometry": [{"type": "Point", "coordinates": [0.0, 0.0]}],
        "created": "2026-09-25T00:00:00Z",
    }
    n = normalize_eonet(record)
    assert n is not None
    assert n.category == "other"


def test_eonet_closed_status():
    record = {
        "id": "eonet_3",
        "title": "Closed event",
        "categories": [{"id": "floods"}],
        "geometry": [{"type": "Point", "coordinates": [0.0, 0.0]}],
        "closed": "2026-09-25T00:00:00Z",
    }
    n = normalize_eonet(record)
    assert n is not None
    assert n.status == "closed"
