"""Meal planner agent (LLM-driven, with deterministic fallback).

Given validated intake + computed nutrition targets, produces a structured,
multi-day meal plan. This is the one agent where generative reasoning adds real
value (variety, culinary coherence, respecting preferences), so it uses the LLM
in strict JSON mode and validates the result against the `MealPlan` schema.

Resilience: if no API key is configured or the LLM call/validation fails, we fall
back to a deterministic template plan so the application always returns something
usable. The `source` field records which path produced the plan.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from app.core.llm import LLMClient, LLMError
from app.core.logging import get_logger
from app.schemas import (
    DayPlan,
    FoodItem,
    IntakeRequest,
    Meal,
    MealPlan,
    NutritionSummary,
)

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a registered-dietitian-style meal planning assistant. You produce safe,
practical, culturally-neutral meal plans. You MUST:
- Hit the daily calorie target within +/- 7% and respect the macro targets as
  closely as is realistic.
- Strictly exclude every listed allergen and disliked food.
- Respect the diet type (e.g. vegan means no animal products).
- Use common, affordable, widely-available ingredients.
- Return ONLY valid JSON matching the requested schema. No prose, no markdown.
Every per-item and per-meal calorie/macro number must be internally consistent
(meal calories = sum of item calories; day totals = sum of meal calories).
"""

_JSON_SCHEMA_HINT = """\
Return a JSON object with EXACTLY this shape:
{
  "days": [
    {
      "day": "Day 1",
      "meals": [
        {
          "name": "Breakfast",
          "items": [
            {"name": "...", "quantity": "150 g",
             "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
          ],
          "calories": 0
        }
      ],
      "total_calories": 0,
      "total_protein_g": 0,
      "total_carbs_g": 0,
      "total_fat_g": 0
    }
  ],
  "hydration_liters": 2.5,
  "general_tips": ["..."]
}
"""


