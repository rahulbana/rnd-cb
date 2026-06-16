"""Research agent: enrich the source material with live web findings.

It (1) asks the LLM for a handful of focused search queries, (2) runs them
through Tavily, and (3) distills the raw results into concise, attributable
findings. If no Tavily key is configured the agent is a no-op so the rest of
the pipeline still runs offline.
"""

from __future__ import annotations

from typing import List

from ..config import Settings
from ..llm import LLMClient
from ..models import ResearchFinding

_QUERY_SYSTEM = (
    "You are a research strategist preparing a presentation. Given source "
    "material and a topic, propose precise web-search queries that would "
    "surface recent facts, statistics, examples and context to strengthen "
    "the deck. Prefer specificity over breadth."
)

_DISTILL_SYSTEM = (
    "You distill raw web search snippets into crisp, presentation-ready "
    "facts. Keep only claims that are concrete and useful. Never invent "
    "numbers; if a snippet is vague, drop it."
)


class ResearchAgent:
    def __init__(self, settings: Settings, llm: LLMClient) -> None:
        self._settings = settings
        self._llm = llm

    def _propose_queries(self, topic: str, source: str) -> List[str]:
        from pydantic import BaseModel, Field

        class _Queries(BaseModel):
            queries: List[str] = Field(default_factory=list)

        result = self._llm.complete_model(
            _Queries,
            _QUERY_SYSTEM,
            f"Topic: {topic}\n\nSource excerpt:\n{source[:4000]}\n\n"
            f"Propose up to {self._settings.max_searches} search queries.",
            fast=True,
        )
        return result.queries[: self._settings.max_searches]

    def _search(self, query: str) -> List[dict]:
        from tavily import TavilyClient

        client = TavilyClient(api_key=self._settings.tavily_api_key)
        resp = client.search(query=query, max_results=3, search_depth="basic")
        return resp.get("results", [])

    def _distill(self, topic: str, raw_results: List[dict]) -> List[ResearchFinding]:
        from pydantic import BaseModel, Field

        class _Findings(BaseModel):
            findings: List[ResearchFinding] = Field(default_factory=list)

        snippets = "\n\n".join(
            f"TITLE: {r.get('title','')}\nURL: {r.get('url','')}\n"
            f"CONTENT: {r.get('content','')}"
            for r in raw_results
        )
        if not snippets.strip():
            return []

        result = self._llm.complete_model(
            _Findings,
            _DISTILL_SYSTEM,
            f"Topic: {topic}\n\nRaw search results:\n{snippets}",
            fast=True,
        )
        return result.findings

    def run(self, topic: str, source: str) -> List[ResearchFinding]:
        """Return distilled findings, or an empty list if research is off."""
        if not self._settings.research_enabled:
            return []

        queries = self._propose_queries(topic, source)
        raw: List[dict] = []
        for q in queries:
            try:
                raw.extend(self._search(q))
            except Exception:  # noqa: BLE001 - research is best-effort
                continue

        if not raw:
            return []
        return self._distill(topic, raw)
