"""FastAPI application factory — the always-on AutoDev engine."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import get_settings
from .database import init_db
from .services import run_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("autodev")

_STATIC_DIR = Path(__file__).parent / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db()
    recovered = run_manager.recover_orphans()
    logger.info(
        "AutoDev started | provider=%s | workspace=%s | recovered=%d",
        settings.llm_provider,
        settings.workspace_root_path,
        recovered,
    )
    yield
    logger.info("AutoDev shutting down")


def create_app() -> FastAPI:
    app = FastAPI(title="AutoDev", version="0.1.0", lifespan=lifespan)
    app.include_router(router)

    if _STATIC_DIR.exists():
        app.mount(
            "/static", StaticFiles(directory=str(_STATIC_DIR)), name="static"
        )

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(str(_STATIC_DIR / "index.html"))

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
