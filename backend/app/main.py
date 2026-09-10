"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .analyzer import using_openai
from .config import get_settings
from .routers import analysis

settings = get_settings()

app = FastAPI(
    title="AI Sentiment Analyzer",
    description="Analyze sentiment and emotion of text, in single or batch mode.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    """Health check and backend capability info."""
    return {
        "status": "ok",
        "engine": "openai" if using_openai() else "lexicon-fallback",
        "model": settings.openai_model if using_openai() else None,
        "max_batch_size": settings.max_batch_size,
    }
