"""Application entrypoint: builds the FastAPI app via a factory.

Run with:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import api_router
from .core.config import Settings, get_settings
from .core.exceptions import AppError
from .core.logging import configure_logging, get_logger


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    app = FastAPI(title="Deep Search Agent", version="2.0.0")

    origins = ["*"] if settings.frontend_origin == "*" else [settings.frontend_origin]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        logger.error("AppError: %s", exc.message)
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})

    logger.info(
        "Deep Search Agent ready | model=%s | search=%s",
        settings.openai_model,
        settings.resolved_search_provider,
    )
    return app


app = create_app()
