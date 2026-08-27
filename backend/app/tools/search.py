"""Web search tool with a provider-fallback chain: Tavily -> DuckDuckGo.

Design notes
------------
- Tavily is purpose-built for agent research (relevance ranking + content
  extraction), so it is the primary provider when a key is configured.
- DuckDuckGo (``ddgs``) is keyless and acts as a resilience fallback when Tavily
  is unavailable, rate-limited, or errors out. This gives the agent graceful
  degradation instead of a hard failure mid-run.
- Everything is async at the call site. The DDG client is synchronous, so it is
  offloaded to a worker thread to avoid blocking the event loop.
- Failures are contained: a single query failing returns an empty list rather
  than aborting the whole research run.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    content: str
    provider: str

    def as_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "provider": self.provider,
        }


class SearchError(RuntimeError):
    """Raised when a search provider fails after retries."""


# --------------------------------------------------------------------------- #
# Tavily provider
# --------------------------------------------------------------------------- #
@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    reraise=True,
)
async def _tavily_search(query: str, max_results: int) -> list[SearchResult]:
    from tavily import AsyncTavilyClient  # local import: optional dependency path

    settings = get_settings()
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    response = await asyncio.wait_for(
        client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=False,
        ),
        timeout=settings.search_timeout,
    )
    results: list[SearchResult] = []
    for item in response.get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", "") or item.get("url", ""),
                url=item.get("url", ""),
                content=item.get("content", "") or "",
                provider="tavily",
            )
        )
    return results


# --------------------------------------------------------------------------- #
# DuckDuckGo provider (fallback, keyless)
# --------------------------------------------------------------------------- #
def _ddg_search_sync(query: str, max_results: int) -> list[SearchResult]:
    # The package was renamed duckduckgo_search -> ddgs; support both.
    try:
        from ddgs import DDGS  # type: ignore
    except ImportError:  # pragma: no cover - environment dependent
        from duckduckgo_search import DDGS  # type: ignore

    results: list[SearchResult] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("href", "") or item.get("url", ""),
                    content=item.get("body", "") or "",
                    provider="duckduckgo",
                )
            )
    return results


async def _ddg_search(query: str, max_results: int) -> list[SearchResult]:
    settings = get_settings()
    return await asyncio.wait_for(
        asyncio.to_thread(_ddg_search_sync, query, max_results),
        timeout=settings.search_timeout,
    )


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
async def web_search(query: str, max_results: int | None = None) -> list[SearchResult]:
    """Run a single web search, falling back across providers.

    Never raises for a single-query failure: returns an empty list so the agent
    can continue with the results it did gather.
    """
    settings = get_settings()
    limit = max_results or settings.max_results_per_query
    query = query.strip()
    if not query:
        return []

    if settings.has_tavily:
        try:
            results = await _tavily_search(query, limit)
            if results:
                return results
            logger.info("tavily returned no results, trying fallback", extra={"query": query})
        except Exception as exc:  # noqa: BLE001 - deliberate degradation boundary
            logger.warning(
                "tavily search failed, falling back to duckduckgo",
                extra={"query": query, "error": str(exc)},
            )

    try:
        return await _ddg_search(query, limit)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "all search providers failed for query",
            extra={"query": query, "error": str(exc)},
        )
        return []


async def batch_search(
    queries: list[str], max_results: int | None = None
) -> dict[str, list[SearchResult]]:
    """Run several queries concurrently. Returns a query -> results mapping."""
    unique = list(dict.fromkeys(q.strip() for q in queries if q.strip()))
    if not unique:
        return {}
    tasks = [web_search(q, max_results) for q in unique]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    out: dict[str, list[SearchResult]] = {}
    for query, result in zip(unique, gathered):
        if isinstance(result, Exception):
            logger.warning("query failed in batch", extra={"query": query, "error": str(result)})
            out[query] = []
        else:
            out[query] = result
    return out
