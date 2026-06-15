"""Pydantic schemas shared between the API and the agent graph."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Request                                                                      #
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Sub-agent structured outputs                                                 #
# --------------------------------------------------------------------------- #
class PlanOutline(BaseModel):
    title: str = Field(..., description="Catchy, clear title for the study plan.")
    overview: str = Field(..., description="2-4 sentence overview of the plan.")
    learning_goals: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    delegations: List[str] = Field(
        default_factory=list,
        description="Short notes on what each specialist agent should focus on.",
    )


class Module(BaseModel):
    title: str
    objectives: List[str] = Field(default_factory=list)
    subtopics: List[str] = Field(default_factory=list)


class CurriculumOutput(BaseModel):
    modules: List[Module] = Field(default_factory=list)


class Session(BaseModel):
    day: str = Field(..., description="Which day, e.g. 'Day 1' or 'Mon'.")
    activity: str
    duration_minutes: int = Field(60, ge=10, le=480)


class Week(BaseModel):
    week_number: int
    focus: str
    sessions: List[Session] = Field(default_factory=list)


class ScheduleOutput(BaseModel):
    weeks: List[Week] = Field(default_factory=list)


class Resource(BaseModel):
    type: str = Field(..., description="video | book | article | exercise | tool")
    title: str
    description: str
    link: Optional[str] = None


class ResourcesOutput(BaseModel):
    resources: List[Resource] = Field(default_factory=list)


class Assessment(BaseModel):
    title: str
    type: str = Field(..., description="quiz | project | practice | self-check")
    description: str
    sample_questions: List[str] = Field(default_factory=list)


class AssessmentOutput(BaseModel):
    assessments: List[Assessment] = Field(default_factory=list)


class StudyTips(BaseModel):
    tips: List[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Quiz                                                                         #
# --------------------------------------------------------------------------- #
class ShortQA(BaseModel):
    question: str
    answer: str


class MCQItem(BaseModel):
    question: str
    options: List[str] = Field(default_factory=list)
    answer: str = Field(..., description="The single correct option text.")


class MultiSelectItem(BaseModel):
    """MMCQ — multiple correct answers."""

    question: str
    options: List[str] = Field(default_factory=list)
    answers: List[str] = Field(
        default_factory=list, description="All correct option texts."
    )


class FillBlank(BaseModel):
    question: str = Field(..., description="A sentence containing a ____ blank.")
    answer: str


class TrueFalseItem(BaseModel):
    statement: str
    answer: bool


class QuizOutput(BaseModel):
    short_questions: List[ShortQA] = Field(default_factory=list)
    mcqs: List[MCQItem] = Field(default_factory=list)
    multi_select_mcqs: List[MultiSelectItem] = Field(default_factory=list)
    fill_in_the_blanks: List[FillBlank] = Field(default_factory=list)
    true_false: List[TrueFalseItem] = Field(default_factory=list)
    long_questions: List[ShortQA] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Final compiled plan                                                          #
# --------------------------------------------------------------------------- #
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
