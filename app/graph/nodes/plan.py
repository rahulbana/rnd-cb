"""Plan node — decompose the topic into sub-questions and initial search queries."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.budget import BudgetTracker
from app.graph.context import RuntimeContext
from app.graph.nodes._common import structured_call
from app.graph.nodes._schemas import ResearchPlan, SearchQueries
from app.graph.prompts import PLAN_HUMAN, PLAN_SYSTEM, QUERY_HUMAN, QUERY_SYSTEM
from app.graph.state import ResearchState
from app.models.schemas import JobStatus, ProgressEvent, ResearchRequest, SubQuestion


async def plan_node(state: ResearchState, config: RunnableConfig) -> dict:
    ctx = RuntimeContext.from_config(config)
    request: ResearchRequest = state["request"]
    budget: BudgetTracker = state["budget"]

    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="plan",
            message=f"Decomposing “{request.topic}” into research questions…",
            iteration=budget.iterations,
            status=JobStatus.running,
        )
    )

    plan = await structured_call(
        ctx,
        budget,
        schema=ResearchPlan,
        system=PLAN_SYSTEM,
        human=PLAN_HUMAN.format(
            topic=request.topic,
            audience=request.audience,
            focus_areas=", ".join(request.focus_areas) or "(none specified)",
        ),
        role="smart",
    )

    sub_questions = [
        SubQuestion(id=f"q{i+1}", question=pq.question, rationale=pq.rationale)
        for i, pq in enumerate(plan.sub_questions)
    ]

    questions_block = "\n".join(f"- {sq.question}" for sq in sub_questions)
    queries = await structured_call(
        ctx,
        budget,
        schema=SearchQueries,
        system=QUERY_SYSTEM,
        human=QUERY_HUMAN.format(topic=request.topic, questions=questions_block),
        role="fast",
    )

    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="plan",
            message=f"Planned {len(sub_questions)} sub-questions, {len(queries.queries)} queries.",
            iteration=budget.iterations,
            usd_spent=budget.usd_spent,
            data={"sub_questions": [sq.question for sq in sub_questions]},
        )
    )

    return {
        "sub_questions": sub_questions,
        "current_queries": queries.queries,
        "budget": budget,
        "iteration": budget.iterations,
    }
