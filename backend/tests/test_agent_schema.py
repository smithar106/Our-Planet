"""Agent output schema + no-LLM behavior tests."""

from app.agent.llm import llm_available
from app.agent.tools import TOOL_DEFINITIONS
from app.constants import PROVIDERS


def test_llm_not_configured_in_tests():
    assert not llm_available()


def test_tool_definitions_are_valid():
    names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    assert "get_event" in names
    assert "get_nearby_events" in names
    assert "get_global_summary" in names


def test_tools_are_read_only():
    # No tool should mention write/create/update/delete mutations.
    forbidden = ("create", "update", "delete", "insert", "write", "publish")
    for t in TOOL_DEFINITIONS:
        desc = t["function"].get("description", "").lower()
        for word in forbidden:
            assert word not in desc, f"tool {t['function']['name']} has forbidden word {word}"


def test_providers_vocabulary():
    assert PROVIDERS == {"usgs", "eonet", "firms"}


async def test_investigate_without_llm_returns_fallback(session):
    from app.agent.investigate import investigate_event
    from app.models import Event

    event = Event(
        id="evt_x",
        source="usgs",
        source_id="usgs_x",
        category="earthquake",
        title="M6.0 earthquake",
        significance_score=60.0,
        significance_tier="SIGNIFICANT",
        change_type="NEW",
        metrics={"magnitude": 6.0, "depth_km": 10.0},
    )
    result = await investigate_event(session, event)
    assert result.status == "fallback"
    assert result.grounded is True
    # Output schema keys are present.
    for key in ("headline", "summary", "why_notable", "watch_next", "source_claims"):
        assert key in result.output
