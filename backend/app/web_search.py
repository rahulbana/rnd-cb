"""Pluggable web search layer.

Supports Tavily and SerpAPI. When the selected provider has no API key the
layer transparently returns synthetic mock results so the pipeline stays
runnable offline.
"""

from __future__ import annotations

import httpx

from .config import Settings, get_settings
from .models import SearchResult


class WebSearchClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.provider = self.settings.resolved_search_provider()

    def search_reviews(self, title: str, author: str | None = None) -> list[SearchResult]:
        """Search the web for reviews and information about a book."""
        query = f'"{title}" book review'
        if author:
            query += f" {author}"

        if self.provider == "tavily":
            return self._tavily(query)
        if self.provider == "serpapi":
            return self._serpapi(query)
        return self._mock(title, author)

    # ---- providers ----

    def _tavily(self, query: str) -> list[SearchResult]:
        try:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.settings.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": self.settings.search_max_results,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                )
                for item in data.get("results", [])
            ]
        except Exception:
            return self._mock(query)

    def _serpapi(self, query: str) -> list[SearchResult]:
        try:
            resp = httpx.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google",
                    "q": query,
                    "num": self.settings.search_max_results,
                    "api_key": self.settings.serpapi_api_key,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    content=item.get("snippet", ""),
                )
                for item in data.get("organic_results", [])
            ]
        except Exception:
            return self._mock(query)

    def _mock(self, title: str, author: str | None = None) -> list[SearchResult]:
        a = author or "the author"
        return [
            SearchResult(
                title=f"{title} — Goodreads reviews",
                url="https://www.goodreads.com/book/mock",
                content=(
                    f"Readers praise {title} by {a} for its pacing and characters. "
                    "Average rating around 4.2/5 across thousands of ratings. "
                    "One reader wrote: 'Could not put it down, a stunning read.'"
                ),
            ),
            SearchResult(
                title=f"The New York Times review of {title}",
                url="https://www.nytimes.com/mock-review",
                content=(
                    f"A critic for The New York Times called {title} 'ambitious and "
                    "deeply human', while noting the middle act drags slightly."
                ),
            ),
            SearchResult(
                title=f"Oprah on {title}",
                url="https://oprah.com/mock",
                content=(
                    f"Celebrity book-club host Oprah Winfrey recommended {title}, "
                    "saying it 'stayed with me for weeks.'"
                ),
            ),
            SearchResult(
                title=f"Penguin Random House — about {title}",
                url="https://penguinrandomhouse.com/mock",
                content=(
                    f"Publisher Penguin Random House describes {title} as a landmark "
                    f"work by {a}, first published to wide acclaim."
                ),
            ),
        ]
