"""Change-detection tests."""

from app.pipeline.state import detect_change


def _event(score=50.0, tier="SIGNIFICANT", status="open", metrics=None, geom=None, last="t1", title="T"):
    return {
        "status": status,
        "significance_score": score,
        "significance_tier": tier,
        "metrics": metrics or {"magnitude": 6.0},
        "geometry": geom,
        "last_observed_at": last,
        "title": title,
    }


def test_new_event():
    assert detect_change(None, _event()) == "NEW"


def test_unchanged():
    e = _event()
    assert detect_change(e, _event()) == "UNCHANGED"


def test_escalating_on_score_increase():
    before = _event(score=50.0)
    after = _event(score=58.0)
    assert detect_change(before, after) == "ESCALATING"


def test_deescalating_on_score_decrease():
    before = _event(score=60.0)
    after = _event(score=50.0)
    assert detect_change(before, after) == "DE-ESCALATING"


def test_updated_on_metric_change_without_score_change():
    before = _event(score=50.0, metrics={"magnitude": 6.0})
    after = _event(score=50.0, metrics={"magnitude": 6.1})
    assert detect_change(before, after) == "UPDATED"


def test_closed():
    before = _event(status="open")
    after = _event(status="closed")
    assert detect_change(before, after) == "CLOSED"


def test_reopened():
    before = _event(status="closed")
    after = _event(status="open")
    assert detect_change(before, after) == "UPDATED"
