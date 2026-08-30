"""FastAPI application entrypoint.

Wires configuration, logging, the API router, CORS, global error handling and
(optionally) serves the static frontend so the whole product runs from a single
process during development.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.v1 import api_router
from .config.logging import configure_logging, get_logger
from .config.settings import get_settings
from .models.db import init_db

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    settings = get_settings()
    logger.info("%s starting (env=%s, llm=%s)", settings.app_name, settings.environment,
                "openai" if settings.llm_enabled else "offline-mock")
    yield
    from .tools.http import aclose
    await aclose()
    logger.info("shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        description="AI-powered multi-agent travel planner.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # pragma: no cover - defensive
            logger.exception("unhandled error [%s] %s %s", request_id, request.method, request.url.path)
            return JSONResponse(status_code=500, content={"detail": "Internal server error",
                                                          "request_id": request_id})
        elapsed = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info("[%s] %s %s -> %s (%.1fms)", request_id, request.method,
                    request.url.path, response.status_code, elapsed)
        return response

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Serve the static frontend if present (single-process dev convenience).
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = create_app()
