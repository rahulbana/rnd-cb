"""Fan-out search across all enabled backends, then dedup + score.

The aggregator is the single entry point the graph's search node uses. It runs
every backend concurrently for each query, merges the hits into `Source`
objects, scores their credibility, orders by credibility, and removes
duplicates (so the survivor of each duplicate group is the most credible copy).
"""

from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.credibility import extract_domain, score_source
from app.dedup import deduplicate
from app.models.schemas import SearchHit, Source
from app.search.arxiv import ArxivBackend
from app.search.base import SearchBackend
from app.search.exa import ExaBackend
from app.search.serper import SerperBackend
from app.search.tavily import TavilyBackend

logger = logging.getLogger(__name__)


class SearchAggregator:
    def __init__(self, backends: list[SearchBackend]) -> None:
        if not backends:
            raise ValueError("SearchAggregator requires at least one backend")
        self.backends = backends

    @classmethod
    def from_settings(cls, settings: Settings) -> SearchAggregator:
        backends: list[SearchBackend] = [ArxivBackend()]
        if settings.tavily_api_key:
            backends.append(TavilyBackend(settings.tavily_api_key))
        if settings.serper_api_key:
            backends.append(SerperBackend(settings.serper_api_key))
        if settings.exa_api_key:
            backends.append(ExaBackend(settings.exa_api_key))
        return cls(backends)

    async def search(self, query: str, *, per_backend: int = 6) -> list[Source]:
        """Run one query across all backends, returning deduped, scored sources."""
        tasks = [b.safe_search(query, limit=per_backend) for b in self.backends]
        results = await asyncio.gather(*tasks)
        hits: list[SearchHit] = [h for group in results for h in group if h.url]
        return self._to_scored_sources(hits)

    async def multi_search(
        self, queries: list[str], *, per_backend: int = 6
    ) -> list[Source]:
        """Run several queries concurrently and merge/dedup across all of them."""
        tasks = [self.search(q, per_backend=per_backend) for q in queries]
        groups = await asyncio.gather(*tasks)
        merged = [s for group in groups for s in group]
        # Re-sort + dedup across queries so cross-query duplicates collapse too.
        merged.sort(key=lambda s: s.credibility, reverse=True)
        return deduplicate(merged)

    def _to_scored_sources(self, hits: list[SearchHit]) -> list[Source]:
        sources: list[Source] = []
        for hit in hits:
            src = Source.from_hit(hit)
            src.domain = extract_domain(src.url)
            src.credibility = score_source(
                url=src.url,
                backend=src.backend,
                published=src.published,
                has_full_content=bool(src.content),
            )
            sources.append(src)
        # Highest credibility first so dedup keeps the best copy of each duplicate.
        sources.sort(key=lambda s: s.credibility, reverse=True)
        return deduplicate(sources)
