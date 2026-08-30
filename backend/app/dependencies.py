"""FastAPI dependency wiring (dependency injection).

Centralizing construction here keeps routes declarative and makes it trivial to
override dependencies in tests (e.g. inject a stub LLM client).
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.core.llm import LLMClient, get_llm_client
from app.database import get_db
from app.services.plan_service import PlanService


def get_orchestrator(
    llm: LLMClient = Depends(get_llm_client),
) -> Orchestrator:
    return Orchestrator(llm)


def get_plan_service(
    db: Session = Depends(get_db),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> PlanService:
    return PlanService(db=db, orchestrator=orchestrator)
