"""Shared graph state for the multi-agent study-plan workflow."""
from __future__ import annotations

from typing import Optional, TypedDict

from app.schemas import (
    AssessmentOutput,
    CurriculumOutput,
    PlanOutline,
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
    study_tips: list[str]
    error: Optional[str]


def request_summary(req: StudyPlanRequest) -> str:
    """A compact, reusable description of the student's request for prompts."""
    parts = [
        f"Class/Grade: {req.grade}",
        f"Subject: {req.subject}",
        f"Topic: {req.topic}",
        f"Plan length: {req.duration_weeks} week(s)",
        f"Time available: {req.hours_per_week} hour(s) per week",
        f"Current level: {req.level}",
        f"Goal: {req.goal}",
    ]
    if req.notes:
        parts.append(f"Extra notes: {req.notes}")
    return "\n".join(parts)
