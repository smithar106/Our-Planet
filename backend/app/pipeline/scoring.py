"""Deterministic significance scoring.

PLANET's significance score is an application-level PRIORITIZATION score
(0-100), NOT an official hazard/risk classification. The formulas are
transparent and category-specific, and are documented in the methodology page.

Design goals:
- deterministic (no LLM involvement)
- strongly nonlinear for magnitude
- no fabrication of certainty: missing inputs contribute zero, never negative
"""

from __future__ import annotations

from typing import Any

from app.constants import clamp, tier_for_score


def score_event(category: str, metrics: dict[str, Any], raw_severity: dict[str, Any] | None = None) -> float:
    """Return a 0-100 significance score for a normalized event."""
    sev = raw_severity or {}
    if category == "earthquake":
        score = _score_earthquake(metrics, sev)
    elif category == "wildfire" and "detection_count" in metrics:
        # FIRMS thermal-anomaly clusters carry detection metrics.
        score = _score_wildfire(metrics)
    else:
        score = _score_generic(category, metrics)
    return round(clamp(score), 2)


def score_and_tier(
    category: str, metrics: dict[str, Any], raw_severity: dict[str, Any] | None = None
) -> tuple[float, str]:
    score = score_event(category, metrics, raw_severity)
    return score, tier_for_score(score)


# ---------------------------------------------------------------------------
# Earthquake
# ---------------------------------------------------------------------------


def _score_earthquake(metrics: dict[str, Any], sev: dict[str, Any]) -> float:
    mag = _to_float(metrics.get("magnitude", sev.get("magnitude")))
    depth = _to_float(metrics.get("depth_km", sev.get("depth_km")))
    felt = _to_float(metrics.get("felt", sev.get("felt")))
    usgs_sig = _to_float(metrics.get("usgs_significance", sev.get("usgs_significance")))
    alert = metrics.get("alert", sev.get("alert"))
    tsunami = _to_float(metrics.get("tsunami", sev.get("tsunami")))

    mag_component = _magnitude_component(mag)  # 0-55
    depth_component = _depth_component(depth)  # 0-10
    felt_component = _felt_component(felt)  # 0-10
    sig_component = _usgs_sig_component(usgs_sig)  # 0-15
    alert_component = _alert_component(alert)  # 0-10
    tsunami_component = 10.0 if tsunami == 1 else 0.0  # 0-10

    return mag_component + depth_component + felt_component + sig_component + alert_component + tsunami_component


def _magnitude_component(mag: float | None) -> float:
    """Strongly nonlinear magnitude component (0-60).

    Anchored so the score scales roughly as (mag/9)^3.5: small quakes score
    almost nothing while each additional unit at the high end adds much more.
    Documented on the methodology page.
    """
    if mag is None:
        return 0.0
    if mag <= 0:
        return 0.0
    return clamp(60.0 * (mag / 9.0) ** 3.5, 0.0, 60.0)


def _depth_component(depth: float | None) -> float:
    """Shallow events have greater surface impact. Deep events score low."""
    if depth is None:
        return 0.0
    if depth < 0:
        return 0.0
    if depth <= 10:
        return 10.0
    if depth <= 35:
        return 8.0
    if depth <= 70:
        return 5.0
    if depth <= 150:
        return 2.0
    return 0.0


def _felt_component(felt: float | None) -> float:
    if felt is None:
        return 0.0
    return clamp(felt / 100.0 * 10.0, 0.0, 10.0)


def _usgs_sig_component(sig: float | None) -> float:
    if sig is None:
        return 0.0
    return clamp(sig / 1000.0 * 15.0, 0.0, 15.0)


def _alert_component(alert: Any) -> float:
    if alert is None:
        return 0.0
    a = str(alert).lower()
    return {"green": 0.0, "yellow": 4.0, "orange": 7.0, "red": 10.0}.get(a, 0.0)


# ---------------------------------------------------------------------------
# Wildfire (FIRMS thermal-anomaly clusters)
# ---------------------------------------------------------------------------


def _score_wildfire(metrics: dict[str, Any]) -> float:
    detections = _to_float(metrics.get("detection_count", 0))
    mean_frp = _to_float(metrics.get("mean_frp", 0))
    max_frp = _to_float(metrics.get("max_frp", 0))
    confidence = _to_float(metrics.get("confidence", 0))
    growth = _to_float(metrics.get("growth_ratio", 0))

    det_component = _detection_component(detections)  # 0-40
    frp_component = _frp_component(max_frp)  # 0-25
    conf_component = clamp(confidence, 0.0, 100.0) / 100.0 * 10.0  # 0-10
    growth_component = _growth_component(growth)  # 0-15
    persistence_component = clamp((mean_frp + max_frp) / 2.0 / 100.0 * 10.0, 0.0, 10.0)  # 0-10

    return det_component + frp_component + conf_component + growth_component + persistence_component


def _detection_component(detections: float) -> float:
    if detections <= 0:
        return 0.0
    import math

    return clamp(40.0 * (math.log10(detections + 1) / math.log10(1001)), 0.0, 40.0)


def _frp_component(max_frp: float) -> float:
    return clamp(max_frp / 100.0 * 25.0, 0.0, 25.0)


def _growth_component(growth_ratio: float) -> float:
    # growth_ratio: current/previous detection count. >1 means growing.
    if growth_ratio is None or growth_ratio <= 1:
        return 0.0
    return clamp(15.0 * (growth_ratio - 1.0) / 2.0, 0.0, 15.0)


# ---------------------------------------------------------------------------
# Generic / EONET events
# ---------------------------------------------------------------------------

_CATEGORY_WEIGHT: dict[str, float] = {
    "volcano": 30.0,
    "storm": 22.0,
    "flood": 22.0,
    "wildfire": 25.0,
    "landslide": 18.0,
    "drought": 12.0,
    "ice": 8.0,
    "earthquake": 30.0,
    "other": 10.0,
}


def _score_generic(category: str, metrics: dict[str, Any]) -> float:
    base = _CATEGORY_WEIGHT.get(category, 10.0)
    sources = _to_float(metrics.get("sources_count", 0))
    persistence = _to_float(metrics.get("persistence_hours", 0))

    src_component = clamp(sources * 2.0, 0.0, 10.0)
    persistence_component = clamp(persistence / 24.0 * 20.0, 0.0, 20.0)

    return base + src_component + persistence_component


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
