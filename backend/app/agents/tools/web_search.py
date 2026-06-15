"""Deep web search tool used by agents to gather trending topics and sources.

Uses Tavily when TAVILY_API_KEY is configured (real, citable sources). Falls back
to a deterministic stub so the app remains runnable in local/dev environments
without external keys.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TAVILY_URL = "https://api.tavily.com/search"


async def web_search(query: str, *, recent_only: bool = False, max_results: int | None = None) -> list[dict]:
    """Run a web search and return a list of source dicts.

    Each source: {title, url, snippet, published}.
    `recent_only` restricts results to roughly the last day for trend discovery.
    """
    max_results = max_results or settings.search_max_results

    if settings.has_tavily:
        try:
            return await _tavily_search(query, recent_only=recent_only, max_results=max_results)
        except Exception as exc:  # pragma: no cover - network failures
            logger.warning("Tavily search failed (%s); using fallback results.", exc)

    return _fallback_results(query, max_results)


async def _tavily_search(query: str, *, recent_only: bool, max_results: int) -> list[dict]:
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
    }
    if recent_only:
        payload["topic"] = "news"
        payload["days"] = 1

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(TAVILY_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title", "").strip() or item.get("url", ""),
                "url": item.get("url", ""),
                "snippet": (item.get("content") or "").strip()[:500],
                "published": item.get("published_date"),
            }
        )
    return results


def _fallback_results(query: str, max_results: int) -> list[dict]:
    """Offline placeholder sources so the pipeline still produces output."""
    logger.info("Using fallback web search results for query: %s", query)
    base = [
        {
            "title": f"Industry overview: {query}",
            "url": "https://example.com/overview",
            "snippet": (
                f"A general overview related to '{query}'. Configure TAVILY_API_KEY to "
                "fetch live, citable sources from the last 24 hours."
            ),
            "published": None,
        },
        {
            "title": f"Recent discussion on {query}",
            "url": "https://example.com/discussion",
            "snippet": f"Community discussion and trends around '{query}'.",
            "published": None,
        },
        {
            "title": f"Best practices for {query}",
            "url": "https://example.com/best-practices",
            "snippet": f"Actionable best practices and tips covering '{query}'.",
            "published": None,
        },
    ]
    return base[:max_results]
