"""FastAPI application entrypoint.

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import router
from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database import init_db

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure schema exists.
    init_db()
    logger.info(
        "app_startup",
        extra={"extra": {"env": settings.app_env, "llm_enabled": settings.llm_enabled}},
    )
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title="Diet Planner Multi-Agent API",
    version=__version__,
    description=(
        "Multi-agent diet planning: intake validation, deterministic nutrition "
        "calculation, LLM meal planning, and a safety review."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so internal errors never leak stack traces to clients."""
    logger.error(
        "unhandled_exception",
        extra={"extra": {"path": str(request.url.path)}},
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": "diet-planner", "docs": "/docs", "health": "/api/v1/health"}
