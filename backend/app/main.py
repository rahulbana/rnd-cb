"""FastAPI application exposing the resume analysis endpoint."""
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import AnalyzeResponse
from app.services.analyzer import AnalysisError, analyze_resume
from app.services.pdf import PDFExtractionError, extract_text

app = FastAPI(
    title="AI Resume Analyzer",
    description="Upload a PDF resume and receive AI-generated feedback.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "llm_configured": settings.llm_configured}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)) -> AnalyzeResponse:
    # Validate content type / extension.
    filename = file.filename or "resume.pdf"
    is_pdf = (file.content_type == "application/pdf") or filename.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=413, detail=f"File too large. Maximum size is {limit_mb} MB."
        )

    # Extract text.
    try:
        resume_text = extract_text(data)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Analyze with the LLM.
    try:
        analysis = analyze_resume(resume_text)
    except AnalysisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnalyzeResponse(
        filename=filename,
        characters_extracted=len(resume_text),
        analysis=analysis,
    )
