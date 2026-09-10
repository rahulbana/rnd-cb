"""AI Code Explainer — FastAPI backend.

Exposes a small JSON API used by the React frontend:

  GET  /api/health    -> service + LLM status
  GET  /api/actions   -> list of supported analysis actions
  POST /api/detect    -> detect the language of a snippet
  POST /api/analyze   -> run an analysis action against a snippet
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from detect import detect_language
from llm import LLMNotConfigured, complete
from prompts import (
    ACTION_LABELS,
    ACTION_PROMPTS,
    build_system_prompt,
    build_user_prompt,
)

# Load backend/.env if present so OPENAI_API_KEY etc. are available.
load_dotenv()

app = FastAPI(title="AI Code Explainer", version="1.0.0")

# Allow the Vite dev server (and any origin during local dev) to call the API.
_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_CODE_CHARS = 20_000


class DetectRequest(BaseModel):
    code: str = Field(..., description="Source code snippet.")


class DetectResponse(BaseModel):
    language: str


class AnalyzeRequest(BaseModel):
    code: str = Field(..., description="Source code snippet to analyse.")
    action: str = Field(..., description="One of the supported action keys.")
    language: str | None = Field(
        default=None, description="Optional language hint; auto-detected if omitted."
    )
    audience: str | None = Field(
        default="beginner",
        description="Target audience: beginner | intermediate | expert.",
    )


class AnalyzeResponse(BaseModel):
    action: str
    language: str
    result: str


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_configured": bool(os.getenv("OPENAI_API_KEY")),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }


@app.get("/api/actions")
def actions() -> dict:
    return {
        "actions": [
            {"key": key, "label": ACTION_LABELS[key]} for key in ACTION_PROMPTS
        ]
    }


@app.post("/api/detect", response_model=DetectResponse)
def detect(req: DetectRequest) -> DetectResponse:
    return DetectResponse(language=detect_language(req.code))


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    code = (req.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="No code provided.")
    if len(code) > MAX_CODE_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Code too large ({len(code)} chars). Limit is {MAX_CODE_CHARS}.",
        )
    if req.action not in ACTION_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{req.action}'. Valid: {list(ACTION_PROMPTS)}",
        )

    language = req.language or detect_language(code)

    system_prompt = build_system_prompt(req.audience)
    user_prompt = build_user_prompt(req.action, code, language)

    try:
        result = complete(system_prompt, user_prompt)
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnalyzeResponse(action=req.action, language=language, result=result)
