"""Health / liveness / readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Response

from ...core.runtime import APP_VERSION, uptime_seconds
from ...providers.llm import get_llm_provider
from ...providers.search import get_search_provider
from ...schemas.search import HealthResponse, LivenessResponse, ReadinessResponse
from ..deps import SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    """General status snapshot (model, provider, version, uptime)."""
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        uptime_seconds=round(uptime_seconds(), 1),
        model=settings.openai_model,
        search_provider=settings.resolved_search_provider,
        openai_configured=bool(settings.openai_api_key),
    )


@router.get("/health/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """Liveness probe: the process is up and serving."""
    return LivenessResponse(uptime_seconds=round(uptime_seconds(), 1))


@router.get("/health/ready")
async def readiness(settings: SettingsDep, response: Response) -> ReadinessResponse:
    """Readiness probe: dependencies are configured and constructible."""
    checks: dict[str, bool] = {}

    try:
        get_llm_provider(settings)
        checks["llm_provider"] = True
    except Exception:  # noqa: BLE001 - readiness must not raise
        checks["llm_provider"] = False

    try:
        get_search_provider(settings)
        checks["search_provider"] = True
    except Exception:  # noqa: BLE001
        checks["search_provider"] = False

    ready = all(checks.values())
    if not ready:
        response.status_code = 503
    return ReadinessResponse(ready=ready, checks=checks)
