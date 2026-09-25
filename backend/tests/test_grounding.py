"""Grounding validation tests — the safety architecture must actually reject
unsupported output."""

from app.agent.grounding import validate_grounding

FACTS = {
    "significance_score": 61.5,
    "confidence": 50.0,
    "metrics": {"magnitude": 6.2, "depth_km": 10.0, "felt": 40},
}


def _gen(**overrides):
    base = {
        "headline": "M6.2 earthquake detected",
        "summary": "A magnitude 6.2 earthquake was reported at a depth of 10 km.",
        "why_notable": ["PLANET flagged it with score 61.5"],
        "watch_next": [],
        "source_claims": [{"source": "usgs", "url": "https://x", "claim": "magnitude 6.2"}],
    }
    base.update(overrides)
    return base


def test_supported_numbers_pass():
    result = validate_grounding(_gen(), FACTS)
    assert result.passed


def test_unsupported_number_fails():
    result = validate_grounding(_gen(summary="Magnitude 9.9 quake killed 5000 people"), FACTS)
    assert not result.passed
    assert any("unsupported number" in i for i in result.issues)


def test_restricted_word_fails():
    result = validate_grounding(_gen(summary="This is a record earthquake"), FACTS)
    assert not result.passed
    assert any("record" in i for i in result.issues)


def test_catastrophic_word_fails():
    result = validate_grounding(_gen(headline="Catastrophic quake strikes"), FACTS)
    assert not result.passed


def test_source_claim_missing_source_fails():
    result = validate_grounding(_gen(source_claims=[{"claim": "no source"}]), FACTS)
    assert not result.passed


def test_neutral_language_passes():
    result = validate_grounding(
        _gen(
            summary="PLANET flagged this event as statistically notable because of its magnitude.",
            why_notable=["PLANET flagged this event as statistically notable"],
        ),
        FACTS,
    )
    assert result.passed
