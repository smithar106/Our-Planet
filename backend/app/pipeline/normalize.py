"""Normalization: convert heterogeneous provider records into a common model.

The normalized model never discards source-specific detail — raw payloads are
preserved verbatim on the source record for audit/debugging.

Data-honesty rules enforced here:
- missing values stay missing (None), never silently coerced to 0/false
- category uses a controlled vocabulary; unknown categories map to "other"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.constants import CATEGORIES, clamp


@dataclass
class NormalizedEvent:
    source: str
    source_id: str
    category: str
    subtype: str | None
    title: str
    latitude: float | None
    longitude: float | None
    geometry: dict[str, Any] | None
    first_observed_at: datetime
    last_observed_at: datetime
    status: str
    raw_severity: dict[str, Any] | None
    confidence: float
    metrics: dict[str, Any]
    source_url: str | None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_id": self.source_id,
            "category": self.category,
            "subtype": self.subtype,
            "title": self.title,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "geometry": self.geometry,
            "first_observed_at": self.first_observed_at,
            "last_observed_at": self.last_observed_at,
            "status": self.status,
            "raw_severity": self.raw_severity,
            "confidence": self.confidence,
            "metrics": self.metrics,
            "source_url": self.source_url,
            "raw_payload": self.raw_payload,
        }


def _as_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _coerce_category(category: str | None) -> str:
    if not category:
        return "other"
    c = category.strip().lower()
    if c in CATEGORIES:
        return c
    return "other"


# EONET category id -> controlled vocabulary.
EONET_CATEGORY_MAP: dict[str, str] = {
    "earthquakes": "earthquake",
    "wildfires": "wildfire",
    "volcanoes": "volcano",
    "severeStorms": "storm",
    "floods": "flood",
    "landslides": "landslide",
    "drought": "drought",
    "seaLakeIce": "ice",
    "dustHaze": "other",
    "manmade": "other",
    "snow": "ice",
    "tempExtremes": "other",
    "waterColor": "other",
}


def normalize_usgs(record: dict[str, Any]) -> NormalizedEvent | None:
    props = record.get("properties") or {}
    source_id = str(record.get("id") or "")
    if not source_id:
        return None

    mag = props.get("mag")
    mag_type = props.get("magType")
    place = props.get("place") or f"M{mag} earthquake" if mag is not None else "Earthquake"

    title = f"M{mag} earthquake" if mag is not None else "Earthquake"
    if place and place != title:
        title = f"{title} — {place}"

    occurred = _as_dt(props.get("time"))
    updated = _as_dt(props.get("updated")) or occurred
    if occurred is None:
        occurred = datetime.now(UTC)
    if updated is None:
        updated = occurred

    depth = record.get("depth_km")
    raw_severity = {
        "magnitude": mag,
        "magnitude_type": mag_type,
        "depth_km": depth,
        "felt": props.get("felt"),
        "cdi": props.get("cdi"),
        "mmi": props.get("mmi"),
        "alert": props.get("alert"),
        "tsunami": _coerce_int(props.get("tsunami")),
        "usgs_significance": props.get("sig"),
    }

    metrics = {
        "magnitude": mag,
        "depth_km": depth,
        "felt": props.get("felt"),
        "cdi": props.get("cdi"),
        "mmi": props.get("mmi"),
        "alert": props.get("alert"),
        "tsunami": _coerce_int(props.get("tsunami")),
        "usgs_significance": props.get("sig"),
    }

    geometry = record.get("geometry")

    return NormalizedEvent(
        source="usgs",
        source_id=source_id,
        category="earthquake",
        subtype=mag_type,
        title=title,
        latitude=record.get("latitude"),
        longitude=record.get("longitude"),
        geometry=geometry,
        first_observed_at=occurred,
        last_observed_at=updated,
        status="open",
        raw_severity=raw_severity,
        confidence=_usgs_confidence(props),
        metrics=metrics,
        source_url=props.get("url"),
        raw_payload=record,
    )


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _usgs_confidence(props: dict[str, Any]) -> float:
    # Deterministic, source-derived confidence: prefer MMI, then CDI, else magnitude.
    mmi = props.get("mmi")
    if mmi is not None:
        return clamp(float(mmi) / 10.0 * 100.0)
    cdi = props.get("cdi")
    if cdi is not None:
        return clamp(float(cdi) / 10.0 * 100.0)
    return 50.0


def normalize_eonet(record: dict[str, Any]) -> NormalizedEvent | None:
    source_id = str(record.get("id") or "")
    if not source_id:
        return None

    title = record.get("title") or "EONET event"
    description = record.get("description")

    # EONET v3 may have a single category or a list.
    categories = record.get("categories") or []
    if isinstance(categories, dict):
        categories = [categories]
    cat_ids = [c.get("id") if isinstance(c, dict) else c for c in categories]
    category = _coerce_category(_map_eonet_category(cat_ids))
    subtype = _map_eonet_subtype(cat_ids)

    geometry = _normalize_eonet_geometry(record.get("geometry"))
    lat, lon = _extract_point(geometry)

    closed = record.get("closed") or record.get("status") == "closed"
    status = "closed" if closed else "open"

    # EONET geometry list may carry dated points; pick first/last.
    occurred = _as_dt(record.get("created")) or _as_dt(record.get("geometry_date"))
    updated = _as_dt(record.get("updated")) or occurred
    if occurred is None:
        occurred = datetime.now(UTC)
    if updated is None:
        updated = occurred

    sources = record.get("sources") or []
    source_url = None
    if isinstance(sources, list) and sources:
        first = sources[0]
        source_url = first.get("url") if isinstance(first, dict) else None

    return NormalizedEvent(
        source="eonet",
        source_id=source_id,
        category=category,
        subtype=subtype,
        title=title,
        latitude=lat,
        longitude=lon,
        geometry=geometry,
        first_observed_at=occurred,
        last_observed_at=updated,
        status=status,
        raw_severity=None,
        confidence=60.0,
        metrics={
            "description": description,
            "categories": cat_ids,
            "sources_count": len(sources) if isinstance(sources, list) else 0,
        },
        source_url=source_url,
        raw_payload=record,
    )


def _map_eonet_category(cat_ids: list[str]) -> str | None:
    for cid in cat_ids:
        if cid in EONET_CATEGORY_MAP:
            return EONET_CATEGORY_MAP[cid]
    return None


def _map_eonet_subtype(cat_ids: list[str]) -> str | None:
    # Preserve the first raw EONET category id as a subtype for transparency.
    for cid in cat_ids:
        return str(cid)
    return None


def _normalize_eonet_geometry(geometry: Any) -> dict[str, Any] | None:
    """EONET v3 geometry is a list of dated geometry objects. Return a single
    GeoJSON geometry (the most recent dated entry, else the first)."""
    if not geometry:
        return None
    if isinstance(geometry, dict):
        return geometry
    if isinstance(geometry, list):
        entries = [g for g in geometry if isinstance(g, dict)]
        if not entries:
            return None
        # Prefer the entry with the latest "date".
        entries.sort(key=lambda g: str(g.get("date") or ""))
        return entries[-1]
    return None


def _extract_point(geometry: dict[str, Any] | None) -> tuple[float | None, float | None]:
    if not geometry or not isinstance(geometry, dict):
        return None, None
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Point" and isinstance(coords, list) and len(coords) >= 2:
        try:
            return float(coords[1]), float(coords[0])
        except (ValueError, TypeError):
            return None, None
    if gtype == "Polygon" and isinstance(coords, list) and coords:
        ring = coords[0] if isinstance(coords[0], list) else coords
        if ring:
            first = ring[0]
            if isinstance(first, list) and len(first) >= 2:
                try:
                    return float(first[1]), float(first[0])
                except (ValueError, TypeError):
                    return None, None
    return None, None
