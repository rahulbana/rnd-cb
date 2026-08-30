"""Safety reviewer agent (deterministic guardrails + LLM summary).

Acts as the final gate before a plan is returned. Hard safety checks are
deterministic and authoritative (calorie floors, allergen leakage, calorie/target
drift). The LLM, when available, only writes a human-friendly summary and
disclaimer — it can never override a hard rule, which keeps the safety boundary
outside of model discretion (defense in depth).

If a `critical` issue is found, the plan is marked not-approved; the orchestrator
decides whether to trigger a revision.
"""

from __future__ import annotations

from app.core.llm import LLMClient, LLMError
from app.core.logging import get_logger
from app.schemas import (
    IntakeRequest,
    MealPlan,
    NutritionSummary,
    SafetyIssue,
    SafetyReview,
    SafetySeverity,
    Sex,
)

logger = get_logger(__name__)

_DEFAULT_DISCLAIMER = (
    "This meal plan is generated for general informational purposes only and is "
    "not medical or dietary advice. Consult a qualified healthcare professional "
    "or registered dietitian before making significant changes to your diet, "
    "especially if you have any medical condition, are pregnant, or take "
    "medication."
)

# Absolute safety floors, mirrored from the nutrition agent.
_CALORIE_FLOOR: dict[Sex, float] = {Sex.female: 1200.0, Sex.male: 1500.0}

# Acceptable drift between the plan's daily calories and the computed target.
_MAX_TARGET_DRIFT = 0.15  # 15%


class SafetyAgent:
    name = "safety"

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(
        self,
        intake: IntakeRequest,
        nutrition: NutritionSummary,
        plan: MealPlan,
    ) -> SafetyReview:
        issues = self._check_rules(intake, nutrition, plan)
        approved = not any(i.severity == SafetySeverity.critical for i in issues)

        summary = self._summarize(intake, nutrition, plan, issues, approved)

        logger.info(
            "safety_reviewed",
            extra={
                "extra": {
                    "approved": approved,
                    "issues": len(issues),
                    "critical": sum(
                        1 for i in issues if i.severity == SafetySeverity.critical
                    ),
                }
            },
        )
        return SafetyReview(
            approved=approved,
            issues=issues,
            disclaimer=_DEFAULT_DISCLAIMER,
            summary=summary,
        )

    # --- Deterministic rules -------------------------------------------------
    def _check_rules(
        self,
        intake: IntakeRequest,
        nutrition: NutritionSummary,
        plan: MealPlan,
    ) -> list[SafetyIssue]:
        issues: list[SafetyIssue] = []

        floor = _CALORIE_FLOOR[intake.sex]
        if nutrition.target_kcal < floor:
            issues.append(
                SafetyIssue(
                    severity=SafetySeverity.critical,
                    code="calorie_below_floor",
                    message=(
                        f"Daily target {nutrition.target_kcal:.0f} kcal is below "
                        f"the {floor:.0f} kcal safety floor."
                    ),
                )
            )

        # Allergen / dislike leakage into the generated plan.
        forbidden = set(intake.allergies)
        disliked = set(intake.dislikes)
        for day in plan.days:
            for meal in day.meals:
                for item in meal.items:
                    lowered = item.name.lower()
                    for allergen in forbidden:
                        if allergen and allergen in lowered:
                            issues.append(
                                SafetyIssue(
                                    severity=SafetySeverity.critical,
                                    code="allergen_present",
                                    message=(
                                        f"Item '{item.name}' may contain declared "
                                        f"allergen '{allergen}'."
                                    ),
                                )
                            )
                    for dislike in disliked:
                        if dislike and dislike in lowered:
                            issues.append(
                                SafetyIssue(
                                    severity=SafetySeverity.warning,
                                    code="dislike_present",
                                    message=(
                                        f"Item '{item.name}' includes disliked food "
                                        f"'{dislike}'."
                                    ),
                                )
                            )

        # Calorie drift between plan and target.
        for day in plan.days:
            if nutrition.target_kcal <= 0:
                continue
            drift = abs(day.total_calories - nutrition.target_kcal) / nutrition.target_kcal
            if drift > _MAX_TARGET_DRIFT:
                issues.append(
                    SafetyIssue(
                        severity=SafetySeverity.warning,
                        code="calorie_drift",
                        message=(
                            f"{day.day} totals {day.total_calories:.0f} kcal, "
                            f"{drift * 100:.0f}% off the "
                            f"{nutrition.target_kcal:.0f} kcal target."
                        ),
                    )
                )

        if nutrition.bmi_category in {"underweight", "obese"}:
            issues.append(
                SafetyIssue(
                    severity=SafetySeverity.info,
                    code="bmi_flag",
                    message=(
                        f"BMI category '{nutrition.bmi_category}' — professional "
                        "guidance is advised."
                    ),
                )
            )

        return issues

    # --- LLM summary (advisory only) ----------------------------------------
    def _summarize(
        self,
        intake: IntakeRequest,
        nutrition: NutritionSummary,
        plan: MealPlan,
        issues: list[SafetyIssue],
        approved: bool,
    ) -> str:
        deterministic = (
            f"Plan {'approved' if approved else 'blocked'} with {len(issues)} "
            f"issue(s). Daily target {nutrition.target_kcal:.0f} kcal, "
            f"diet '{intake.diet_type.value}', goal '{intake.goal.value}'."
        )
        if not self._llm.enabled:
            return deterministic

        try:
            data = self._llm.complete_json(
                system_prompt=(
                    "You write a brief, reassuring but honest one-paragraph safety "
                    "summary for a diet plan. Return JSON {\"summary\": \"...\"}. "
                    "Do not invent new medical claims."
                ),
                user_prompt=(
                    f"Approved: {approved}. Issues: "
                    f"{[i.message for i in issues]}. "
                    f"Target: {nutrition.target_kcal:.0f} kcal, "
                    f"BMI {nutrition.bmi} ({nutrition.bmi_category})."
                ),
                temperature=0.3,
                max_tokens=300,
            )
            text = str(data.get("summary", "")).strip()
            return text or deterministic
        except LLMError as exc:
            logger.warning(
                "safety_summary_fallback", extra={"extra": {"error": str(exc)}}
            )
            return deterministic
