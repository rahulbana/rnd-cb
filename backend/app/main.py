"""FastAPI application entrypoint.

Run locally with:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import routes_documents, routes_health, routes_ws
from .config import get_settings
from .core.logging import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router)
    app.include_router(routes_documents.router)
    app.include_router(routes_ws.router)

    @app.on_event("startup")
    async def _startup() -> None:
        log.info("%s starting (env=%s, llm=%s, retrieval=%s)",
                 settings.app_name, settings.environment,
                 settings.llm_provider, settings.retrieval_strategy)

    return app


app = create_app()
