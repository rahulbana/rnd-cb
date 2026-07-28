"""Reflect node — assess evidence sufficiency, identify gaps, and re-plan queries.

This is what makes the loop agentic rather than a one-shot pipeline. The node:
  1. Summarizes current evidence per sub-question.
  2. Asks the LLM whether coverage is sufficient and, if not, what's missing.
  3. If gaps remain AND budget allows, generates targeted queries for the gaps
     and routes back to search. Otherwise routes to synthesis.

The routing decision (`route_after_reflect`) is a pure function of state, so it
is deterministic and replayable from a checkpoint.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.budget import BudgetTracker
from app.graph.context import RuntimeContext
from app.graph.nodes._common import structured_call
from app.graph.nodes._schemas import GapAssessment, SearchQueries
from app.graph.prompts import REFLECT_HUMAN, REFLECT_SYSTEM, REPLAN_HUMAN, REPLAN_SYSTEM
from app.graph.state import ResearchState
from app.models.schemas import JobStatus, ProgressEvent, ResearchRequest, Source, SubQuestion


def _evidence_summary(sources: list[Source], limit: int = 25) -> str:
    top = sorted(sources, key=lambda s: s.credibility, reverse=True)[:limit]
    lines = []
    for s in top:
        mark = "✓read" if s.read else "snippet"
        lines.append(f"- [{s.credibility:.2f} {mark}] {s.title} ({s.domain}) — {s.snippet[:160]}")
    return "\n".join(lines) or "(no sources yet)"


async def reflect_node(state: ResearchState, config: RunnableConfig) -> dict:
    ctx = RuntimeContext.from_config(config)
    budget: BudgetTracker = state["budget"]
    request: ResearchRequest = state["request"]
    sub_questions: list[SubQuestion] = state.get("sub_questions", [])
    sources: list[Source] = state.get("sources", [])

    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="reflect",
            message="Assessing evidence and hunting for gaps…",
            iteration=budget.iterations,
            status=JobStatus.running,
        )
    )

    questions_block = "\n".join(f"- {sq.question}" for sq in sub_questions)
    assessment = await structured_call(
        ctx,
        budget,
        schema=GapAssessment,
        system=REFLECT_SYSTEM,
        human=REFLECT_HUMAN.format(
            topic=request.topic,
            questions=questions_block,
            evidence=_evidence_summary(sources),
        ),
        role="smart",
    )

    gaps = [] if assessment.sufficient else assessment.gaps

    # Decide whether another iteration is even possible before spending on re-plan.
    will_continue = bool(gaps) and not budget.should_stop()

    next_queries: list[str] = state.get("current_queries", [])
    if will_continue:
        gaps_block = "\n".join(f"- {g}" for g in gaps)
        replan = await structured_call(
            ctx,
            budget,
            schema=SearchQueries,
            system=REPLAN_SYSTEM.format(max_queries=ctx.settings.max_searches_per_iteration),
            human=REPLAN_HUMAN.format(
                topic=request.topic, questions=questions_block, gaps=gaps_block
            ),
            role="fast",
        )
        next_queries = replan.queries

    stop_reason = budget.stop_reason() if budget.should_stop() else None
    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="reflect",
            message=(
                f"{len(gaps)} gap(s) found; continuing." if will_continue
                else "Coverage sufficient — moving to synthesis."
                if not gaps else f"Gaps remain but stopping: {stop_reason}"
            ),
            iteration=budget.iterations,
            sources_found=len(sources),
            usd_spent=budget.usd_spent,
            data={"gaps": gaps},
        )
    )

    return {
        "gaps": gaps,
        "current_queries": next_queries,
        "budget": budget,
        "stop_reason": stop_reason,
    }


def route_after_reflect(state: ResearchState) -> str:
    """Deterministic router: 'search' to iterate again, or 'synthesize' to finish."""
    budget: BudgetTracker = state["budget"]
    gaps = state.get("gaps", [])
    if gaps and not budget.should_stop():
        return "search"
    return "synthesize"
