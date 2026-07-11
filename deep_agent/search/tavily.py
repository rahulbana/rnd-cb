"""Tavily search provider."""
from __future__ import annotations

from deep_agent.models.schemas import SearchResult
from deep_agent.search.base import SearchClient
from deep_agent.utils.logging import get_logger
from deep_agent.utils.retry import http_retry

logger = get_logger("search.tavily")


class TavilySearchClient(SearchClient):
    """Search client backed by the Tavily API."""

    name = "tavily"

    def __init__(self, api_key: str, max_results: int = 6) -> None:
        super().__init__(max_results=max_results)
        if not api_key:
            raise ValueError("TAVILY_API_KEY is required for the Tavily provider.")
        # Imported lazily so the dependency is only needed when selected.
        from tavily import TavilyClient

        self._client = TavilyClient(api_key=api_key)

    @http_retry(max_attempts=3)
    def _raw_search(self, query: str, max_results: int) -> dict:
        return self._client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
        )

    def search(self, query: str, max_results: int | None = None) -> list[SearchResult]:
        limit = max_results or self.max_results
        logger.info("Tavily search: %r (max=%d)", query, limit)
        try:
            payload = self._raw_search(query, limit)
        except Exception as exc:  # noqa: BLE001 - surfaced as empty result set
            logger.error("Tavily search failed for %r: %s", query, exc)
            return []

        results = [
            SearchResult(
                title=item.get("title", "") or item.get("url", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                score=item.get("score"),
                provider=self.name,
                query=query,
            )
            for item in payload.get("results", [])
            if item.get("url")
        ]
        logger.info("Tavily returned %d results for %r", len(results), query)
        return results
