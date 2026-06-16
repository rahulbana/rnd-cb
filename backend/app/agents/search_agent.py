"""Search agent: gathers raw web evidence about a book."""

from __future__ import annotations

from ..models import SearchResult
from ..web_search import WebSearchClient


class SearchAgent:
    """Wraps the web search layer; the entry point of the pipeline."""

    def __init__(self, search_client: WebSearchClient | None = None) -> None:
        self.search_client = search_client or WebSearchClient()

    def run(self, title: str, author: str | None = None) -> list[SearchResult]:
        return self.search_client.search_reviews(title, author)
