"""NASA EONET API v3 ingestion.

EONET provides broader natural events (wildfires, severe storms, volcanoes,
floods, landslides, ice, dust/haze, drought, ...). Categories are NOT assumed
to always be present — we normalize only what the provider returns.
"""

from __future__ import annotations

from app.config import settings
from app.ingest.base import BaseProvider, FetchResult, ProviderUnavailable


class EonetProvider(BaseProvider):
    name = "eonet"

    def __init__(self, api_url: str | None = None) -> None:
        super().__init__()
        self.api_url = api_url or settings.eonet_api_url

    async def fetch(self) -> FetchResult:
        # EONET v3 "open" events (with geometry), limited to recent activity.
        params = {"status": "open", "limit": 50}
        try:
            data = await self.get_json(self.api_url, params=params)
        except ProviderUnavailable:
            raise
        except Exception as exc:  # pragma: no cover
            raise ProviderUnavailable(f"eonet fetch error: {exc}") from exc

        events = data.get("events", []) if isinstance(data, dict) else []
        return FetchResult(provider=self.name, records=events)
