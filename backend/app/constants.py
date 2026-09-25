"""Controlled vocabularies and constants for PLANET.

Centralizing these makes the data-honesty rules enforceable:
- categories are a fixed set (not arbitrary strings)
- tiers are a fixed set
- change types are a fixed set
"""

from __future__ import annotations

# Normalized event categories (controlled vocabulary).
CATEGORIES: frozenset[str] = frozenset(
    {
        "earthquake",
        "wildfire",
        "volcano",
        "storm",
        "flood",
        "landslide",
        "drought",
        "ice",
        "other",
    }
)

# Significance tiers, ordered from lowest to highest.
SIGNIFICANCE_TIERS: tuple[str, ...] = (
    "ROUTINE",
    "NOTABLE",
    "SIGNIFICANT",
    "MAJOR",
)

TIER_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (75.0, "MAJOR"),
    (50.0, "SIGNIFICANT"),
    (25.0, "NOTABLE"),
    (0.0, "ROUTINE"),
)

# Change / state transition types.
CHANGE_TYPES: frozenset[str] = frozenset({"NEW", "UPDATED", "ESCALATING", "DE-ESCALATING", "UNCHANGED", "CLOSED"})

# Event statuses.
EVENT_STATUSES: frozenset[str] = frozenset({"open", "closed"})

# Providers.
PROVIDERS: frozenset[str] = frozenset({"usgs", "eonet", "firms"})


def tier_for_score(score: float) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "ROUTINE"


# Categories the FIRMS thermal-anomaly detector should be described as.
# Important honesty rule: FIRMS reports thermal anomalies / fire detections,
# NOT confirmed wildfires.
FIRMS_CATEGORY = "wildfire"


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))
