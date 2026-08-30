"""Deterministic orchestrator for the diet-planning pipeline.

Coordinates the agents in a fixed, auditable sequence. The control flow is
deterministic (a plain function, not an autonomous agent) because the steps and
their order are known — this is the simplest mechanism that solves the problem
and is far easier to test, observe, and reason about than a self-directing agent.

Flow:
    intake -> nutrition -> meal_planner -> safety
                              ^                |
                              |    (1 revision if critical & LLM available)
                              +----------------+
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.intake import IntakeAgent, IntakeResult
from app.agents.meal_planner import MealPlannerAgent
from app.agents.nutrition import NutritionAgent
from app.agents.safety import SafetyAgent
from app.core.llm import LLMClient
from app.core.logging import get_logger
from app.schemas import (
    IntakeRequest,
    MealPlan,
    NutritionSummary,
    SafetyReview,
    SafetySeverity,
)

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    intake: IntakeRequest
    nutrition: NutritionSummary
    meal_plan: MealPlan
    safety: SafetyReview
    warnings: list[str]


class Orchestrator:
    """Wires the agents together. Injected dependencies keep it testable."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        days: int = 3,
        max_revisions: int = 1,
    ) -> None:
        self._intake = IntakeAgent()
        self._nutrition = NutritionAgent()
        self._planner = MealPlannerAgent(llm, days=days)
        self._safety = SafetyAgent(llm)
        self._llm = llm
        self._max_revisions = max_revisions

    def run(self, request: IntakeRequest) -> PipelineResult:
        logger.info("pipeline_start", extra={"extra": {"goal": request.goal.value}})

        intake_result: IntakeResult = self._intake.run(request)
        nutrition = self._nutrition.run(intake_result.intake)

        meal_plan = self._planner.run(intake_result.intake, nutrition)
        safety = self._safety.run(intake_result.intake, nutrition, meal_plan)

        # One bounded revision attempt if a critical issue is found and the LLM
        # can actually produce a different plan (the deterministic fallback is
        # already constraint-aware, so re-running it would not change anything).
        revisions = 0
        while (
            not safety.approved
            and revisions < self._max_revisions
            and self._llm.enabled
            and meal_plan.source == "llm"
        ):
            revisions += 1
            logger.info(
                "pipeline_revision", extra={"extra": {"attempt": revisions}}
            )
            meal_plan = self._planner.run(intake_result.intake, nutrition)
            safety = self._safety.run(intake_result.intake, nutrition, meal_plan)

        logger.info(
            "pipeline_complete",
            extra={
                "extra": {
                    "approved": safety.approved,
                    "revisions": revisions,
                    "plan_source": meal_plan.source,
                }
            },
        )
        return PipelineResult(
            intake=intake_result.intake,
            nutrition=nutrition,
            meal_plan=meal_plan,
            safety=safety,
            warnings=intake_result.warnings,
        )
