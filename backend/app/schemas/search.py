"""Request / response models for the search API."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .source import Source


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's research question.")
    num_subqueries: Optional[int] = Field(
        default=None, ge=1, le=10, description="How many sub-queries to generate."
    )


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    model: str
    search_provider: str
    openai_configured: bool


class LivenessResponse(BaseModel):
    status: str = "alive"
    uptime_seconds: float


class ReadinessResponse(BaseModel):
    ready: bool
    checks: Dict[str, bool]


class ReportResult(BaseModel):
    """Final result payload (also available as the 'report' SSE event)."""

    query: str
    report: str
    sources: List[Source] = Field(default_factory=list)
