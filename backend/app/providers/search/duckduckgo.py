"""DuckDuckGo search provider (no API key required)."""
from __future__ import annotations

import asyncio
from typing import List

from ...core.config import Settings
from ...core.exceptions import SearchProviderError
from ...schemas.source import RawResult
from .base import BaseSearchProvider


class DuckDuckGoSearchProvider(BaseSearchProvider):
    name = "duckduckgo"

    def __init__(self, settings: Settings) -> None:  # noqa: ARG002 - uniform signature
        pass

    async def search(self, query: str, max_results: int) -> List[RawResult]:
        def _run() -> List[RawResult]:
            # ``ddgs`` is the maintained successor of ``duckduckgo_search``.
            try:
                from ddgs import DDGS
            except ImportError:  # pragma: no cover - older package name
                from duckduckgo_search import DDGS  # type: ignore

            results: List[RawResult] = []
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=max_results):
                    results.append(
                        RawResult(
                            title=item.get("title", ""),
                            url=item.get("href", "") or item.get("url", ""),
                            content=item.get("body", "") or item.get("snippet", ""),
                        )
                    )
            return results

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001 - normalise provider errors
            raise SearchProviderError(f"DuckDuckGo search failed: {exc}") from exc
