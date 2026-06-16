"""Search agent — stage 2.

Executes the planner's queries using the LLM's web-search tool and returns
structured :class:`PaperCandidate` records. It deliberately casts a wide net;
filtering for correctness is the validator's job.
"""

from __future__ import annotations

from ..llm import LLMClient
from ..models import PaperRequest, SearchPlan, SearchResult

_SYSTEM = """You are the web-search agent in a question-paper collection system.

Use web search to find actual downloadable board examination question papers
matching the request. For every promising result, capture:

- a clear title,
- the most direct URL you can (prefer links that end in .pdf or lead straight
  to a paper rather than generic landing pages),
- the hosting source/domain,
- and whatever board / subject / class / year you can infer.

Prefer official board sites and reputable education portals. Gather as many
distinct, relevant candidates as you reasonably can. Do not fabricate URLs — only
report links you actually encountered in search results."""


class SearchAgent:
    """Runs the plan's searches and returns candidate papers."""

    name = "searcher"

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(self, request: PaperRequest, plan: SearchPlan) -> SearchResult:
        queries = "\n".join(f"- {q.query}" for q in plan.queries)
        sources = ", ".join(plan.trusted_sources) or "any reputable source"
        user = (
            f"Find papers for: {request.describe()}\n\n"
            f"Run these searches (and sensible variations):\n{queries}\n\n"
            f"Prefer these sources: {sources}\n\n"
            "Return every relevant candidate paper you can find with direct "
            "links."
        )
        result = self._llm.search(system=_SYSTEM, user=user, schema=SearchResult)

        # Deduplicate by URL while preserving order, then cap the list so later
        # stages stay cheap.
        seen: set[str] = set()
        unique = []
        for cand in result.candidates:
            key = cand.url.strip().rstrip("/")
            if key and key not in seen:
                seen.add(key)
                unique.append(cand)
        return SearchResult(candidates=unique)
