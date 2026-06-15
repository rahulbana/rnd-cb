"""Study-plan endpoints: generate, stream, and export."""
from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse

from app.schemas import StudyPlan, StudyPlanRequest
from app.services.exporters import build_pdf, plan_filename, render_markdown
from app.services.planner_service import generate_plan, stream_plan

router = APIRouter(prefix="/study-plan", tags=["study-plans"])


@router.post("", response_model=StudyPlan)
async def create_study_plan(req: StudyPlanRequest) -> StudyPlan:
    """Generate a complete study plan in a single request (no streaming)."""
    return await generate_plan(req)


@router.post("/stream")
async def create_study_plan_stream(req: StudyPlanRequest) -> EventSourceResponse:
    """Stream live agent progress while the plan is built (SSE)."""
    return EventSourceResponse(stream_plan(req))


@router.post("/markdown", response_class=PlainTextResponse)
async def study_plan_markdown(plan: StudyPlan) -> str:
    """Re-render a plan to Markdown."""
    return render_markdown(plan)


@router.post("/pdf")
async def study_plan_pdf(plan: StudyPlan) -> Response:
    """Render a plan to a downloadable PDF document."""
    return Response(
        content=build_pdf(plan),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{plan_filename(plan, "pdf")}"'
        },
    )
