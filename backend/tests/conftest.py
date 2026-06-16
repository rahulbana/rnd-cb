"""Shared pytest fixtures.

The fixtures stub the LLM and web research so the whole agent graph, API and
exporters can be exercised offline, deterministically and without API keys.
"""
from __future__ import annotations

import pytest

from app.schemas import (
    Assessment,
    AssessmentOutput,
    CaseStudy,
    CurriculumOutput,
    FillBlank,
    MCQItem,
    Module,
    MultiSelectItem,
    PlanOutline,
    QuizOutput,
    Resource,
    ResourcesOutput,
    ScheduleOutput,
    Session,
    ShortQA,
    StudyPlan,
    StudyPlanRequest,
    StudyTips,
    TrueFalseItem,
    Week,
)


def _fake_output(schema):
    """Return a deterministic instance of a given agent output schema."""
    if schema is PlanOutline:
        return PlanOutline(
            title="Mastering Quadratics",
            overview="A focused 2-week plan.",
            learning_goals=["Solve quadratic equations"],
            prerequisites=["Basic algebra"],
            delegations=["curriculum: modules"],
        )
    if schema is CurriculumOutput:
        return CurriculumOutput(
            modules=[Module(title="Factoring", objectives=["Factor"], subtopics=["GCF"])]
        )
    if schema is ScheduleOutput:
        return ScheduleOutput(
            weeks=[
                Week(
                    week_number=1,
                    focus="Basics",
                    sessions=[Session(day="Mon", activity="Watch intro", duration_minutes=45)],
                )
            ]
        )
    if schema is ResourcesOutput:
        return ResourcesOutput(
            resources=[
                Resource(type="video", title="Khan Academy", description="Videos",
                         link="https://khanacademy.org")
            ]
        )
    if schema is AssessmentOutput:
        return AssessmentOutput(
            assessments=[
                Assessment(title="Quiz 1", type="quiz", description="Check basics",
                           sample_questions=["Solve x^2-4=0"])
            ]
        )
    if schema is QuizOutput:
        return QuizOutput(
            short_questions=[ShortQA(question="What is a root?", answer="A solution")],
            mcqs=[MCQItem(question="Roots of x^2-4?", options=["2,-2", "1,4"], answer="2,-2")],
            multi_select_mcqs=[
                MultiSelectItem(question="Which are quadratic?", options=["x^2+1", "2x"],
                                answers=["x^2+1"])
            ],
            fill_in_the_blanks=[FillBlank(question="Graph is a ____.", answer="parabola")],
            true_false=[TrueFalseItem(statement="Degree is 2.", answer=True)],
            case_studies=[
                CaseStudy(
                    scenario="A ball is thrown and its height follows h=-5t^2+20t.",
                    questions=[ShortQA(question="When does it land?", answer="At t=4s")],
                )
            ],
            long_questions=[ShortQA(question="Derive the formula.", answer="Complete the square")],
        )
    if schema is StudyTips:
        return StudyTips(tips=["Practice daily", "Review mistakes"])
    raise AssertionError(f"No fake output configured for schema {schema!r}")


@pytest.fixture
def stub_llm(monkeypatch):
    """Replace the LLM call so the graph runs offline and deterministically."""
    from app.agents import llm

    async def fake_run_structured(system, user, schema, temperature=0.3):
        return _fake_output(schema)

    monkeypatch.setattr(llm, "run_structured", fake_run_structured)


@pytest.fixture
def no_research(monkeypatch):
    """Disable web research during tests."""
    from app.services import research

    async def fake(*_args, **_kwargs):
        return ""

    monkeypatch.setattr(research, "research_quiz_context", fake)


@pytest.fixture
def sample_request() -> StudyPlanRequest:
    return StudyPlanRequest(
        grade=9, subject="Mathematics", topic="Quadratic Equations",
        duration_weeks=2, hours_per_week=5,
    )


@pytest.fixture
def sample_plan() -> StudyPlan:
    plan = StudyPlan(
        request=StudyPlanRequest(grade=9, subject="Math", topic="Quadratics"),
        outline=_fake_output(PlanOutline),
        curriculum=_fake_output(CurriculumOutput),
        schedule=_fake_output(ScheduleOutput),
        resources=_fake_output(ResourcesOutput),
        assessment=_fake_output(AssessmentOutput),
        quiz=_fake_output(QuizOutput),
        study_tips=["Practice daily"],
    )
    return plan
