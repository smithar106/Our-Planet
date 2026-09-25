"""NASA FIRMS Area API ingestion (VIIRS_NOAA20_NRT / VIIRS_NOAA21_NRT).

FIRMS returns individual thermal-anomaly detections. We do NOT depend on
VIIRS_SNPP_NRT. The MAP key is stored server-side only.

The Area API returns CSV. Columns (VIIRS):
  latitude, longitude, bright_ti4, scan, track, acq_date, acq_time,
  satellite, instrument, confidence, version, bright_ti5, frp, daynight

When no MAP key is configured, fetch() raises ProviderUnavailable so the
pipeline can degrade gracefully; tests and local dev use fixtures instead.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.ingest.base import BaseProvider, FetchResult, ProviderUnavailable


class FirmsProvider(BaseProvider):
    name = "firms"

    SOURCES = ("VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT")

    def __init__(self, api_url: str | None = None, map_key: str | None = None) -> None:
        super().__init__()
        self.api_url = api_url or settings.firms_api_url
        self.map_key = map_key if map_key is not None else settings.nasa_firms_map_key

    def _url(self, source: str) -> str:
        return f"{self.api_url}/{self.map_key}/{source}/world/1"

    async def fetch(self) -> FetchResult:
        if not self.map_key:
            raise ProviderUnavailable("firms unavailable: NASA_FIRMS_MAP_KEY not configured")

        records: list[dict[str, Any]] = []
        for source in self.SOURCES:
            text = await self.get_text(self._url(source))
            for row in self._parse_csv(text, source):
                records.append(row)
        return FetchResult(provider=self.name, records=records)

    @staticmethod
    def _parse_csv(text: str, source: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(text))
        rows: list[dict[str, Any]] = []
        for row in reader:
            try:
                lat = float(row.get("latitude", ""))
                lon = float(row.get("longitude", ""))
                acq_date = row.get("acq_date", "")
                acq_time = row.get("acq_time", "0000")
                acq_dt = _parse_acq(acq_date, acq_time)
                frp = _to_float(row.get("frp"))
                confidence = row.get("confidence", "").strip().lower()
                rows.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "bright_ti4": _to_float(row.get("bright_ti4")),
                        "scan": _to_float(row.get("scan")),
                        "track": _to_float(row.get("track")),
                        "acq_date": acq_date,
                        "acq_time": acq_time,
                        "satellite": row.get("satellite", source),
                        "instrument": row.get("instrument", "VIIRS"),
                        "confidence": confidence,
                        "frp": frp,
                        "daynight": row.get("daynight", ""),
                        "acquired_at": acq_dt,
                    }
                )
            except (ValueError, TypeError):  # pragma: no cover - malformed row
                continue
        return rows


def _to_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _parse_acq(acq_date: str, acq_time: str) -> datetime:
    # acq_date = YYYY-MM-DD, acq_time = HHMM (UTC)
    try:
        hour = int(acq_time[:2])
        minute = int(acq_time[2:4])
        return datetime.strptime(acq_date, "%Y-%m-%d").replace(hour=hour, minute=minute, tzinfo=UTC)
    except (ValueError, IndexError):  # pragma: no cover
        return datetime.now(UTC)
