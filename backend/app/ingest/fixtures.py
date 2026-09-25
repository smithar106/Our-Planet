"""Deterministic fixture data + offline providers.

Used for tests, evaluation, and local seeding when no network or API key is
available. Fixtures are static and version-controlled so scoring/grounding
behavior can be verified reproducibly.
"""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime, timedelta
from typing import Any

from app.ingest.base import BaseProvider, FetchResult

_FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"

_NOW = datetime.now(UTC)


def _ts(hours_ago: float) -> int:
    return int((_NOW - timedelta(hours=hours_ago)).timestamp() * 1000)


# ---------------------------------------------------------------------------
# USGS GeoJSON features
# ---------------------------------------------------------------------------

USGS_FEATURES: list[dict[str, Any]] = [
    {
        "type": "Feature",
        "id": "usgs_m7_001",
        "geometry": {"type": "Point", "coordinates": [155.7, -6.2, 35.0]},
        "properties": {
            "mag": 7.2,
            "place": "Pacific region",
            "time": _ts(0.2),
            "updated": _ts(0.1),
            "magType": "mww",
            "felt": 120,
            "cdi": 6.5,
            "mmi": 7.0,
            "alert": "orange",
            "tsunami": 0,
            "sig": 800,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/usgs_m7_001",
            "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/usgs_m7_001.geojson",
        },
    },
    {
        "type": "Feature",
        "id": "usgs_m3_001",
        "geometry": {"type": "Point", "coordinates": [-122.3, 37.8, 8.0]},
        "properties": {
            "mag": 3.1,
            "place": "California",
            "time": _ts(1.5),
            "updated": _ts(1.4),
            "magType": "ml",
            "felt": 3,
            "cdi": 2.0,
            "mmi": None,
            "alert": None,
            "tsunami": 0,
            "sig": 45,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/usgs_m3_001",
        },
    },
    {
        "type": "Feature",
        "id": "usgs_m62_001",
        "geometry": {"type": "Point", "coordinates": [139.8, 35.6, 50.0]},
        "properties": {
            "mag": 6.2,
            "place": "Japan region",
            "time": _ts(3.0),
            "updated": _ts(2.9),
            "magType": "mww",
            "felt": 40,
            "cdi": 4.0,
            "mmi": 5.5,
            "alert": "yellow",
            "tsunami": 0,
            "sig": 500,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/usgs_m62_001",
        },
    },
]


# ---------------------------------------------------------------------------
# EONET v3 events
# ---------------------------------------------------------------------------

EONET_EVENTS: list[dict[str, Any]] = [
    {
        "id": "eonet_wildfire_001",
        "title": "Wildfire in California",
        "description": "Large wildfire reported near Los Angeles.",
        "categories": [{"id": "wildfires", "title": "Wildfires"}],
        "geometry": [
            {
                "type": "Point",
                "coordinates": [-118.2, 34.1],
                "date": (_NOW - timedelta(hours=6)).isoformat(),
            }
        ],
        "created": (_NOW - timedelta(hours=48)).isoformat(),
        "updated": (_NOW - timedelta(hours=2)).isoformat(),
        "closed": None,
        "sources": [{"id": "src1", "url": "https://example.com/wildfire"}],
    },
    {
        "id": "eonet_volcano_001",
        "title": "Volcanic activity",
        "description": "Ash emissions observed.",
        "categories": [{"id": "volcanoes", "title": "Volcanoes"}],
        "geometry": [
            {
                "type": "Point",
                "coordinates": [157.0, -6.0],
                "date": (_NOW - timedelta(hours=12)).isoformat(),
            }
        ],
        "created": (_NOW - timedelta(hours=72)).isoformat(),
        "updated": (_NOW - timedelta(hours=1)).isoformat(),
        "closed": (_NOW - timedelta(hours=1)).isoformat(),  # closed event
        "sources": [{"id": "src2", "url": "https://example.com/volcano"}],
    },
]


# ---------------------------------------------------------------------------
# FIRMS CSV (VIIRS)
# ---------------------------------------------------------------------------

FIRMS_CSV: str = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,"
    "confidence,version,bright_ti5,frp,daynight\n"
    "34.05,-118.25,330.1,1.0,1.0,2026-09-25,0841,NOAA-20,VIIRS,high,2.0,300.0,42.5,D\n"
    "34.06,-118.24,329.0,1.1,1.1,2026-09-25,0841,NOAA-20,VIIRS,high,2.0,299.0,40.0,D\n"
    "34.07,-118.26,328.5,1.2,1.2,2026-09-25,0842,NOAA-20,VIIRS,nominal,2.0,298.0,20.0,D\n"
    "34.08,-118.23,327.0,1.3,1.3,2026-09-25,0843,NOAA-20,VIIRS,low,2.0,297.0,10.0,D\n"
    "40.5,-120.5,325.0,2.0,2.0,2026-09-25,0830,NOAA-21,VIIRS,high,2.0,290.0,55.0,D\n"
    "40.51,-120.49,324.0,2.1,2.1,2026-09-25,0831,NOAA-21,VIIRS,high,2.0,289.0,50.0,D\n"
)


class FixtureUsgsProvider(BaseProvider):
    name = "usgs"

    async def fetch(self) -> FetchResult:
        records = []
        for feature in USGS_FEATURES:
            props = feature.get("properties", {})
            geometry = feature.get("geometry") or {}
            coords = geometry.get("coordinates") or []
            records.append(
                {
                    "id": props.get("id") or feature.get("id"),
                    "properties": props,
                    "geometry": geometry,
                    "longitude": coords[0] if len(coords) > 0 else None,
                    "latitude": coords[1] if len(coords) > 1 else None,
                    "depth_km": coords[2] if len(coords) > 2 else None,
                }
            )
        return FetchResult(provider=self.name, records=records)


class FixtureEonetProvider(BaseProvider):
    name = "eonet"

    async def fetch(self) -> FetchResult:
        return FetchResult(provider=self.name, records=EONET_EVENTS)


class FixtureFirmsProvider(BaseProvider):
    name = "firms"

    async def fetch(self) -> FetchResult:
        from app.ingest.firms import FirmsProvider

        records = FirmsProvider._parse_csv(FIRMS_CSV, "VIIRS_NOAA20_NRT")
        return FetchResult(provider=self.name, records=records)


def load_json_fixture(name: str) -> Any:
    path = _FIXTURE_DIR / name
    return json.loads(path.read_text())
