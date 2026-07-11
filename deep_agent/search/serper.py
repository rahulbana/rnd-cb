"""Serper.dev (Google Search API) provider."""
from __future__ import annotations

import httpx

from deep_agent.models.schemas import SearchResult
from deep_agent.search.base import SearchClient
from deep_agent.utils.logging import get_logger
from deep_agent.utils.retry import http_retry

logger = get_logger("search.serper")

_SERPER_ENDPOINT = "https://google.serper.dev/search"


class SerperSearchClient(SearchClient):
    """Search client backed by the Serper.dev API."""

    name = "serper"

    def __init__(self, api_key: str, max_results: int = 6, timeout: int = 20) -> None:
        super().__init__(max_results=max_results)
        if not api_key:
            raise ValueError("SERPER_API_KEY is required for the Serper provider.")
        self._api_key = api_key
        self._timeout = timeout

    @http_retry(max_attempts=3)
    def _raw_search(self, query: str, max_results: int) -> dict:
        response = httpx.post(
            _SERPER_ENDPOINT,
            headers={
                "X-API-KEY": self._api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": max_results},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()

    def search(self, query: str, max_results: int | None = None) -> list[SearchResult]:
        limit = max_results or self.max_results
        logger.info("Serper search: %r (max=%d)", query, limit)
        try:
            payload = self._raw_search(query, limit)
        except Exception as exc:  # noqa: BLE001
            logger.error("Serper search failed for %r: %s", query, exc)
            return []

        results = [
            SearchResult(
                title=item.get("title", "") or item.get("link", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                score=None,
                provider=self.name,
                query=query,
            )
            for item in payload.get("organic", [])[:limit]
            if item.get("link")
        ]
        logger.info("Serper returned %d results for %r", len(results), query)
        return results
