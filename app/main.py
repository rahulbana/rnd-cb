"""FastAPI application: API routes, NDJSON streaming, and static UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import config
from .llm import MODEL, count_tokens
from .models import (
    SUMMARY_FORMATS,
    SUMMARY_LENGTHS,
    SUMMARY_STYLES,
    ExtractRequest,
    SummarizeRequest,
)
from . import prompts
from .summarizer import extract_structured, summarize_streaming

# The React frontend (frontend/) builds into ./public, which we serve at "/".
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
MAX_INPUT_CHARS = 5_000_000  # ~1.25M tokens — a hard guard against runaway inputs

app = FastAPI(title="AI Text Summarizer")


# The frontend reads an `error` field on failures; normalize FastAPI's default
# `detail` shape to match for both raised HTTPExceptions and validation errors.
@app.exception_handler(HTTPException)
async def _http_exc_handler(_req: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def _validation_exc_handler(
    _req: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": str(exc.errors())})


def _guard_text(text: str) -> None:
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")
    if len(text) > MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Input too large ({len(text)} chars; max {MAX_INPUT_CHARS}).",
        )


@app.get("/api/config")
async def get_config() -> dict:
    """Expose the option vocabulary and active model so the UI can render itself."""
    return {
        "model": MODEL,
        "lengths": SUMMARY_LENGTHS,
        "styles": SUMMARY_STYLES,
        "formats": SUMMARY_FORMATS,
    }


@app.post("/api/count-tokens")
async def count_tokens_route(req: SummarizeRequest) -> dict:
    """Token estimate for the exact request that would be sent, without running it."""
    _guard_text(req.text)
    system = prompts.build_system_prompt(req)
    user = prompts.build_user_prompt(req.text)
    return {"inputTokens": count_tokens(system, user), "model": MODEL}


@app.post("/api/summarize")
async def summarize_route(req: SummarizeRequest) -> StreamingResponse:
    """Streaming summary. Emits newline-delimited JSON (NDJSON) stream events."""
    _guard_text(req.text)

    async def gen() -> AsyncIterator[bytes]:
        try:
            async for event in summarize_streaming(req):
                yield (json.dumps(event) + "\n").encode("utf-8")
        except Exception as exc:  # noqa: BLE001 — surface any failure to the client
            yield (json.dumps({"type": "error", "message": str(exc)}) + "\n").encode(
                "utf-8"
            )

    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@app.post("/api/extract")
async def extract_route(req: ExtractRequest) -> JSONResponse:
    """Structured JSON extraction (non-streaming)."""
    _guard_text(req.text)
    try:
        structured = await extract_structured(req.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(structured.model_dump())


# Serve the built React frontend if present. Mounted last so the /api/* routes
# above take precedence; html=True serves public/index.html at "/". When the
# frontend hasn't been built yet, show instructions instead of failing to start.
if (PUBLIC_DIR / "index.html").is_file():
    app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")
else:

    @app.get("/")
    async def _needs_build() -> HTMLResponse:
        return HTMLResponse(
            "<h1>Frontend not built</h1>"
            "<p>Build the React app first:</p>"
            "<pre>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</pre>"
            "<p>Then reload. The API is already running at <code>/api/*</code>.</p>",
            status_code=503,
        )
