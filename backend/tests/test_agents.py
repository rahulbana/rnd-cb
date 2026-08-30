"""Tests for intake, meal-planner fallback, safety, and orchestrator."""

from __future__ import annotations

import pytest

from app.agents.intake import IntakeAgent
from app.agents.meal_planner import MealPlannerAgent
from app.agents.nutrition import NutritionAgent
from app.agents.orchestrator import Orchestrator
from app.agents.safety import SafetyAgent
from app.core.llm import LLMClient
from app.schemas import DietType, Goal, IntakeRequest, Sex


class DisabledLLM(LLMClient):
    """LLM stub that reports itself unavailable (forces deterministic paths)."""

    def __init__(self) -> None:  # noqa: D401 - test stub
        pass

    @property
    def enabled(self) -> bool:
        return False


@pytest.fixture
def base_intake() -> IntakeRequest:
    return IntakeRequest(
        age=30, sex=Sex.male, height_cm=180, weight_kg=80,
        goal=Goal.maintain, diet_type=DietType.balanced, meals_per_day=3,
    )


def test_intake_flags_minor() -> None:
    intake = IntakeRequest(age=15, sex=Sex.female, height_cm=160, weight_kg=55)
    result = IntakeAgent().run(intake)
    assert any("minor" in w.lower() for w in result.warnings)


def test_fallback_plan_respects_allergies(base_intake: IntakeRequest) -> None:
    intake = base_intake.model_copy(
        update={"diet_type": DietType.vegan, "allergies": ["tofu"]}
    )
    nutrition = NutritionAgent().run(intake)
    plan = MealPlannerAgent(DisabledLLM(), days=2).run(intake, nutrition)

    assert plan.source == "fallback"
    assert len(plan.days) == 2
    for day in plan.days:
        for meal in day.meals:
            for item in meal.items:
                assert "tofu" not in item.name.lower()


def test_fallback_meals_per_day(base_intake: IntakeRequest) -> None:
    intake = base_intake.model_copy(update={"meals_per_day": 5})
    nutrition = NutritionAgent().run(intake)
    plan = MealPlannerAgent(DisabledLLM(), days=1).run(intake, nutrition)
    assert len(plan.days[0].meals) == 5


def test_safety_blocks_allergen_leak(base_intake: IntakeRequest) -> None:
    from app.schemas import (
        DayPlan,
        FoodItem,
        Meal,
        MealPlan,
    )

    intake = base_intake.model_copy(update={"allergies": ["peanut"]})
    nutrition = NutritionAgent().run(intake)
    bad_item = FoodItem(
        name="peanut butter toast", quantity="2 slices",
        calories=300, protein_g=10, carbs_g=30, fat_g=15,
    )
    plan = MealPlan(
        days=[
            DayPlan(
                day="Day 1",
                meals=[Meal(name="Breakfast", items=[bad_item], calories=300)],
                total_calories=300, total_protein_g=10,
                total_carbs_g=30, total_fat_g=15,
            )
        ],
        source="llm",
    )
    review = SafetyAgent(DisabledLLM()).run(intake, nutrition, plan)
    assert review.approved is False
    assert any(i.code == "allergen_present" for i in review.issues)


def test_orchestrator_end_to_end_without_llm(base_intake: IntakeRequest) -> None:
    result = Orchestrator(DisabledLLM(), days=3).run(base_intake)
    assert result.meal_plan.source == "fallback"
    assert len(result.meal_plan.days) == 3
    assert result.nutrition.target_kcal > 0
    assert result.safety.disclaimer
