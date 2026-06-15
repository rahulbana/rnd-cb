"""Shared graph state for the multi-agent study-plan workflow."""
from __future__ import annotations

from typing import Optional, TypedDict

from app.schemas import (
    AssessmentOutput,
    CurriculumOutput,
    PlanOutline,
    QuizOutput,
    ResourcesOutput,
    ScheduleOutput,
    StudyPlanRequest,
)


class PlanState(TypedDict, total=False):
    """State passed between agent nodes.

    Each node writes to a distinct key, so the fan-out branches can run in
    parallel without conflicting reducers.
    """

    request: StudyPlanRequest
    outline: PlanOutline
    curriculum: CurriculumOutput
    schedule: ScheduleOutput
    resources: ResourcesOutput
    assessment: AssessmentOutput
    quiz: QuizOutput
    study_tips: list[str]
    error: Optional[str]
