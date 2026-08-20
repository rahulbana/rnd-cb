"""FastAPI application: upload a document, get notes + questions back.

No data is persisted. Uploaded files are parsed in memory and discarded once the
response is returned.
"""
from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .document_parser import UnsupportedFileError, parse_document
from .html_generator import render_html, render_variants
from .llm import LLMConfigError, generate_study_material
from .ocr import OCRError
from .web_research import ResearchResult, gather_references
from .schemas import (
    QUESTION_TYPE_LABELS,
    QUESTION_TYPES,
    Downloads,
    GenerateResponse,
)

app = FastAPI(
    title="Study Notes & Question Generator",
    description="Turn documents into revision notes and practice questions.",
    version="1.0.0",
)

# Allow the React dev server (and any origin, since there's no stored data) to
# call the API. Tighten ALLOWED_ORIGINS in production if desired.
_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
_origins = ["*"] if _origins_env.strip() == "*" else [
    o.strip() for o in _origins_env.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Reject files that are too large to keep memory usage bounded (default 15 MB).
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))


@app.get("/api/health")
def health():
    from .ocr import is_ocr_configured
    from .web_research import is_enabled as web_search_enabled

    return {
        "status": "ok",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "ocr_available": is_ocr_configured(),
        "web_search_enabled": web_search_enabled(),
    }


@app.get("/api/question-types")
def question_types():
    """List the supported question types for the UI to render toggles."""
    return {"types": [{"id": t, "label": QUESTION_TYPE_LABELS[t]} for t in QUESTION_TYPES]}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(
    file: UploadFile = File(...),
    question_types: str = Form(",".join(QUESTION_TYPES)),
    grade_level: str = Form(""),
    web_search: bool = Form(True),
    coverage: str = Form("thorough"),
):
    """Parse the uploaded document and generate notes + questions."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )

    # 1. Extract text from the document (OCR is used automatically for scanned
    #    PDFs and image uploads).
    try:
        parsed = parse_document(file.filename or "", data)
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    except OCRError as exc:
        # Local OCR (Tesseract) is unavailable on the server.
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        raise HTTPException(status_code=400, detail=f"Could not read the file: {exc}")
    text = parsed.text

    # 2. Determine which question types to generate.
    selected: List[str] = [
        t.strip() for t in question_types.split(",") if t.strip() in QUESTION_TYPES
    ]
    if not selected:
        selected = list(QUESTION_TYPES)

    # 3. Optionally research reference material online to enrich the output.
    research = ResearchResult()
    if web_search:
        try:
            research = gather_references(text, grade_level)
        except Exception:  # noqa: BLE001 - research is best-effort
            research = ResearchResult()

    # 4. Generate study material with the LLM (using any research context).
    try:
        material = generate_study_material(
            text, selected, grade_level=grade_level,
            research_context=research.context, coverage=coverage,
        )
    except LLMConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"Generation failed: {exc}"
        )

    # 5. Render the three downloadable, self-contained HTML documents:
    #    notes, questions+answers, and questions-only (practice sheet).
    variants = render_variants(
        material, file.filename or "document", grade_level, sources=research.sources
    )

    return GenerateResponse(
        source_filename=file.filename or "document",
        grade_level=grade_level or None,
        ocr_used=parsed.ocr_used,
        web_search_used=research.used,
        sources=research.sources,
        material=material,
        downloads=Downloads(**variants),
    )


@app.post("/api/generate/html", response_class=HTMLResponse)
async def generate_html(
    file: UploadFile = File(...),
    question_types: str = Form(",".join(QUESTION_TYPES)),
    grade_level: str = Form(""),
    variant: str = Form("questions_with_answers"),
):
    """Same as /api/generate but returns a single raw HTML document.

    ``variant`` is one of: notes, questions_with_answers, questions_only.
    """
    result: GenerateResponse = await generate(file, question_types, grade_level)  # type: ignore[arg-type]
    html_doc = getattr(result.downloads, variant, None)
    if html_doc is None:
        raise HTTPException(
            status_code=400,
            detail="variant must be one of: notes, questions_with_answers, questions_only",
        )
    return HTMLResponse(content=html_doc)


@app.exception_handler(Exception)
async def unhandled(_request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"Unexpected error: {exc}"})
