"""Chunking Strategy Explorer — FastAPI application.

Upload a text document, pick a chunking strategy, tune its parameters, and see
every chunk it produces alongside an impact analysis (size distribution,
overlap redundancy, and how often the strategy cuts through words/sentences).

Run:  uvicorn app.main:app --reload
"""

from __future__ import annotations

import io
import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .chunkers import STRATEGIES, run_strategy
from .stats import analyze

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Chunking Strategy Explorer", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

MAX_BYTES = 2 * 1024 * 1024  # 2 MB upload cap


def _strategies_payload() -> list[dict]:
    payload = []
    for s in STRATEGIES.values():
        payload.append(
            {
                "key": s.key,
                "label": s.label,
                "description": s.description,
                "requires_openai": s.requires_openai,
                "available": (not s.requires_openai) or bool(os.getenv("OPENAI_API_KEY")),
                "params": [vars(p) for p in s.params],
            }
        )
    return payload


def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "strategies": _strategies_payload(),
            "openai_enabled": bool(os.getenv("OPENAI_API_KEY")),
        },
    )


@app.get("/api/strategies")
async def api_strategies():
    return {"strategies": _strategies_payload()}


@app.post("/api/chunk")
async def api_chunk(
    strategy: str = Form(...),
    params: str = Form("{}"),
    text: str = Form(""),
    file: UploadFile | None = File(None),
):
    import json

    if strategy not in STRATEGIES:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}")

    # Prefer an uploaded file; fall back to pasted text.
    content = ""
    filename = None
    if file is not None and file.filename:
        raw = await file.read()
        if len(raw) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 2 MB).")
        content = _decode(raw)
        filename = file.filename
    elif text.strip():
        content = text

    if not content.strip():
        raise HTTPException(status_code=400, detail="No text provided. Upload a file or paste text.")

    try:
        parsed_params = json.loads(params) if params else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid parameters payload.")

    # Coerce known numeric params to int/float based on the strategy spec.
    spec = {p.name: p for p in STRATEGIES[strategy].params}
    clean_params = {}
    for name, value in parsed_params.items():
        p = spec.get(name)
        if p is None:
            continue
        try:
            if p.type == "int":
                clean_params[name] = int(value)
            elif p.type == "float":
                clean_params[name] = float(value)
            elif p.type == "bool":
                clean_params[name] = bool(value)
            else:
                clean_params[name] = value
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid value for {p.label}.")

    try:
        chunks = run_strategy(strategy, content, clean_params)
    except RuntimeError as exc:  # e.g. missing OpenAI key
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Chunking failed: {exc}")

    stats = analyze(chunks, content)

    return JSONResponse(
        {
            "strategy": strategy,
            "strategy_label": STRATEGIES[strategy].label,
            "filename": filename,
            "params": clean_params,
            "stats": stats,
            "chunks": [c.to_dict() for c in chunks],
        }
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
