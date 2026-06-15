"""Health / readiness endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: SettingsDep) -> dict:
    """Report service status and configuration readiness."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "model": settings.openai_model,
        "llm_configured": settings.has_api_key,
        "web_research": settings.web_research,
    }
