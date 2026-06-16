"""Multi-agent orchestration.

The orchestrator runs the three agents in sequence:

    1. ``PlannerAgent``  -> turns the problem statement into a plan.
    2. ``CoderAgent``    -> writes code that follows the plan.
    3. ``ReviewerAgent`` -> reviews/repairs the code and reports what it fixed.

Keeping the wiring in one place means the API layer stays thin and the pipeline
can be unit-tested by injecting fake agents.
"""
from __future__ import annotations

import logging

from app.agents import CoderAgent, PlannerAgent, ReviewerAgent
from app.schemas import GenerateResponse, Language

logger = logging.getLogger(__name__)


class CodeGenerationOrchestrator:
    """Coordinates the planner, coder, and reviewer agents."""

    def __init__(
        self,
        planner: PlannerAgent | None = None,
        coder: CoderAgent | None = None,
        reviewer: ReviewerAgent | None = None,
    ) -> None:
        """Build the orchestrator.

        Agents can be injected (useful for tests); otherwise they are created
        lazily on first use so the app can start even before an API key is set.
        """
        self._planner = planner
        self._coder = coder
        self._reviewer = reviewer

    # Lazy construction keeps import-time side effects (and API-key checks) out
    # of module import and application startup.
    @property
    def planner(self) -> PlannerAgent:
        if self._planner is None:
            self._planner = PlannerAgent()
        return self._planner

    @property
    def coder(self) -> CoderAgent:
        if self._coder is None:
            self._coder = CoderAgent()
        return self._coder

    @property
    def reviewer(self) -> ReviewerAgent:
        if self._reviewer is None:
            self._reviewer = ReviewerAgent()
        return self._reviewer

    def run(self, language: Language, problem_statement: str) -> GenerateResponse:
        """Execute the full pipeline.

        Args:
            language: Target programming language.
            problem_statement: The user's problem description.

        Returns:
            A fully populated :class:`GenerateResponse`.

        Raises:
            AgentError: Propagated from any agent that fails irrecoverably.
        """
        logger.info("Planning solution for language=%s", language.value)
        plan = self.planner.plan(language, problem_statement)

        logger.info("Writing code (%d plan steps)", len(plan))
        draft_code, explanation = self.coder.write(language, problem_statement, plan)

        logger.info("Reviewing generated code")
        final_code, review_notes = self.reviewer.review(
            language, problem_statement, draft_code
        )

        return GenerateResponse(
            language=language.display_name,
            plan=plan,
            code=final_code,
            review_notes=review_notes,
            explanation=explanation,
        )
