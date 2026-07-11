"""Search factory — returns a client for the configured search provider."""
from __future__ import annotations

from functools import lru_cache

from deep_agent.config import SearchProvider, get_settings
from deep_agent.search.base import SearchClient
from deep_agent.utils.logging import get_logger

logger = get_logger("search.factory")


@lru_cache(maxsize=1)
def get_search_client() -> SearchClient:
    """Return a cached search client for the configured provider."""

    settings = get_settings()
    logger.info("Initialising search provider=%s", settings.search_provider.value)

    if settings.search_provider is SearchProvider.TAVILY:
        from deep_agent.search.tavily import TavilySearchClient

        return TavilySearchClient(
            api_key=settings.tavily_api_key or "",
            max_results=settings.search_max_results,
        )

    if settings.search_provider is SearchProvider.SERPER:
        from deep_agent.search.serper import SerperSearchClient

        return SerperSearchClient(
            api_key=settings.serper_api_key or "",
            max_results=settings.search_max_results,
            timeout=settings.scrape_timeout_seconds,
        )

    raise ValueError(f"Unsupported search provider: {settings.search_provider}")
