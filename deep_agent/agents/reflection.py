"""Reflection Agent — critiques coverage and decides whether to loop."""
from __future__ import annotations

from deep_agent.agents.base import BaseAgent
from deep_agent.config import LLMTier, get_settings
from deep_agent.models.schemas import ReflectionResult
from deep_agent.state import ResearchState
from deep_agent.utils.context import build_sources_block

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

class ReflectionAgent(BaseAgent):
    """Self-critique that drives the adaptive research loop."""

    name = "reflection"
    # Routing/critique is lightweight — use the cheaper FAST tier when set.
    llm_tier = LLMTier.FAST

    def run(self, state: ResearchState) -> dict:
        plan = state["plan"]
        scraped = state.get("scraped", [])
        iteration = state.get("iteration", 0) + 1
        max_iterations = state.get("max_iterations", 3)

        # Guard: with no gathered sources there is nothing to reflect on and
        # re-running the same queries won't help. Skip the LLM call and stop
        # the loop so the graph can route to the no-results terminal.
        if not scraped:
            self.logger.warning(
                "No sources gathered after iteration %d; ending research loop.",
                iteration,
            )
            return {
                "reflection": ReflectionResult(
                    is_sufficient=True,
                    reasoning="No source content could be retrieved.",
                ),
                "iteration": iteration,
                "pending_queries": [],
            }

        settings = get_settings()
        # Reflection needs breadth over depth — use a tighter per-source cap.
        sources_block, _ = build_sources_block(
            scraped,
            total_chars=settings.max_context_chars,
            per_source_chars=min(settings.per_source_chars, 600),
        )

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
