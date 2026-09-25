"""Chat service tests — no-LLM path must return deterministic guidance."""

from app.chat.service import answer_question


async def test_chat_without_llm_is_deterministic(session):
    result = await answer_question(session, "What happened today?")
    assert result["deterministic"] is True
    assert "answer" in result
    assert "no LLM" in result["answer"].lower() or "unavailable" in result["answer"].lower()


async def test_chat_empty_question(session):
    result = await answer_question(session, "")
    assert result["deterministic"] is True


async def test_chat_too_long(session):
    result = await answer_question(session, "x" * 2000)
    assert result["deterministic"] is True
    assert "too long" in result["answer"].lower()
