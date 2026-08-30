"""Pydantic schemas: the API contract and the inter-agent data model.

These models are the single source of truth for what a valid request looks like
and what shape each agent produces/consumes. Validation lives here so that bad
input is rejected at the boundary, never deep inside an agent.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- Enumerations ------------------------------------------------------------
class Sex(str, Enum):
    male = "male"
    female = "female"


class ActivityLevel(str, Enum):
    """Maps to a TDEE multiplier in the nutrition calculator."""

    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class Goal(str, Enum):
    lose_weight = "lose_weight"
    maintain = "maintain"
    gain_muscle = "gain_muscle"


class DietType(str, Enum):
    balanced = "balanced"
    vegetarian = "vegetarian"
    vegan = "vegan"
    keto = "keto"
    mediterranean = "mediterranean"
    high_protein = "high_protein"


# --- Request -----------------------------------------------------------------
class IntakeRequest(BaseModel):
    """Raw user intake. Bounds guard against nonsensical or unsafe input."""

    model_config = ConfigDict(extra="forbid")

    age: Annotated[int, Field(ge=13, le=100, description="Age in years")]
    sex: Sex
    height_cm: Annotated[float, Field(ge=120, le=250, description="Height in cm")]
    weight_kg: Annotated[float, Field(ge=30, le=400, description="Weight in kg")]
    activity_level: ActivityLevel = ActivityLevel.moderate
    goal: Goal = Goal.maintain
    diet_type: DietType = DietType.balanced
    meals_per_day: Annotated[int, Field(ge=2, le=6)] = 3
    allergies: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=500)

    @field_validator("allergies", "dislikes", mode="before")
    @classmethod
    def _normalize_list(cls, value: object) -> list[str]:
        """Accept a comma-separated string or a list; return a clean list."""
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",")
        if not isinstance(value, (list, tuple)):
            raise ValueError("must be a list or comma-separated string")
        return [str(v).strip().lower() for v in value if str(v).strip()]


# --- Nutrition ---------------------------------------------------------------
class MacroTargets(BaseModel):
    protein_g: float
    carbs_g: float
    fat_g: float


class NutritionSummary(BaseModel):
    """Deterministically computed energy and macro targets."""

    bmr_kcal: float = Field(description="Basal metabolic rate")
    tdee_kcal: float = Field(description="Total daily energy expenditure")
    target_kcal: float = Field(description="Goal-adjusted daily calorie target")
    bmi: float
    bmi_category: str
    macros: MacroTargets
    rationale: str


# --- Meal plan ---------------------------------------------------------------
class FoodItem(BaseModel):
    name: str
    quantity: str = Field(description="Human-readable serving, e.g. '150 g'")
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class Meal(BaseModel):
    name: str = Field(description="e.g. Breakfast, Lunch, Snack")
    items: list[FoodItem]
    calories: float = Field(ge=0)


class DayPlan(BaseModel):
    day: str
    meals: list[Meal]
    total_calories: float = Field(ge=0)
    total_protein_g: float = Field(ge=0)
    total_carbs_g: float = Field(ge=0)
    total_fat_g: float = Field(ge=0)


class MealPlan(BaseModel):
    days: list[DayPlan]
    hydration_liters: float = Field(default=2.5, ge=0)
    general_tips: list[str] = Field(default_factory=list)
    source: str = Field(
        default="llm",
        description="'llm' or 'fallback' (deterministic template).",
    )


# --- Safety ------------------------------------------------------------------
class SafetySeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class SafetyIssue(BaseModel):
    severity: SafetySeverity
    code: str
    message: str


class SafetyReview(BaseModel):
    approved: bool
    issues: list[SafetyIssue] = Field(default_factory=list)
    disclaimer: str
    summary: str


# --- Aggregate response ------------------------------------------------------
class DietPlanResponse(BaseModel):
    plan_id: int
    intake: IntakeRequest
    nutrition: NutritionSummary
    meal_plan: MealPlan
    safety: SafetyReview
    created_at: str


class PlanListItem(BaseModel):
    plan_id: int
    goal: Goal
    diet_type: DietType
    target_kcal: float
    approved: bool
    created_at: str


class ErrorResponse(BaseModel):
    detail: str
