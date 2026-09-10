"""API routes for the resume generator."""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response

from ..config import get_settings
from ..schemas import (
    GenerateRequest,
    GenerateResponse,
    RenderRequest,
    ResumeStyle,
)
from ..services import llm, pdf

router = APIRouter(prefix="/api", tags=["resume"])


def _safe_filename(name: str) -> str:
    """Turn a person's name into a safe file stem like 'jane_doe'."""

    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    return slug or "resume"


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "llm_enabled": settings.llm_enabled,
        "model": settings.openai_model if settings.llm_enabled else None,
    }


@router.get("/styles")
def list_styles() -> dict:
    """Expose available resume styles for the frontend picker."""

    return {"styles": [s.value for s in ResumeStyle]}


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    """Turn raw user input into a polished, structured resume via the LLM."""

    resume = llm.generate_resume(req.input, tone=req.tone)
    return GenerateResponse(resume=resume, style=req.style)


@router.post("/preview-html")
def preview_html(req: RenderRequest) -> dict:
    """Return rendered HTML for the live preview (matches the PDF layout)."""

    return {"html": pdf.render_html(req.resume, req.style)}


@router.post("/render-pdf")
def render_pdf(req: RenderRequest) -> Response:
    """Render a (possibly user-edited) resume to a downloadable PDF."""

    try:
        pdf_bytes = pdf.render_pdf(req.resume, req.style)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    stem = _safe_filename(req.resume.personal.full_name)
    filename = f"{stem}_resume.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{filename}\"; "
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )
