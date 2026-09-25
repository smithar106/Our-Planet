"""State / change detection.

Compares the normalized incoming event against the persisted prior state to
classify the transition as one of:
  NEW, UPDATED, ESCALATING, DE-ESCALATING, UNCHANGED, CLOSED

This is deterministic and never consults the LLM. It powers the UI's
"NEW 12 MIN AGO", "ESCALATING", "UPDATED" labels.
"""

from __future__ import annotations

from typing import Any

# Score delta (absolute) that qualifies as escalation / de-escalation.
ESCALATION_DELTA = 5.0


def detect_change(prior: dict[str, Any] | None, new: dict[str, Any]) -> str:
    """Classify the state transition between prior and new event state.

    `prior` and `new` are dicts containing at least:
      status, significance_score, significance_tier, metrics, geometry,
      last_observed_at.
    """
    if prior is None:
        return "NEW"

    prior_status = prior.get("status", "open")
    new_status = new.get("status", "open")

    if new_status == "closed" and prior_status != "closed":
        return "CLOSED"
    if prior_status == "closed" and new_status == "open":
        return "UPDATED"  # provider reopened the event

    old_score = float(prior.get("significance_score") or 0.0)
    new_score = float(new.get("significance_score") or 0.0)
    delta = new_score - old_score

    if delta >= ESCALATION_DELTA:
        return "ESCALATING"
    if delta <= -ESCALATION_DELTA:
        return "DE-ESCALATING"

    if _meaningful_change(prior, new):
        return "UPDATED"

    return "UNCHANGED"


def _meaningful_change(prior: dict[str, Any], new: dict[str, Any]) -> bool:
    """True when observable fields changed even if the score did not."""
    if prior.get("last_observed_at") != new.get("last_observed_at"):
        return True
    if _normalize_geometry(prior.get("geometry")) != _normalize_geometry(new.get("geometry")):
        return True
    if _normalize_metrics(prior.get("metrics")) != _normalize_metrics(new.get("metrics")):
        return True
    if prior.get("title") != new.get("title"):
        return True
    return False


def _normalize_geometry(geometry: Any) -> Any:
    if geometry is None:
        return None
    if isinstance(geometry, dict):
        return {k: _normalize_geometry(v) for k, v in sorted(geometry.items())}
    if isinstance(geometry, list):
        return [_normalize_geometry(x) for x in geometry]
    return geometry


def _normalize_metrics(metrics: Any) -> Any:
    if metrics is None:
        return None
    if isinstance(metrics, dict):
        return {k: _normalize_metrics(v) for k, v in sorted(metrics.items())}
    if isinstance(metrics, list):
        return [_normalize_metrics(x) for x in metrics]
    return metrics
