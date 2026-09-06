"""Health, readiness, and active-provider routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe -- the process is up."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness probe. Phase 10 extends this to check datastores."""
    return {"status": "ready"}


@router.get("/providers")
async def providers() -> dict[str, str]:
    """The active adapter behind every port -- the live wiring diagram.

    Proves the config-as-wiring principle: this reflects ``.env``, nothing
    hardcoded.
    """
    return {
        "llm": settings.LLM_PROVIDER,
        "embedder": settings.EMBEDDER_PROVIDER,
        "vector_store": settings.VECTOR_STORE_PROVIDER,
        "reranker": settings.RERANKER_PROVIDER,
        "retriever": settings.RETRIEVER_STRATEGY,
        "parser": settings.PARSER_STRATEGY,
        "chunker": settings.CHUNKER_STRATEGY,
        "storage": settings.STORAGE_PROVIDER,
        "task_queue": settings.TASK_QUEUE_PROVIDER,
    }
