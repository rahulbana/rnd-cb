"""Health, readiness, and active-provider routes.

- ``/health`` is the **liveness** probe: the process is up. It never touches a
  datastore, so a transient DB blip can't trigger a pod restart loop.
- ``/ready`` is the **readiness** probe: checks the datastores the app needs to
  serve traffic (Postgres, and Redis when Celery is the task queue). A failing
  dependency returns 503 so the orchestrator (Cloud Run / k8s) stops routing
  requests until it recovers.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe -- the process is up. No datastore access."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}


def _check_database() -> tuple[bool, str]:
    """Run ``SELECT 1`` against the configured database."""
    try:
        from app.db.base import get_engine  # noqa: PLC0415

        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:  # pragma: no cover - exercised via fake failures
        return False, f"error: {exc.__class__.__name__}"


def _check_redis() -> tuple[bool, str]:
    """Ping Redis. Only meaningful when Celery is the task queue."""
    if settings.TASK_QUEUE_PROVIDER != "celery":
        return True, "skipped"
    try:
        import redis  # noqa: PLC0415

        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        client.ping()
        return True, "ok"
    except Exception as exc:  # pragma: no cover - exercised via fake failures
        return False, f"error: {exc.__class__.__name__}"


@router.get("/ready")
async def ready(response: Response) -> dict[str, Any]:
    """Readiness probe -- verifies the datastores needed to serve traffic."""
    checks: dict[str, str] = {}
    ok = True

    db_ok, db_detail = _check_database()
    checks["database"] = db_detail
    ok = ok and db_ok

    redis_ok, redis_detail = _check_redis()
    checks["redis"] = redis_detail
    ok = ok and redis_ok

    if not ok:
        response.status_code = 503
    return {"status": "ready" if ok else "not_ready", "checks": checks}


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
        "tracer": settings.TRACER_PROVIDER,
        "eval_harness": settings.EVAL_HARNESS,
        "secret_provider": settings.SECRET_PROVIDER,
    }
