"""FastAPI application entrypoint.

Exposes three endpoints consumed by the React frontend:

    GET  /api/health     -> liveness probe.
    GET  /api/languages  -> the languages the dropdown should offer.
    POST /api/generate   -> run the multi-agent pipeline and return the result.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.agents import AgentError
from app.config import get_settings
from app.schemas import (
    GenerateRequest,
    GenerateResponse,
    Language,
    LanguageOption,
)
from app.services import CodeGenerationOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Agent Code Generator",
    version=__version__,
    description=(
        "Generates, reviews, and documents code in the language of your choice "
        "using a planner -> coder -> reviewer agent pipeline."
    ),
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A single orchestrator instance is reused across requests; the underlying
# OpenAI client is thread-safe for our usage.
orchestrator = CodeGenerationOrchestrator()


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok", "version": __version__}


@app.get("/api/languages", response_model=list[LanguageOption], tags=["meta"])
def list_languages() -> list[LanguageOption]:
    """Return the languages the frontend dropdown should display."""
    return [
        LanguageOption(value=lang.value, label=lang.display_name)
        for lang in Language
    ]


@app.post("/api/generate", response_model=GenerateResponse, tags=["generation"])
def generate(request: GenerateRequest) -> GenerateResponse:
    """Run the multi-agent pipeline for a single request.

    Input validation is handled automatically by the :class:`GenerateRequest`
    model; this handler focuses on running the pipeline and translating agent
    failures into clean HTTP errors.
    """
    try:
        return orchestrator.run(request.language, request.problem_statement)
    except AgentError as exc:
        # Expected, user-facing failures (bad config, model errors, etc.).
        logger.warning("Generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except Exception as exc:  # pragma: no cover - last-resort safety net
        logger.exception("Unexpected error during generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the code.",
        ) from exc
