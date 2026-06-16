"""Typed data structures shared across the agent pipeline."""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    """Possible conclusions about a claim, based solely on gathered sources."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    PARTIALLY_TRUE = "PARTIALLY_TRUE"
    UNVERIFIED = "UNVERIFIED"


class Stance(str, Enum):
    """How an individual source relates to the claim."""

    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NEUTRAL = "NEUTRAL"


class Source(BaseModel):
    """A single piece of evidence gathered from the web."""

    index: int
    title: str
    url: str
    content: str
    query: str = Field(description="The search query that surfaced this source.")
    score: float = 0.0


class SourceAssessment(BaseModel):
    """The verdict model's stance on one numbered source."""

    index: int
    stance: Stance
    note: str = Field(description="One line on what this source says about the claim.")


class FactCheckResult(BaseModel):
    """Structured output produced by the verdict model."""

    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    key_findings: List[str] = Field(default_factory=list)
    source_assessments: List[SourceAssessment] = Field(default_factory=list)


class FactCheckReport(BaseModel):
    """The full result returned to the CLI: the verdict plus the evidence it used."""

    claim: str
    result: FactCheckResult
    sources: List[Source]
    queries: List[str]
