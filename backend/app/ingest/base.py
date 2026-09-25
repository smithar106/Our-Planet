"""Ingest provider base classes."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("planet.ingest")


class ProviderError(Exception):
    pass


class ProviderUnavailable(ProviderError):
    """Raised when a provider is unreachable or explicitly disabled."""


@dataclass
class FetchResult:
    provider: str
    records: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: float = field(default_factory=time.time)
    ok: bool = True
    error: str | None = None


class BaseProvider:
    """Common HTTP fetching with bounded retries + exponential backoff.

    A failed provider must never prevent other providers from running, so
    callers catch ProviderError and continue.
    """

    name: str = "base"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _client_get(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=settings.http_timeout_seconds,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        client = await self._client_get()
        last_exc: Exception | None = None
        for attempt in range(settings.http_max_retries):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code in (401, 403, 404):
                    raise ProviderUnavailable(f"{self.name} request rejected ({exc.response.status_code})") from exc
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exc = exc
            backoff = min(2**attempt, 8)
            logger.warning("%s fetch attempt %s failed: %s", self.name, attempt + 1, last_exc)
            await asyncio.sleep(backoff)
        raise ProviderUnavailable(f"{self.name} fetch failed after retries: {last_exc}")

    async def get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        client = await self._client_get()
        last_exc: Exception | None = None
        for attempt in range(settings.http_max_retries):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code in (401, 403, 404):
                    raise ProviderUnavailable(f"{self.name} request rejected ({exc.response.status_code})") from exc
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exc = exc
            await asyncio.sleep(min(2**attempt, 8))
        raise ProviderUnavailable(f"{self.name} fetch failed after retries: {last_exc}")

    async def fetch(self) -> FetchResult:
        raise NotImplementedError
