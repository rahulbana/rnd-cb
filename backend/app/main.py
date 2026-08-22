from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import research

settings = get_settings()

app = FastAPI(
    title="YouTube Research Assistant",
    description=(
        "Summarize YouTube videos, ask questions about them, and generate "
        "mind maps — powered by their transcripts and an OpenAI model."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "model": settings.openai_model,
        "openai_configured": bool(settings.openai_api_key),
    }
