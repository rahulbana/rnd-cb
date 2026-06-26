"""Health / readiness endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from ...schemas.search import HealthResponse
from ..deps import SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=settings.openai_model,
        search_provider=settings.resolved_search_provider,
        openai_configured=bool(settings.openai_api_key),
    )
