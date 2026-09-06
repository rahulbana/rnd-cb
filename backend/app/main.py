"""FastAPI application entrypoint.

A fully wired, empty skeleton: health checks, versioned ``/api/v1``,
structured logging, and global exception handling. Every later phase adds an
adapter or route -- never new structure.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.v1.routes import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger("app")
    logger.info(
        "startup",
        app=settings.APP_NAME,
        env=settings.ENV,
        llm=settings.LLM_PROVIDER,
        embedder=settings.EMBEDDER_PROVIDER,
        vector_store=settings.VECTOR_STORE_PROVIDER,
    )
    yield
    logger.info("shutdown", app=settings.APP_NAME)


def create_app() -> FastAPI:
    """Application factory."""
    configure_logging()
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"name": settings.APP_NAME, "docs": "/docs", "api": settings.API_V1_PREFIX}

    return app


app = create_app()
