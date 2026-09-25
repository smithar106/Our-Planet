"""Deterministic fallback explanation.

When LLM generation fails validation (or no LLM is configured), we publish a
deterministic description built ONLY from verified fields. The public site
never depends on the LLM succeeding — AI failure yields "less sophisticated
but still correct".
"""

from __future__ import annotations

from typing import Any


def deterministic_description(event: Any) -> dict[str, Any]:
    """Build a structured, source-grounded description from event fields only."""
    metrics = event.metrics or {}
    headline = event.title or f"{event.category} event"
    summary_parts: list[str] = []

    if event.category == "earthquake":
        mag = metrics.get("magnitude")
        depth = metrics.get("depth_km")
        if mag is not None:
            summary_parts.append(f"A magnitude {mag} earthquake was reported by USGS")
            if event.latitude is not None and event.longitude is not None:
                summary_parts.append(f"near {round(event.latitude, 2)}, {round(event.longitude, 2)}")
            if event.last_observed_at is not None:
                summary_parts.append(f"at {event.last_observed_at.isoformat()}")
            if depth is not None:
                summary_parts.append(f"at a depth of {depth} km")
    elif event.category == "wildfire":
        count = metrics.get("detection_count")
        if count is not None:
            summary_parts.append(f"PLANET identified a thermal-anomaly cluster with {count} detections")
            summary_parts.append("detected by NASA FIRMS (satellite thermal anomalies, not a confirmed wildfire)")
    else:
        summary_parts.append(f"A {event.category} event was reported by {event.source.upper()}")

    summary_parts.append(
        f"PLANET assigned it a significance score of {round(event.significance_score, 1)} "
        f"({event.significance_tier}) based on its available source attributes."
    )

    return {
        "headline": headline,
        "summary": " ".join(summary_parts) + ".",
        "why_notable": [
            f"Deterministic significance score {round(event.significance_score, 1)} "
            f"({event.significance_tier}) from category-specific scoring."
        ],
        "watch_next": [],
        "source_claims": [
            {
                "source": event.source,
                "url": event.source_url,
                "claim": "Event attributes derived from provider record.",
            }
        ],
        "grounded": True,
        "deterministic": True,
    }
