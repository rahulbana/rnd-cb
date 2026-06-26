"""Tavily search provider (requires TAVILY_API_KEY)."""
from __future__ import annotations

import asyncio
from typing import List

from ...core.config import Settings
from ...core.exceptions import ConfigurationError, SearchProviderError
from ...schemas.source import RawResult
from .base import BaseSearchProvider


class TavilySearchProvider(BaseSearchProvider):
    name = "tavily"

    def __init__(self, settings: Settings) -> None:
        if not settings.tavily_api_key:
            raise ConfigurationError("TAVILY_API_KEY is required for the Tavily provider.")
        from tavily import TavilyClient

        self._client = TavilyClient(api_key=settings.tavily_api_key)

    async def search(self, query: str, max_results: int) -> List[RawResult]:
        def _run() -> List[RawResult]:
            resp = self._client.search(
                query=query, max_results=max_results, search_depth="advanced"
            )
            return [
                RawResult(
                    title=item.get("title") or item.get("url", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                )
                for item in resp.get("results", [])
            ]

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001 - normalise provider errors
            raise SearchProviderError(f"Tavily search failed: {exc}") from exc
