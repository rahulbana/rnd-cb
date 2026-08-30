"""Health and metadata endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...config.settings import get_settings
from ...models.db import get_session
from ...repositories import observability_repository
from ...services.engine import get_orchestrator, get_runtime

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": get_settings().app_name}


@router.get("/meta")
def meta(session: Session = Depends(get_session)) -> dict:
    runtime = get_runtime()
    orchestrator = get_orchestrator()
    settings = get_settings()
    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "llm": {
            "mode": "offline (mock)" if runtime.offline else "openai",
            "model_fast": settings.llm_model_fast,
            "model_strong": settings.llm_model_strong,
        },
        "agents": list(get_orchestrator_agent_names(orchestrator)),
        "tools": orchestrator.tools.list_tools(),
        "observability": observability_repository.summary(session),
    }


def get_orchestrator_agent_names(orchestrator) -> list[str]:
    from ...agents import ALL_AGENTS

    return list(ALL_AGENTS.keys())
