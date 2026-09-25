"""Significance scoring tests — verify determinism and nonlinearity."""

from app.constants import tier_for_score
from app.pipeline.scoring import score_event


def test_earthquake_magnitude_is_nonlinear():
    m3 = score_event("earthquake", {"magnitude": 3.0, "depth_km": 10.0})
    m4 = score_event("earthquake", {"magnitude": 4.0, "depth_km": 10.0})
    m7 = score_event("earthquake", {"magnitude": 7.0, "depth_km": 10.0})
    m8 = score_event("earthquake", {"magnitude": 8.0, "depth_km": 10.0})

    # 7 -> 8 gap must dwarf the 3 -> 4 gap.
    assert (m8 - m7) > (m4 - m3) * 3
    assert m8 > m7 > m4 > m3


def test_earthquake_shallow_scores_higher_than_deep():
    shallow = score_event("earthquake", {"magnitude": 6.0, "depth_km": 5.0})
    deep = score_event("earthquake", {"magnitude": 6.0, "depth_km": 300.0})
    assert shallow > deep


def test_tsunami_flag_adds_score():
    base = score_event("earthquake", {"magnitude": 7.0, "depth_km": 30.0, "tsunami": 0})
    flagged = score_event("earthquake", {"magnitude": 7.0, "depth_km": 30.0, "tsunami": 1})
    assert flagged > base


def test_score_is_deterministic():
    args = {"magnitude": 6.4, "depth_km": 40.0, "felt": 50}
    assert score_event("earthquake", args) == score_event("earthquake", args)


def test_score_bounded_0_100():
    assert 0 <= score_event("earthquake", {"magnitude": 9.9, "depth_km": 1.0}) <= 100
    assert 0 <= score_event("earthquake", {"magnitude": 1.0}) <= 100


def test_tiers():
    assert tier_for_score(90) == "MAJOR"
    assert tier_for_score(60) == "SIGNIFICANT"
    assert tier_for_score(30) == "NOTABLE"
    assert tier_for_score(10) == "ROUTINE"


def test_wildfire_scoring_uses_detections_and_frp():
    small = score_event("wildfire", {"detection_count": 2, "max_frp": 5.0, "confidence": 40})
    large = score_event("wildfire", {"detection_count": 500, "max_frp": 80.0, "confidence": 90})
    assert large > small
