"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import history, sql
from .schemas import HealthResponse

settings = get_settings()

app = FastAPI(
    title="AI SQL Generator",
    description="Convert natural-language questions into read-only SQL.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sql.router, prefix="/api")
app.include_router(history.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        llm_configured=settings.llm_configured,
        model=settings.openai_model,
        dialect=settings.sql_dialect,
    )
