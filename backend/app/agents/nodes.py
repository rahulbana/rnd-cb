"""Agent node implementations for the study-plan graph.

The architecture is a supervisor / multi-agent pattern:

    planner (lead agent)
        |
        +--> curriculum agent  -.
        +--> scheduler agent     \\  (run in parallel)
        +--> resources agent     /
        +--> assessment agent  -'
        |
    compiler (lead agent assembles the final plan + study tips)

The lead "planner" agent designs the high-level plan and delegates focused
briefs to each specialist agent. The compiler synthesises everything back
into one coherent study plan.
"""
from __future__ import annotations

from app.agents.llm import run_structured
from app.agents.state import PlanState, request_summary
from app.services.search import research_quiz_context
from app.schemas import (
    AssessmentOutput,
    CurriculumOutput,
    PlanOutline,
    QuizOutput,
    ResourcesOutput,
    ScheduleOutput,
    StudyTips,
)

GRADE_TONE = (
    "Write at a reading level and complexity appropriate for the student's "
    "class/grade. Use age-appropriate language, concrete examples, and an "
    "encouraging tone."
)


async def planner_node(state: PlanState) -> PlanState:
    """Lead agent: creates the outline and delegation briefs."""
    req = state["request"]
    system = (
        "You are the lead study-plan architect for school students. "
        "You design the overall plan and decide what each specialist agent "
        "(curriculum, scheduler, resources, assessment) should focus on. "
        + GRADE_TONE
    )
    user = (
        f"Create the high-level outline for this student:\n\n{request_summary(req)}\n\n"
        "Provide a title, a short overview, concrete learning goals, any "
        "prerequisites, and a short delegation note for each specialist agent."
    )
    outline = await run_structured(system, user, PlanOutline, temperature=0.4)
    return {"outline": outline}


async def curriculum_node(state: PlanState) -> PlanState:
    """Specialist agent: breaks the topic into modules and objectives."""
    req = state["request"]
    outline = state["outline"]
    system = (
        "You are a curriculum designer. Break the topic into a logical sequence "
        "of learning modules, each with clear objectives and subtopics. " + GRADE_TONE
    )
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Overall plan: {outline.title} — {outline.overview}\n"
        f"Learning goals: {', '.join(outline.learning_goals) or 'n/a'}\n\n"
        "Produce 3-6 modules that build on each other from foundations to mastery."
    )
    curriculum = await run_structured(system, user, CurriculumOutput, temperature=0.3)
    return {"curriculum": curriculum}


async def scheduler_node(state: PlanState) -> PlanState:
    """Specialist agent: lays out a realistic week-by-week schedule."""
    req = state["request"]
    outline = state["outline"]
    system = (
        "You are a study scheduler. Build a realistic, balanced timetable that "
        "fits the student's available time, with focused sessions and built-in "
        "review and rest. " + GRADE_TONE
    )
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Overall plan: {outline.title} — {outline.overview}\n\n"
        f"Create exactly {req.duration_weeks} week(s). Each week should have a focus "
        f"and several sessions whose total time fits about {req.hours_per_week} "
        "hours/week. Keep sessions specific and actionable."
    )
    schedule = await run_structured(system, user, ScheduleOutput, temperature=0.3)
    return {"schedule": schedule}


async def resources_node(state: PlanState) -> PlanState:
    """Specialist agent: recommends learning resources."""
    req = state["request"]
    outline = state["outline"]
    system = (
        "You are a learning-resources curator. Recommend a varied, high-quality "
        "mix of free and accessible resources (videos, articles, books, practice "
        "exercises, tools). Only suggest links you are confident exist; otherwise "
        "describe the resource without a link. " + GRADE_TONE
    )
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Overall plan: {outline.title} — {outline.overview}\n\n"
        "Recommend 5-8 resources covering different learning styles."
    )
    resources = await run_structured(system, user, ResourcesOutput, temperature=0.4)
    return {"resources": resources}


async def assessment_node(state: PlanState) -> PlanState:
    """Specialist agent: designs checkpoints and assessments."""
    req = state["request"]
    outline = state["outline"]
    system = (
        "You are an assessment designer. Create checkpoints, quizzes, practice "
        "sets and a small project so the student can measure progress. " + GRADE_TONE
    )
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Overall plan: {outline.title} — {outline.overview}\n\n"
        "Create 3-5 assessments with sample questions, increasing in difficulty."
    )
    assessment = await run_structured(system, user, AssessmentOutput, temperature=0.4)
    return {"assessment": assessment}


async def quiz_node(state: PlanState) -> PlanState:
    """Specialist agent: researches board materials, then generates a quiz."""
    req = state["request"]
    outline = state["outline"]

    # Ground the quiz in real board materials when web research is available.
    references = await research_quiz_context(req.grade, req.subject, req.topic)
    reference_block = ""
    if references:
        reference_block = (
            "\nReference material gathered from the web (board sites like CBSE/"
            "ICSE, previous-year papers and teacher notes/quizzes). Use it to "
            "match the style, difficulty and commonly-tested points of these "
            "boards. Do NOT copy any text verbatim — write original, "
            "paraphrased questions grounded in these references:\n"
            f"{references}\n"
        )

    system = (
        "You are an expert quiz master and question-paper setter for school "
        "students, familiar with CBSE, ICSE and state-board exam patterns. You "
        "generate large, varied question banks with correct answers. Make "
        "questions accurate, unambiguous and grade-appropriate, and cover the "
        "topic broadly across difficulty levels. " + GRADE_TONE
    )
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Topic context: {outline.title} — {outline.overview}\n"
        f"Learning goals: {', '.join(outline.learning_goals) or 'n/a'}\n"
        f"{reference_block}\n"
        "Create an ABUNDANT practice quiz covering the topic. Provide:\n"
        "- short_questions: 8-10 short-answer questions, each with a concise answer.\n"
        "- mcqs: 8-10 multiple-choice questions, each with 4 options and exactly "
        "one correct answer (answer must match one option verbatim).\n"
        "- multi_select_mcqs: 5-6 multiple-correct questions (MMCQ), each with "
        "4-5 options and 2+ correct answers (answers must match options verbatim).\n"
        "- fill_in_the_blanks: 8-10 sentences each containing a '____' blank, "
        "with the answer.\n"
        "- true_false: 6-8 statements with a boolean answer.\n"
        "- long_questions: 4-5 descriptive/long-answer questions with model answers.\n"
        "Ensure variety and avoid duplicates."
    )
    quiz = await run_structured(system, user, QuizOutput, temperature=0.6)
    return {"quiz": quiz}


async def compiler_node(state: PlanState) -> PlanState:
    """Lead agent: synthesises final study tips from all specialist output."""
    req = state["request"]
    outline = state["outline"]
    system = (
        "You are the lead study coach assembling the final plan. Provide a short "
        "list of practical, motivating study tips tailored to the student. "
        + GRADE_TONE
    )
    module_titles = ", ".join(m.title for m in state["curriculum"].modules) or "n/a"
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Plan: {outline.title}. Modules: {module_titles}.\n\n"
        "Give 4-6 concise study tips (habits, focus techniques, how to use the "
        "resources and assessments effectively)."
    )

    tips = await run_structured(system, user, StudyTips, temperature=0.5)
    return {"study_tips": tips.tips}
