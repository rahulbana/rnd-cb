"""FastAPI application entrypoint for the AI Question Generator."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .grading import grade
from .llm import LLMError, generate_questions
from .schemas import (
    GenerateRequest,
    GenerateResponse,
    GradeRequest,
    GradeResponse,
)

settings = get_settings()

app = FastAPI(
    title="AI Question Generator",
    description="Generate MCQ, True/False, and short-answer study questions "
    "from any topic, then take a quiz and get scored.",
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
    return {
        "status": "ok",
        "model": settings.openai_model,
        "openai_configured": bool(settings.openai_api_key),
    }


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    try:
        questions = generate_questions(req)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return GenerateResponse(
        topic=req.topic,
        difficulty=req.difficulty,
        questions=questions,
    )


@app.post("/api/grade", response_model=GradeResponse)
def grade_quiz(req: GradeRequest) -> GradeResponse:
    return grade(req)
