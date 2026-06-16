"""Public schema exports.

Importing from ``app.schemas`` keeps call sites stable regardless of how the
models are organised internally.
"""
from app.schemas.content import (
    Assessment,
    AssessmentOutput,
    CurriculumOutput,
    Module,
    PlanOutline,
    Resource,
    ResourcesOutput,
    ScheduleOutput,
    Session,
    StudyTips,
    Week,
)
from app.schemas.plan import StudyPlan
from app.schemas.quiz import (
    CaseStudy,
    FillBlank,
    MCQItem,
    MultiSelectItem,
    QuizOutput,
    ShortQA,
    TrueFalseItem,
)
from app.schemas.request import StudyPlanRequest

__all__ = [
    "StudyPlanRequest",
    "PlanOutline",
    "Module",
    "CurriculumOutput",
    "Session",
    "Week",
    "ScheduleOutput",
    "Resource",
    "ResourcesOutput",
    "Assessment",
    "AssessmentOutput",
    "StudyTips",
    "ShortQA",
    "MCQItem",
    "MultiSelectItem",
    "FillBlank",
    "TrueFalseItem",
    "CaseStudy",
    "QuizOutput",
    "StudyPlan",
]
