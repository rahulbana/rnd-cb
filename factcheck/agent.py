"""Orchestrates the fact-checking pipeline: queries -> web search -> verdict."""

from __future__ import annotations

from typing import Callable, Optional

from openai import OpenAI

from .config import Settings
from .llm import Reasoner
from .models import FactCheckReport
from .search import WebSearcher

# A simple progress callback so the CLI can show what's happening.
ProgressFn = Callable[[str], None]


class FactCheckAgent:
    def __init__(self, settings: Settings, progress: Optional[ProgressFn] = None) -> None:
        self._settings = settings
        self._progress = progress or (lambda _msg: None)
        self._reasoner = Reasoner(OpenAI(api_key=settings.openai_api_key), settings.model)
        self._searcher = WebSearcher(settings.tavily_api_key)

    def check(
        self,
        claim: str,
        *,
        max_queries: int = 4,
        results_per_query: int = 5,
        max_sources: int = 12,
        depth: str = "advanced",
    ) -> FactCheckReport:
        claim = claim.strip()

        self._progress("Drafting search queries...")
        queries = self._reasoner.generate_queries(claim, max_queries=max_queries)
        for q in queries:
            self._progress(f"  query: {q}")

        self._progress("Searching the web and gathering sources...")
        sources = self._searcher.gather(
            queries,
            results_per_query=results_per_query,
            depth=depth,
            max_sources=max_sources,
        )
        self._progress(f"Gathered {len(sources)} unique source(s).")

        self._progress("Evaluating the claim against gathered sources only...")
        result = self._reasoner.verdict(claim, sources)

        return FactCheckReport(claim=claim, result=result, sources=sources, queries=queries)
