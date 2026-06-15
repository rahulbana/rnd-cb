"""FastAPI application factory for the multi-agent study planner."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.graph import build_graph
from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("main")

    build_graph()  # compile/validate the agent graph at startup
    if not settings.has_api_key:
        log.warning("OPENAI_API_KEY is not set — plan generation will fail until configured.")
    log.info(
        "%s v%s started (model=%s, web_research=%s)",
        settings.app_name,
        settings.app_version,
        settings.openai_model,
        settings.web_research,
    )
    yield
    log.info("shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Agentic study-plan generator for students (class 5-12).",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
