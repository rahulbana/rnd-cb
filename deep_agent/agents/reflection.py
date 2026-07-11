"""Reflection Agent — critiques coverage and decides whether to loop."""
from __future__ import annotations

from deep_agent.agents.base import BaseAgent
from deep_agent.models.schemas import ReflectionResult
from deep_agent.state import ResearchState

_SYSTEM = (
    "You are a rigorous research editor. Assess whether the gathered "
    "evidence is sufficient to write a complete, well-supported report on "
    "the objective. Identify concrete knowledge gaps and, if the evidence "
    "is insufficient, propose targeted follow-up search queries to close "
    "them. Be decisive: only request more research when it would materially "
    "improve the report."
)

_USER = (
    "Objective:\n{objective}\n\n"
    "Sources gathered so far ({n_sources} documents):\n{sources}\n\n"
    "Assess sufficiency and, if needed, propose up to 4 follow-up queries."
)

# Cap per-source context so prompts stay within token budgets.
_SNIPPET_CHARS = 600


class ReflectionAgent(BaseAgent):
    """Self-critique that drives the adaptive research loop."""

    name = "reflection"

    def run(self, state: ResearchState) -> dict:
        plan = state["plan"]
        scraped = state.get("scraped", [])
        iteration = state.get("iteration", 0) + 1
        max_iterations = state.get("max_iterations", 3)

        sources_block = "\n\n".join(
            f"[{i + 1}] {doc.title or doc.url} ({doc.url})\n"
            f"{doc.content[:_SNIPPET_CHARS]}"
            for i, doc in enumerate(scraped)
        ) or "(no sources gathered yet)"

        reflection = self._structured(
            ReflectionResult,
            system=_SYSTEM,
            user=_USER.format(
                objective=plan.objective,
                n_sources=len(scraped),
                sources=sources_block,
            ),
        )

        # Enforce the hard iteration ceiling regardless of the model's view.
        force_stop = iteration >= max_iterations
        if force_stop and not reflection.is_sufficient:
            self.logger.info(
                "Iteration ceiling (%d) reached; stopping research loop.",
                max_iterations,
            )
            reflection.is_sufficient = True

        self.logger.info(
            "Reflection (iter %d/%d): sufficient=%s, %d gaps, %d follow-ups",
            iteration,
            max_iterations,
            reflection.is_sufficient,
            len(reflection.gaps),
            len(reflection.follow_up_queries),
        )

        return {
            "reflection": reflection,
            "iteration": iteration,
            "pending_queries": (
                [] if reflection.is_sufficient else reflection.follow_up_queries
            ),
        }
