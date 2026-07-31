"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.tracing import LangfuseTracingMiddleware
from app.services import observability

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    observability.configure()
    await init_db()
    yield
    observability.flush()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Records each API request as a single Langfuse trace (no-op when tracing
# is off). Added after CORS so CORS remains the outermost middleware.
app.add_middleware(LangfuseTracingMiddleware)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Serve generated media (banner images).
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
app.mount(
    settings.MEDIA_URL_PREFIX,
    StaticFiles(directory=settings.MEDIA_DIR),
    name="media",
)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "llm_configured": bool(settings.OPENAI_API_KEY),
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "tracing": observability.is_enabled(),
    }
