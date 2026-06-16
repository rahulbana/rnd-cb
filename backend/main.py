"""FastAPI application exposing the resume-rating agent."""
from __future__ import annotations

import io
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from agent import rate_resume
from schemas import RateRequest, RateResponse

load_dotenv()

app = FastAPI(
    title="Resume Rater Agent",
    description="Rate a resume against a job description using OpenAI.",
    version="1.0.0",
)

_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_pdf_text(data: bytes) -> str:
    """Extract text from a PDF file's raw bytes."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


@app.get("/health")
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini")}


@app.post("/api/rate", response_model=RateResponse)
def rate(payload: RateRequest) -> RateResponse:
    """Rate a resume against a job description (both supplied as text)."""
    try:
        return rate_resume(payload.resume, payload.job_description)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the client
        raise HTTPException(status_code=502, detail=f"Rating failed: {exc}") from exc


@app.post("/api/rate-file", response_model=RateResponse)
async def rate_file(
    job_description: str = Form(...),
    resume_file: UploadFile = File(...),
) -> RateResponse:
    """Rate an uploaded resume (PDF or plain text) against a job description."""
    data = await resume_file.read()
    filename = (resume_file.filename or "").lower()

    try:
        if filename.endswith(".pdf"):
            resume_text = _extract_pdf_text(data)
        else:
            resume_text = data.decode("utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail=f"Could not read resume file: {exc}"
        ) from exc

    if not resume_text.strip():
        raise HTTPException(
            status_code=400, detail="No readable text found in the uploaded resume."
        )

    try:
        return rate_resume(resume_text, job_description)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Rating failed: {exc}") from exc
