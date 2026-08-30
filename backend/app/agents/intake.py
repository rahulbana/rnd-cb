"""Intake & validation agent.

Responsibility: turn raw user input into a trusted, normalized intake object and
surface any soft warnings (e.g. very high BMI, aggressive goals). Hard bounds are
already enforced by the `IntakeRequest` Pydantic schema at the API boundary; this
agent adds domain-level normalization and advisory checks.

Design note: this agent is intentionally deterministic. Input validation must be
predictable and cheap — we do NOT ask an LLM whether a weight is valid. Free-text
notes are passed through to downstream agents as constraints, not executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.schemas import Goal, IntakeRequest

logger = get_logger(__name__)


@dataclass
class IntakeResult:
    intake: IntakeRequest
    warnings: list[str] = field(default_factory=list)


class IntakeAgent:
    name = "intake"

    def run(self, payload: IntakeRequest) -> IntakeResult:
        warnings: list[str] = []

        bmi = payload.weight_kg / ((payload.height_cm / 100) ** 2)
        if bmi < 16:
            warnings.append(
                "BMI indicates significant underweight; a healthcare "
                "professional should be consulted before weight loss."
            )
        elif bmi >= 35:
            warnings.append(
                "BMI is in the high range; medical supervision is recommended "
                "for any structured diet."
            )

        if payload.goal == Goal.lose_weight and bmi < 18.5:
            warnings.append(
                "Weight-loss goal selected while already underweight; consider "
                "'maintain' or 'gain_muscle' instead."
            )

        if payload.age < 18:
            warnings.append(
                "User is a minor; plans are informational only and require "
                "pediatric/guardian oversight."
            )

        logger.info(
            "intake_validated",
            extra={"extra": {"bmi": round(bmi, 1), "warnings": len(warnings)}},
        )
        return IntakeResult(intake=payload, warnings=warnings)
