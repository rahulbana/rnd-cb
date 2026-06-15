"""Structured outputs produced by the planner and specialist agents."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


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