class MealPlannerAgent:
    name = "meal_planner"

    def __init__(self, llm: LLMClient, days: int = 3) -> None:
        self._llm = llm
        self._days = days

    def run(self, intake: IntakeRequest, nutrition: NutritionSummary) -> MealPlan:
        if not self._llm.enabled:
            logger.info("meal_planner_fallback", extra={"extra": {"reason": "no_llm"}})
            return self._fallback(intake, nutrition)

        try:
            return self._generate_with_llm(intake, nutrition)
        except (LLMError, ValidationError, KeyError, ValueError) as exc:
            logger.warning(
                "meal_planner_fallback",
                extra={"extra": {"reason": "llm_failure", "error": str(exc)}},
            )
            return self._fallback(intake, nutrition)

    # --- LLM path ------------------------------------------------------------
    def _generate_with_llm(
        self, intake: IntakeRequest, nutrition: NutritionSummary
    ) -> MealPlan:
        user_prompt = self._build_prompt(intake, nutrition)
        data = self._llm.complete_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=3000,
        )
        plan = MealPlan.model_validate({**data, "source": "llm"})
        if not plan.days:
            raise ValueError("LLM returned an empty plan")
        logger.info(
            "meal_planner_llm_ok", extra={"extra": {"days": len(plan.days)}}
        )
        return plan

    def _build_prompt(
        self, intake: IntakeRequest, nutrition: NutritionSummary
    ) -> str:
        constraints = {
            "days": self._days,
            "meals_per_day": intake.meals_per_day,
            "diet_type": intake.diet_type.value,
            "goal": intake.goal.value,
            "daily_calorie_target": nutrition.target_kcal,
            "macro_targets_g": nutrition.macros.model_dump(),
            "allergies_exclude": intake.allergies,
            "dislikes_exclude": intake.dislikes,
            "user_notes": intake.notes,
        }
        return (
            "Create a meal plan with these constraints:\n"
            f"{json.dumps(constraints, indent=2)}\n\n"
            f"{_JSON_SCHEMA_HINT}"
        )

    # --- Deterministic fallback ---------------------------------------------
    def _fallback(
        self, intake: IntakeRequest, nutrition: NutritionSummary
    ) -> MealPlan:
        """Build a simple, allergen-aware template plan without the LLM.

        Distributes the calorie target across meals and picks placeholder items
        that respect the diet type and exclusions. Numbers are approximate but
        internally consistent.
        """
        target = nutrition.target_kcal
        meal_names = self._meal_names(intake.meals_per_day)
        # Weight distribution across meals (main meals larger than snacks).
        weights = self._meal_weights(intake.meals_per_day)

        pantry = self._pantry(intake)
        days: list[DayPlan] = []
        for d in range(1, self._days + 1):
            meals: list[Meal] = []
            for idx, (mname, w) in enumerate(zip(meal_names, weights)):
                meal_kcal = round(target * w, 1)
                item = self._make_item(pantry[idx % len(pantry)], meal_kcal, nutrition)
                meals.append(
                    Meal(name=mname, items=[item], calories=item.calories)
                )
            days.append(self._summarize_day(f"Day {d}", meals))

        return MealPlan(
            days=days,
            hydration_liters=2.5,
            general_tips=[
                "This is a deterministic template plan (LLM unavailable). "
                "Vary ingredients within your diet type to meet the macro targets.",
                "Prioritize whole foods and lean protein sources.",
            ],
            source="fallback",
        )

    @staticmethod
    def _meal_names(n: int) -> list[str]:
        base = ["Breakfast", "Lunch", "Dinner"]
        snacks = ["Morning Snack", "Afternoon Snack", "Evening Snack"]
        if n <= 3:
            return base[:n]
        names = base + snacks
        # Interleave snacks between main meals for realism, then trim.
        return (["Breakfast", "Morning Snack", "Lunch", "Afternoon Snack",
                 "Dinner", "Evening Snack"])[:n]

    @staticmethod
    def _meal_weights(n: int) -> list[float]:
        # Roughly balanced with slightly smaller snacks.
        raw = {
            2: [0.5, 0.5],
            3: [0.3, 0.4, 0.3],
            4: [0.28, 0.12, 0.35, 0.25],
            5: [0.25, 0.1, 0.32, 0.1, 0.23],
            6: [0.22, 0.1, 0.28, 0.1, 0.22, 0.08],
        }[n]
        total = sum(raw)
        return [w / total for w in raw]

    @staticmethod
    def _pantry(intake: IntakeRequest) -> list[str]:
        from app.schemas import DietType

        base = {
            DietType.vegan: ["tofu & quinoa bowl", "lentil stew", "chickpea salad"],
            DietType.vegetarian: ["greek yogurt & oats", "paneer & rice", "bean chili"],
            DietType.keto: ["eggs & avocado", "salmon & greens", "chicken & cheese"],
            DietType.high_protein: ["egg-white omelette", "grilled chicken & rice",
                                    "cottage cheese bowl"],
            DietType.mediterranean: ["olive-oil veggie bowl", "grilled fish & farro",
                                     "hummus plate"],
            DietType.balanced: ["oats & fruit", "chicken & rice", "mixed veg & tofu"],
        }.get(intake.diet_type, ["oats & fruit", "chicken & rice", "mixed veg & tofu"])

        excluded = set(intake.allergies) | set(intake.dislikes)
        filtered = [p for p in base if not any(x in p for x in excluded)]
        return filtered or ["balanced whole-food plate"]

    @staticmethod
    def _make_item(
        name: str, kcal: float, nutrition: NutritionSummary
    ) -> FoodItem:
        # Split this meal's calories using the day's macro ratio.
        total_macro_kcal = (
            nutrition.macros.protein_g * 4
            + nutrition.macros.carbs_g * 4
            + nutrition.macros.fat_g * 9
        ) or 1.0
        p_ratio = (nutrition.macros.protein_g * 4) / total_macro_kcal
        c_ratio = (nutrition.macros.carbs_g * 4) / total_macro_kcal
        f_ratio = (nutrition.macros.fat_g * 9) / total_macro_kcal
        return FoodItem(
            name=name,
            quantity="1 serving",
            calories=round(kcal, 1),
            protein_g=round(kcal * p_ratio / 4, 1),
            carbs_g=round(kcal * c_ratio / 4, 1),
            fat_g=round(kcal * f_ratio / 9, 1),
        )

    @staticmethod
    def _summarize_day(day: str, meals: list[Meal]) -> DayPlan:
        items = [i for m in meals for i in m.items]
        return DayPlan(
            day=day,
            meals=meals,
            total_calories=round(sum(m.calories for m in meals), 1),
            total_protein_g=round(sum(i.protein_g for i in items), 1),
            total_carbs_g=round(sum(i.carbs_g for i in items), 1),
            total_fat_g=round(sum(i.fat_g for i in items), 1),
        )
