"""Inbound request schema."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StudyPlanRequest(BaseModel):
    """Input describing the student and what they want to study."""

    grade: int = Field(..., ge=5, le=12, description="Student class/grade (5-12).")
    subject: str = Field(..., min_length=1, description="Subject, e.g. 'Mathematics'.")
    topic: str = Field(..., min_length=1, description="Topic, e.g. 'Quadratic Equations'.")
    duration_weeks: int = Field(2, ge=1, le=52, description="Plan length in weeks.")
    hours_per_week: int = Field(5, ge=1, le=40, description="Study hours available per week.")
    goal: str = Field(
        "build a strong conceptual understanding",
        description="What the student wants to achieve.",
    )
    level: str = Field(
        "intermediate",
        description="Current level: beginner | intermediate | advanced.",
    )
    notes: Optional[str] = Field(
        None, description="Any extra context, e.g. exam dates or weak areas."
    )
