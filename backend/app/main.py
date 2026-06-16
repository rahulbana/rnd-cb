"""FastAPI entrypoint for the CSV Insight Agent."""

from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .analysis import profile_dataframe, read_csv
from .config import settings
from .llm_agent import generate_insights
from .models import AnalysisResponse

app = FastAPI(
    title="CSV Insight Agent",
    description="Autonomous agent that profiles a CSV from multiple perspectives "
    "and returns inferences plus interactive chart specs.",
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
def health() -> dict[str, object]:
    """Lightweight readiness probe; also tells the UI if the LLM is active."""
    return {
        "status": "ok",
        "llm_enabled": settings.llm_enabled,
        "model": settings.openai_model if settings.llm_enabled else None,
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)) -> AnalysisResponse:
    """Accept a CSV upload and return the full analysis payload."""
    if not file.filename or not file.filename.lower().endswith((".csv", ".tsv", ".txt")):
        raise HTTPException(status_code=400, detail="Please upload a .csv/.tsv/.txt file.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_upload_bytes // (1024 * 1024)} MB).",
        )

    try:
        df = read_csv(raw, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if df.shape[0] == 0 or df.shape[1] == 0:
        raise HTTPException(status_code=422, detail="No tabular data found in the file.")

    profile = profile_dataframe(df, file.filename)
    insights, llm_used = generate_insights(
        profile["overview"],
        profile["columns"],
        profile["correlations"],
        profile["sample_rows"],
    )

    return AnalysisResponse(
        overview=profile["overview"],
        columns=profile["columns"],
        correlations=profile["correlations"],
        charts=profile["charts"],
        inferences=insights["inferences"],
        narrative=insights["narrative"],
        suggested_questions=insights["suggested_questions"],
        llm_used=llm_used,
        sample_rows=profile["sample_rows"],
    )
