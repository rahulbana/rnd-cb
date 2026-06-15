"""The final compiled study plan."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from app.schemas.content import (
    AssessmentOutput,
    CurriculumOutput,
    PlanOutline,
    ResourcesOutput,
    ScheduleOutput,
)
from app.schemas.quiz import QuizOutput
from app.schemas.request import StudyPlanRequest


class StudyPlan(BaseModel):
    request: StudyPlanRequest
    outline: PlanOutline
    curriculum: CurriculumOutput
    schedule: ScheduleOutput
    resources: ResourcesOutput
    assessment: AssessmentOutput
    quiz: QuizOutput = Field(default_factory=QuizOutput)
    study_tips: List[str] = Field(default_factory=list)
    markdown: str = Field("", description="Full plan rendered as Markdown for download.")
