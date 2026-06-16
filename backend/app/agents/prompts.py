"""Prompt templates for each agent.

Keeping prompts in one place makes them easy to review, tune and test in
isolation from the orchestration logic.
"""
from __future__ import annotations

from app.schemas import PlanOutline, StudyPlanRequest

GRADE_TONE = (
    "Write at a reading level and complexity appropriate for the student's "
    "class/grade. Use age-appropriate language, concrete examples, and an "
    "encouraging tone."
)

Prompt = tuple[str, str]  # (system, user)


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


def _goals(outline: PlanOutline) -> str:
    return ", ".join(outline.learning_goals) or "n/a"


def planner_prompt(req: StudyPlanRequest) -> Prompt:
    system = (
        "You are the lead study-plan architect for school students. "
        "You design the overall plan and decide what each specialist agent "
        "(curriculum, scheduler, resources, assessment, quiz) should focus on. "
        + GRADE_TONE
    )
    user = (
        f"Create the high-level outline for this student:\n\n{request_summary(req)}\n\n"
        "Provide a title, a short overview, concrete learning goals, any "
        "prerequisites, and a short delegation note for each specialist agent."
    )
    return system, user


def curriculum_prompt(req: StudyPlanRequest, outline: PlanOutline) -> Prompt:
    system = (
        "You are a curriculum designer. Break the topic into a logical sequence "
        "of learning modules, each with clear objectives and subtopics. " + GRADE_TONE
    )
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Overall plan: {outline.title} — {outline.overview}\n"
        f"Learning goals: {_goals(outline)}\n\n"
        "Produce 3-6 modules that build on each other from foundations to mastery."
    )
    return system, user


def scheduler_prompt(req: StudyPlanRequest, outline: PlanOutline) -> Prompt:
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
    return system, user


def resources_prompt(req: StudyPlanRequest, outline: PlanOutline) -> Prompt:
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
    return system, user


def assessment_prompt(req: StudyPlanRequest, outline: PlanOutline) -> Prompt:
    system = (
        "You are an assessment designer. Create checkpoints, quizzes, practice "
        "sets and a small project so the student can measure progress. " + GRADE_TONE
    )
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Overall plan: {outline.title} — {outline.overview}\n\n"
        "Create 3-5 assessments with sample questions, increasing in difficulty."
    )
    return system, user


def quiz_prompt(req: StudyPlanRequest, outline: PlanOutline, references: str) -> Prompt:
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
        f"Learning goals: {_goals(outline)}\n"
        f"{reference_block}\n"
        "Create an ABUNDANT practice quiz covering the topic. For EVERY question "
        "type below, generate at least 15-20 questions (more is welcome):\n"
        "- short_questions: 15-20 short-answer questions, each with a concise answer.\n"
        "- mcqs: 15-20 multiple-choice questions, each with 4 options and exactly "
        "one correct answer (answer must match one option verbatim).\n"
        "- multi_select_mcqs: 15-20 multiple-correct questions (MMCQ), each with "
        "4-5 options and 2+ correct answers (answers must match options verbatim).\n"
        "- fill_in_the_blanks: 15-20 sentences each containing a '____' blank, "
        "with the answer.\n"
        "- true_false: 15-20 statements with a boolean answer.\n"
        "- case_studies: about 5 CBSE-style case/source-based questions. Each must "
        "have a short real-world 'scenario' (2-4 sentences) followed by 4-5 "
        "sub-questions (in 'questions'), each with its answer. Include these "
        "wherever the topic supports applied/real-world reasoning.\n"
        "- long_questions: 15-20 descriptive/long-answer questions with model answers.\n"
        "Spread questions across easy, medium and hard difficulty. Ensure variety "
        "and avoid duplicates."
    )
    return system, user


def compiler_prompt(
    req: StudyPlanRequest, outline: PlanOutline, module_titles: str
) -> Prompt:
    system = (
        "You are the lead study coach assembling the final plan. Provide a short "
        "list of practical, motivating study tips tailored to the student. "
        + GRADE_TONE
    )
    user = (
        f"Student request:\n{request_summary(req)}\n\n"
        f"Plan: {outline.title}. Modules: {module_titles}.\n\n"
        "Give 4-6 concise study tips (habits, focus techniques, how to use the "
        "resources and assessments effectively)."
    )
    return system, user
