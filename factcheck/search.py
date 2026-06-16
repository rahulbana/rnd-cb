"""Web search and source gathering via the Tavily API.

This module is the *only* place the agent reaches out to the open web. The text
it returns is the sole material the verdict model is allowed to reason over.
"""

from __future__ import annotations

from typing import List

from tavily import TavilyClient

from .models import Source


class WebSearcher:
    def __init__(self, api_key: str) -> None:
        self._client = TavilyClient(api_key=api_key)

    def gather(
        self,
        queries: List[str],
        *,
        results_per_query: int = 5,
        depth: str = "advanced",
        max_sources: int = 12,
    ) -> List[Source]:
        """Run every query, then dedupe and rank the union of results by URL.

        Args:
            queries: Search strings to investigate the claim from multiple angles.
            results_per_query: How many results to request per query.
            depth: Tavily search depth — "advanced" performs a deeper crawl.
            max_sources: Hard cap on sources handed to the verdict model.
        """
        by_url: dict[str, Source] = {}

        for query in queries:
            try:
                response = self._client.search(
                    query=query,
                    search_depth=depth,
                    max_results=results_per_query,
                    include_answer=False,
                    include_raw_content=True,
                )
            except Exception as exc:  # noqa: BLE001 - surface as a skipped query
                # One bad query shouldn't sink the whole run.
                print(f"  ! search failed for query {query!r}: {exc}")
                continue

            for item in response.get("results", []):
                url = item.get("url")
                if not url:
                    continue

                content = (item.get("raw_content") or item.get("content") or "").strip()
                if not content:
                    continue

                score = float(item.get("score", 0.0) or 0.0)
                existing = by_url.get(url)
                if existing is None or score > existing.score:
                    by_url[url] = Source(
                        index=0,  # assigned after ranking
                        title=item.get("title") or url,
                        url=url,
                        content=content,
                        query=query,
                        score=score,
                    )

        ranked = sorted(by_url.values(), key=lambda s: s.score, reverse=True)[:max_sources]
        for i, source in enumerate(ranked, start=1):
            source.index = i
        return ranked
