"""Web search tools.

Two providers are supported:
  * Tavily        – used when TAVILY_API_KEY is configured (best quality).
  * DuckDuckGo    – zero-config fallback so the app runs out of the box.

Each tool exposes an async ``search(query, max_results)`` coroutine returning a
list of normalised result dicts: {title, url, content}.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List

from ..config import settings


class BaseSearchTool:
    name: str = "base"

    async def search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        raise NotImplementedError


class TavilySearchTool(BaseSearchTool):
    name = "tavily_search"

    def __init__(self) -> None:
        from tavily import TavilyClient

        self._client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    async def search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        def _run() -> List[Dict[str, str]]:
            resp = self._client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
            )
            results = []
            for item in resp.get("results", []):
                results.append(
                    {
                        "title": item.get("title", "") or item.get("url", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                    }
                )
            return results

        return await asyncio.to_thread(_run)


class DuckDuckGoSearchTool(BaseSearchTool):
    name = "duckduckgo_search"

    async def search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        def _run() -> List[Dict[str, str]]:
            # ``ddgs`` is the maintained successor of ``duckduckgo_search``.
            try:
                from ddgs import DDGS
            except ImportError:  # pragma: no cover - older package name
                from duckduckgo_search import DDGS  # type: ignore

            results = []
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=max_results):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("href", "") or item.get("url", ""),
                            "content": item.get("body", "") or item.get("snippet", ""),
                        }
                    )
            return results

        return await asyncio.to_thread(_run)


def get_search_tool() -> BaseSearchTool:
    """Choose a search provider based on configuration."""
    provider = settings.SEARCH_PROVIDER.lower()
    if provider == "tavily" or (provider == "auto" and settings.TAVILY_API_KEY):
        return TavilySearchTool()
    return DuckDuckGoSearchTool()
