"""Unit tests for the deterministic nutrition calculator.

These are the highest-value tests: numeric correctness must never regress.
"""

from __future__ import annotations

import pytest

from app.agents.nutrition import NutritionAgent
from app.schemas import ActivityLevel, DietType, Goal, IntakeRequest, Sex


@pytest.fixture
def agent() -> NutritionAgent:
    return NutritionAgent()


def test_bmr_matches_mifflin_st_jeor_male(agent: NutritionAgent) -> None:
    # Known reference: 30yo male, 180cm, 80kg -> BMR = 1780 kcal.
    intake = IntakeRequest(
        age=30, sex=Sex.male, height_cm=180, weight_kg=80,
        activity_level=ActivityLevel.sedentary, goal=Goal.maintain,
    )
    result = agent.run(intake)
    assert result.bmr_kcal == pytest.approx(1780.0, abs=0.5)


def test_bmr_matches_mifflin_st_jeor_female(agent: NutritionAgent) -> None:
    # 30yo female, 165cm, 60kg -> BMR = 1320.25 kcal.
    intake = IntakeRequest(
        age=30, sex=Sex.female, height_cm=165, weight_kg=60,
        activity_level=ActivityLevel.sedentary, goal=Goal.maintain,
    )
    result = agent.run(intake)
    assert result.bmr_kcal == pytest.approx(1320.25, abs=0.5)


def test_tdee_applies_activity_multiplier(agent: NutritionAgent) -> None:
    intake = IntakeRequest(
        age=30, sex=Sex.male, height_cm=180, weight_kg=80,
        activity_level=ActivityLevel.moderate, goal=Goal.maintain,
    )
    result = agent.run(intake)
    assert result.tdee_kcal == pytest.approx(1780.0 * 1.55, abs=1.0)


def test_weight_loss_applies_deficit(agent: NutritionAgent) -> None:
    intake = IntakeRequest(
        age=30, sex=Sex.male, height_cm=180, weight_kg=80,
        activity_level=ActivityLevel.moderate, goal=Goal.lose_weight,
    )
    result = agent.run(intake)
    assert result.target_kcal == pytest.approx(result.tdee_kcal - 500, abs=1.0)


def test_calorie_floor_enforced(agent: NutritionAgent) -> None:
    # Small sedentary female with weight-loss goal should hit the 1200 floor.
    intake = IntakeRequest(
        age=60, sex=Sex.female, height_cm=150, weight_kg=45,
        activity_level=ActivityLevel.sedentary, goal=Goal.lose_weight,
    )
    result = agent.run(intake)
    assert result.target_kcal >= 1200.0
    assert "floor" in result.rationale.lower()


def test_macros_are_calorie_consistent(agent: NutritionAgent) -> None:
    intake = IntakeRequest(
        age=25, sex=Sex.male, height_cm=175, weight_kg=75,
        activity_level=ActivityLevel.active, goal=Goal.gain_muscle,
        diet_type=DietType.high_protein,
    )
    result = agent.run(intake)
    macro_kcal = (
        result.macros.protein_g * 4
        + result.macros.carbs_g * 4
        + result.macros.fat_g * 9
    )
    # Macro-derived calories should closely reconstruct the target.
    assert macro_kcal == pytest.approx(result.target_kcal, rel=0.02)


def test_bmi_category(agent: NutritionAgent) -> None:
    intake = IntakeRequest(
        age=40, sex=Sex.female, height_cm=160, weight_kg=90,
        goal=Goal.lose_weight,
    )
    result = agent.run(intake)
    assert result.bmi_category == "obese"
