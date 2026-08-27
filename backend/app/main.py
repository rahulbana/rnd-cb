"""FastAPI application entrypoint.

Wires configuration, structured logging, Postgres persistence (LangGraph
checkpointer), the research service, and the HTTP/SSE routes. Persistence and
background runs are managed by the lifespan so resources open on startup and
drain cleanly on shutdown.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as research_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.persistence import Persistence
from app.services.research_service import ResearchService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set; research runs will fail until configured")

    persistence = Persistence()
    await persistence.open(settings)
    app.state.persistence = persistence
    app.state.research_service = ResearchService(persistence.checkpointer, settings)
    logger.info("application startup complete", extra={"environment": settings.environment})

    try:
        yield
    finally:
        await app.state.research_service.shutdown()
        await persistence.close()
        logger.info("application shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Deep Research Agent",
        version="1.0.0",
        description="Autonomous LangGraph research agent (OpenAI + Tavily/DuckDuckGo) "
        "with durable Postgres-checkpointed state for long-running tasks.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(research_router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
