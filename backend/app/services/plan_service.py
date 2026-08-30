"""Application service: runs the pipeline and persists results.

Sits between the HTTP layer and the domain (agents + repository). Keeping this
here means the API routes stay thin and the business flow is unit-testable
without a web server.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator, PipelineResult
from app.core.logging import get_logger
from app.models import DietPlan
from app.schemas import (
    DietPlanResponse,
    IntakeRequest,
    MealPlan,
    NutritionSummary,
    PlanListItem,
    SafetyReview,
)

logger = get_logger(__name__)


class PlanService:
    def __init__(self, db: Session, orchestrator: Orchestrator) -> None:
        self._db = db
        self._orchestrator = orchestrator

    def create_plan(self, request: IntakeRequest) -> DietPlanResponse:
        result: PipelineResult = self._orchestrator.run(request)
        record = self._persist(result)
        return self._to_response(record)

    def get_plan(self, plan_id: int) -> DietPlanResponse | None:
        record = self._db.get(DietPlan, plan_id)
        return self._to_response(record) if record else None

    def list_plans(self, limit: int = 50) -> list[PlanListItem]:
        stmt = select(DietPlan).order_by(DietPlan.created_at.desc()).limit(limit)
        rows = self._db.execute(stmt).scalars().all()
        return [
            PlanListItem(
                plan_id=r.id,
                goal=r.goal,
                diet_type=r.diet_type,
                target_kcal=r.target_kcal,
                approved=r.approved,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ]

    def delete_plan(self, plan_id: int) -> bool:
        record = self._db.get(DietPlan, plan_id)
        if record is None:
            return False
        self._db.delete(record)
        self._db.commit()
        return True

    # --- internals -----------------------------------------------------------
    def _persist(self, result: PipelineResult) -> DietPlan:
        record = DietPlan(
            goal=result.intake.goal.value,
            diet_type=result.intake.diet_type.value,
            target_kcal=result.nutrition.target_kcal,
            approved=result.safety.approved,
            intake=result.intake.model_dump(mode="json"),
            nutrition=result.nutrition.model_dump(mode="json"),
            meal_plan=result.meal_plan.model_dump(mode="json"),
            safety=result.safety.model_dump(mode="json"),
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        logger.info("plan_persisted", extra={"extra": {"plan_id": record.id}})
        return record

    @staticmethod
    def _to_response(record: DietPlan) -> DietPlanResponse:
        return DietPlanResponse(
            plan_id=record.id,
            intake=IntakeRequest.model_validate(record.intake),
            nutrition=NutritionSummary.model_validate(record.nutrition),
            meal_plan=MealPlan.model_validate(record.meal_plan),
            safety=SafetyReview.model_validate(record.safety),
            created_at=record.created_at.isoformat(),
        )
