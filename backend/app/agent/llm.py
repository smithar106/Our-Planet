"""LLM provider abstraction.

OpenAI-compatible chat-completions client. Not hardwired to one model:
LLM_PROVIDER / LLM_MODEL / LLM_API_KEY / LLM_BASE_URL select the backend.
DeepSeek's API is OpenAI-compatible, so it works out of the box.

The application MUST remain functional with no LLM configured — callers
should check `llm_available()` and fall back to deterministic paths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("planet.agent.llm")

_DEFAULT_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com/v1",
}


class LLMUnavailable(Exception):
    pass


class LLMError(Exception):
    pass


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)


def llm_available() -> bool:
    return settings.llm_configured


def _base_url() -> str:
    if settings.llm_base_url:
        return settings.llm_base_url.rstrip("/")
    return _DEFAULT_BASE_URLS.get(settings.llm_provider, settings.llm_base_url or "")


class LLMClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=_base_url(),
                timeout=settings.llm_timeout_seconds,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> ChatResponse:
        if not llm_available():
            raise LLMUnavailable("no LLM configured")

        payload: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        client = await self._get_client()
        try:
            resp = await client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMError("LLM request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"LLM HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

        return _parse_response(data)


def _parse_response(data: dict[str, Any]) -> ChatResponse:
    usage = data.get("usage") or {}
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")

    tool_calls: list[ToolCall] = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            import json

            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args))

    return ChatResponse(content=content, tool_calls=tool_calls, usage=usage)
