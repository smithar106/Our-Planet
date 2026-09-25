"""USGS earthquake GeoJSON feed ingestion.

Uses the official USGS GeoJSON summary feed. We ingest structured fields only
and never scrape HTML pages.

Useful fields preserved (in raw_payload):
- USGS event id, place, time, updated
- mag, magType, longitude, latitude, depth
- felt, cdi, mmi, alert, tsunami, sig
- detail URL, event URL
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.ingest.base import BaseProvider, FetchResult, ProviderUnavailable


class UsgsProvider(BaseProvider):
    name = "usgs"

    def __init__(self, feed_url: str | None = None) -> None:
        super().__init__()
        self.feed_url = feed_url or settings.usgs_feed_url

    async def fetch(self) -> FetchResult:
        try:
            data = await self.get_json(self.feed_url)
        except ProviderUnavailable:
            raise
        except Exception as exc:  # pragma: no cover
            raise ProviderUnavailable(f"usgs fetch error: {exc}") from exc

        features = data.get("features", []) if isinstance(data, dict) else []
        records: list[dict[str, Any]] = []
        for feature in features:
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
