"""FastAPI entrypoint for the book review aggregator backend."""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .agents import Orchestrator
from .config import get_settings
from .export import report_to_markdown, report_to_pdf
from .models import AnalyzeRequest, BookReport

settings = get_settings()

app = FastAPI(
    title="Book Review Aggregator",
    description=(
        "Multi-agent service that researches a book on the web and returns an "
        "author summary plus aggregated, verified reviews."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _orchestrator() -> Orchestrator:
    # Constructed per request so settings/keys are always fresh.
    return Orchestrator()


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "llm_enabled": settings.llm_enabled,
        "search_provider": settings.resolved_search_provider(),
    }


@app.post("/analyze", response_model=BookReport)
def analyze(req: AnalyzeRequest) -> BookReport:
    """Run the full multi-agent pipeline for a book and return the report."""
    try:
        return _orchestrator().run(req.title, req.author)
    except Exception as exc:  # surface a clean error to the client
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {exc}") from exc


@app.post("/export/markdown")
def export_markdown(req: AnalyzeRequest) -> Response:
    report = _orchestrator().run(req.title, req.author)
    md = report_to_markdown(report)
    filename = _slug(report.book.title) + ".md"
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers=_attachment_headers(filename),
    )


@app.post("/export/pdf")
def export_pdf(req: AnalyzeRequest) -> Response:
    report = _orchestrator().run(req.title, req.author)
    pdf = report_to_pdf(report)
    filename = _slug(report.book.title) + ".pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers=_attachment_headers(filename),
    )


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug or "book-report"


def _attachment_headers(filename: str) -> dict[str, str]:
    return {
        "Content-Disposition": f"attachment; filename=\"{filename}\"; "
        f"filename*=UTF-8''{quote(filename)}"
    }
