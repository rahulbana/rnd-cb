"""Request/response models for the HTTP API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=2000, description="The research question.")


class ResearchStartResponse(BaseModel):
    thread_id: str
    status: str = "running"


class SourceOut(BaseModel):
    title: str = ""
    url: str = ""
    provider: str = ""


class ResearchStateResponse(BaseModel):
    thread_id: str
    topic: str = ""
    status: str  # running | completed | not_found
    iteration: int = 0
    is_complete: bool = False
    plan: list[str] = Field(default_factory=list)
    findings_count: int = 0
    sources: list[SourceOut] = Field(default_factory=list)
    final_report: str = ""
