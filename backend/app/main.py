"""FastAPI application entrypoint for the AI Grammar & Rewriting Assistant."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .llm import TransformError, WritingAssistant
from .schemas import HealthResponse, TransformRequest, TransformResponse

settings = get_settings()
assistant = WritingAssistant(settings)

app = FastAPI(
    title="AI Grammar & Rewriting Assistant",
    description="A Grammarly-like API powered by an LLM.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=settings.openai_model,
        openai_configured=assistant.configured,
    )


@app.post("/api/transform", response_model=TransformResponse)
def transform(req: TransformRequest) -> TransformResponse:
    try:
        return assistant.transform(req.text, req.action)
    except TransformError as exc:
        # 400 for config problems, 502 for upstream/model problems.
        message = str(exc)
        status = 400 if "not configured" in message else 502
        raise HTTPException(status_code=status, detail=message) from exc
