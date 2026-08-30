"""HTTP API routes.

Thin controllers: validate (via Pydantic on the request model), delegate to the
service, map domain results to HTTP responses. No business logic here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.config import get_settings
from app.dependencies import get_plan_service
from app.schemas import (
    DietPlanResponse,
    ErrorResponse,
    IntakeRequest,
    PlanListItem,
)
from app.services.plan_service import PlanService

router = APIRouter(prefix="/api/v1", tags=["diet-plans"])


@router.get("/health", summary="Liveness/readiness probe")
def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_enabled": settings.llm_enabled,
        "model": settings.openai_model if settings.llm_enabled else None,
    }


@router.post(
    "/plans",
    response_model=DietPlanResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
    summary="Generate and store a new diet plan",
)
def create_plan(
    request: IntakeRequest,
    service: PlanService = Depends(get_plan_service),
) -> DietPlanResponse:
    return service.create_plan(request)


@router.get(
    "/plans",
    response_model=list[PlanListItem],
    summary="List recent diet plans",
)
def list_plans(
    limit: int = 50,
    service: PlanService = Depends(get_plan_service),
) -> list[PlanListItem]:
    return service.list_plans(limit=min(max(limit, 1), 200))


@router.get(
    "/plans/{plan_id}",
    response_model=DietPlanResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Fetch a stored diet plan",
)
def get_plan(
    plan_id: int,
    service: PlanService = Depends(get_plan_service),
) -> DietPlanResponse:
    plan = service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


@router.delete(
    "/plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a stored diet plan",
)
def delete_plan(
    plan_id: int,
    service: PlanService = Depends(get_plan_service),
) -> Response:
    if not service.delete_plan(plan_id):
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
