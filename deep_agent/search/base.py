"""Abstract search-provider interface.

Every concrete provider (Tavily, Serper, ...) implements :meth:`search`
and returns a normalised ``list[SearchResult]`` so that the rest of the
system is provider-agnostic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from deep_agent.models.schemas import SearchResult


class SearchClient(ABC):
    """Common contract for all search back-ends."""

    #: Human-readable provider name, surfaced on each result.
    name: str = "base"

    def __init__(self, max_results: int = 6) -> None:
        self.max_results = max_results

    @abstractmethod
    def search(self, query: str, max_results: int | None = None) -> list[SearchResult]:
        """Run a single query and return normalised results."""

    def batch_search(self, queries: list[str]) -> list[SearchResult]:
        """Run several queries sequentially and flatten the results."""

        results: list[SearchResult] = []
        for query in queries:
            results.extend(self.search(query))
        return results
