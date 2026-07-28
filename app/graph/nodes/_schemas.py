"""Internal structured-output schemas for the planning/reflection LLM calls."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlannedQuestion(BaseModel):
    question: str = Field(..., description="A specific, answerable research sub-question.")
    rationale: str = Field(default="", description="Why this matters for the report.")


class ResearchPlan(BaseModel):
    sub_questions: list[PlannedQuestion] = Field(..., min_length=1)


class SearchQueries(BaseModel):
    queries: list[str] = Field(..., min_length=1, description="Flat list of search queries.")


class GapAssessment(BaseModel):
    sufficient: bool = Field(..., description="True if evidence is strong across all sub-questions.")
    gaps: list[str] = Field(
        default_factory=list, description="Concrete missing pieces; empty when sufficient."
    )
