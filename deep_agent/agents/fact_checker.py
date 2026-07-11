"""Fact Checker Agent — verifies key claims against gathered sources."""
from __future__ import annotations

from pydantic import BaseModel, Field

from deep_agent.agents.base import BaseAgent
from deep_agent.config import get_settings
from deep_agent.models.schemas import FactCheckResult
from deep_agent.state import ResearchState
from deep_agent.utils.context import build_sources_block


class _FactCheckBatch(BaseModel):
    """Wrapper so the LLM can return a list under structured output."""

    results: list[FactCheckResult] = Field(default_factory=list)


_SYSTEM = (
    "You are a meticulous fact-checker. Extract the most important factual "
    "claims that a report on the objective would rely on, then verify each "
    "claim strictly against the provided sources. For every claim give a "
    "verdict (supported / partially_supported / unsupported / unverifiable), "
    "a confidence score in [0,1], the URLs that support it, and a brief "
    "explanation. Never use outside knowledge — judge only against the "
    "sources given. Check between 5 and 10 claims."
)

_USER = (
    "Objective:\n{objective}\n\n"
    "Sources:\n{sources}\n\n"
    "Identify and verify the key claims."
)


class FactCheckerAgent(BaseAgent):
    """Grounds the report by verifying claims against evidence."""

    name = "fact_checker"

    def run(self, state: ResearchState) -> dict:
        plan = state["plan"]
        scraped = state.get("scraped", [])

        if not scraped:
            self.logger.warning("No sources available for fact checking.")
            return {"fact_checks": []}

        settings = get_settings()
        sources_block, _ = build_sources_block(
            scraped,
            total_chars=settings.max_context_chars,
            per_source_chars=settings.per_source_chars,
        )

        batch = self._structured(
            _FactCheckBatch,
            system=_SYSTEM,
            user=_USER.format(objective=plan.objective, sources=sources_block),
        )

        verdict_counts: dict[str, int] = {}
        for fc in batch.results:
            verdict_counts[fc.verdict.value] = (
                verdict_counts.get(fc.verdict.value, 0) + 1
            )
        self.logger.info(
            "Fact-checked %d claims: %s", len(batch.results), verdict_counts
        )

        return {"fact_checks": batch.results}
