"""Nutrition calculator agent (deterministic tool).

Computes BMR, TDEE, a goal-adjusted calorie target, BMI, and macro split using
well-established formulas. This is pure arithmetic on validated input — the LLM
is never involved, because numeric targets must be correct and reproducible.

References:
- BMR: Mifflin-St Jeor equation (1990).
- TDEE: BMR * activity multiplier.
- Macro splits: common evidence-informed ranges per diet type; protein is
  anchored to body weight for muscle-preservation.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.schemas import (
    ActivityLevel,
    DietType,
    Goal,
    IntakeRequest,
    MacroTargets,
    NutritionSummary,
    Sex,
)

logger = get_logger(__name__)

# TDEE activity multipliers (standard Mifflin-St Jeor companions).
_ACTIVITY_MULTIPLIERS: dict[ActivityLevel, float] = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.light: 1.375,
    ActivityLevel.moderate: 1.55,
    ActivityLevel.active: 1.725,
    ActivityLevel.very_active: 1.9,
}

# Goal-based calorie adjustment (kcal/day). Kept conservative for safety.
_GOAL_ADJUSTMENT: dict[Goal, float] = {
    Goal.lose_weight: -500.0,   # ~0.45 kg/week deficit
    Goal.maintain: 0.0,
    Goal.gain_muscle: +300.0,   # lean surplus
}

# Absolute calorie floors by sex — never prescribe below these without medical care.
_CALORIE_FLOOR: dict[Sex, float] = {Sex.female: 1200.0, Sex.male: 1500.0}

# Macro distribution as (protein_g_per_kg, carb_fraction_of_remaining).
# Fat takes the remainder of calories after protein and carbs.
_DIET_MACROS: dict[DietType, tuple[float, float]] = {
    DietType.balanced: (1.6, 0.50),
    DietType.vegetarian: (1.5, 0.52),
    DietType.vegan: (1.5, 0.55),
    DietType.keto: (1.8, 0.08),
    DietType.mediterranean: (1.5, 0.48),
    DietType.high_protein: (2.0, 0.40),
}

# Calories per gram of each macronutrient (Atwater factors).
_KCAL_PER_G = {"protein": 4.0, "carbs": 4.0, "fat": 9.0}


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal"
    if bmi < 30:
        return "overweight"
    return "obese"


class NutritionAgent:
    name = "nutrition"

    def run(self, intake: IntakeRequest) -> NutritionSummary:
        # BMR — Mifflin-St Jeor.
        s = 5.0 if intake.sex == Sex.male else -161.0
        bmr = (
            10.0 * intake.weight_kg
            + 6.25 * intake.height_cm
            - 5.0 * intake.age
            + s
        )

        tdee = bmr * _ACTIVITY_MULTIPLIERS[intake.activity_level]

        raw_target = tdee + _GOAL_ADJUSTMENT[intake.goal]
        floor = _CALORIE_FLOOR[intake.sex]
        target = max(raw_target, floor)
        floored = target > raw_target

        bmi = intake.weight_kg / ((intake.height_cm / 100) ** 2)

        macros = self._macros(intake, target)

        rationale_parts = [
            f"BMR {bmr:.0f} kcal (Mifflin-St Jeor), "
            f"TDEE {tdee:.0f} kcal at '{intake.activity_level.value}' activity.",
            f"Goal '{intake.goal.value}' applies a "
            f"{_GOAL_ADJUSTMENT[intake.goal]:+.0f} kcal/day adjustment.",
        ]
        if floored:
            rationale_parts.append(
                f"Target raised to the {floor:.0f} kcal safety floor for "
                f"{intake.sex.value}s."
            )

        summary = NutritionSummary(
            bmr_kcal=round(bmr, 1),
            tdee_kcal=round(tdee, 1),
            target_kcal=round(target, 1),
            bmi=round(bmi, 1),
            bmi_category=_bmi_category(bmi),
            macros=macros,
            rationale=" ".join(rationale_parts),
        )
        logger.info(
            "nutrition_computed",
            extra={
                "extra": {
                    "target_kcal": summary.target_kcal,
                    "bmi": summary.bmi,
                    "floored": floored,
                }
            },
        )
        return summary

    @staticmethod
    def _macros(intake: IntakeRequest, target_kcal: float) -> MacroTargets:
        protein_per_kg, carb_fraction = _DIET_MACROS[intake.diet_type]

        protein_g = protein_per_kg * intake.weight_kg
        protein_kcal = protein_g * _KCAL_PER_G["protein"]

        remaining_kcal = max(target_kcal - protein_kcal, 0.0)
        carb_kcal = remaining_kcal * carb_fraction
        fat_kcal = remaining_kcal - carb_kcal

        return MacroTargets(
            protein_g=round(protein_g, 1),
            carbs_g=round(carb_kcal / _KCAL_PER_G["carbs"], 1),
            fat_g=round(fat_kcal / _KCAL_PER_G["fat"], 1),
        )
