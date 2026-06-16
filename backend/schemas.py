"""Pydantic models describing the request/response contract of the API."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class RateRequest(BaseModel):
    """Plain-text rating request (resume + job description as strings)."""

    resume: str = Field(..., min_length=1, description="The candidate's resume text.")
    job_description: str = Field(
        ..., min_length=1, description="The job description to rate the resume against."
    )


class CategoryScore(BaseModel):
    """Score for a single evaluation dimension."""

    name: str = Field(..., description="Name of the evaluation dimension.")
    score: int = Field(..., ge=0, le=100, description="Score from 0-100.")
    reasoning: str = Field(..., description="Short justification for the score.")


class RateResponse(BaseModel):
    """Structured rating returned to the frontend."""

    overall_score: int = Field(..., ge=0, le=100, description="Overall match score 0-100.")
    verdict: str = Field(
        ..., description="One-line hiring verdict, e.g. 'Strong match'."
    )
    summary: str = Field(..., description="A short paragraph summarizing the fit.")
    categories: List[CategoryScore] = Field(
        default_factory=list, description="Per-dimension scores."
    )
    matched_skills: List[str] = Field(
        default_factory=list, description="Skills present in both resume and JD."
    )
    missing_skills: List[str] = Field(
        default_factory=list, description="JD skills not found in the resume."
    )
    strengths: List[str] = Field(
        default_factory=list, description="Key strengths of the candidate for this role."
    )
    gaps: List[str] = Field(
        default_factory=list, description="Notable gaps or concerns."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable suggestions to improve the resume for this role.",
    )
