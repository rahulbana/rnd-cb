"""FastAPI application exposing the multi-agent study planner."""
from __future__ import annotations

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.schemas import StudyPlan, StudyPlanRequest
from app.services.export import render_markdown
from app.services.pdf import build_pdf
from app.services.plan_service import generate_plan, stream_plan


def _filename(plan: StudyPlan, ext: str) -> str:
    raw = f"study-plan-{plan.request.subject}-{plan.request.topic}".lower()
    slug = "".join(c if c.isalnum() else "-" for c in raw).strip("-")
    return f"{slug or 'study-plan'}.{ext}"

settings = get_settings()

app = FastAPI(
    title="Multi-Agent Study Planner",
    description="Agentic study-plan generator for students (class 5-12).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    """Health check; reports whether an API key is configured."""
    return {"status": "ok", "model": settings.openai_model, "configured": settings.has_api_key}


@app.post("/api/study-plan", response_model=StudyPlan)
async def create_study_plan(req: StudyPlanRequest) -> StudyPlan:
    """Generate a complete study plan in a single request (no streaming)."""
    return await generate_plan(req)


@app.post("/api/study-plan/stream")
async def create_study_plan_stream(req: StudyPlanRequest) -> EventSourceResponse:
    """Stream live agent progress while the plan is built (SSE)."""
    return EventSourceResponse(stream_plan(req))


@app.post("/api/study-plan/markdown", response_class=PlainTextResponse)
async def study_plan_markdown(plan: StudyPlan) -> str:
    """Re-render a plan to Markdown (used for server-side download if desired)."""
    return render_markdown(plan)


@app.post("/api/study-plan/pdf")
async def study_plan_pdf(plan: StudyPlan) -> Response:
    """Render a plan to a downloadable PDF document."""
    pdf_bytes = build_pdf(plan)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename(plan, "pdf")}"'
        },
    )
