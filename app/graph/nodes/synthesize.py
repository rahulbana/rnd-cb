"""Synthesize node — produce the final validated `ResearchReport`.

The LLM writes into a permissive `ReportDraft`; `normalize_citations` (in
`app.graph.citations`) then repairs the citation graph deterministically so
every inline [n] points at a source we actually retrieved. See that module for
the guarantees.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.budget import BudgetTracker
from app.graph.citations import ReportDraft, normalize_citations
from app.graph.context import RuntimeContext
from app.graph.nodes._common import structured_call
from app.graph.prompts import SYNTH_HUMAN, SYNTH_SYSTEM
from app.graph.state import ResearchState
from app.models.schemas import JobStatus, ProgressEvent, ResearchRequest, Source, SubQuestion


def _sources_block(sources: list[Source], limit: int = 30) -> str:
    top = sorted(sources, key=lambda s: s.credibility, reverse=True)[:limit]
    lines = []
    for s in top:
        text = (s.content or s.snippet)[:600]
        lines.append(f"[id={s.id} · cred={s.credibility:.2f}] {s.title} · {s.url}\n{text}")
    return "\n\n".join(lines) or "(no sources)"


async def synthesize_node(state: ResearchState, config: RunnableConfig) -> dict:
    ctx = RuntimeContext.from_config(config)
    budget: BudgetTracker = state["budget"]
    request: ResearchRequest = state["request"]
    sub_questions: list[SubQuestion] = state.get("sub_questions", [])
    sources: list[Source] = state.get("sources", [])

    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="synthesize",
            message="Writing the analyst report…",
            iteration=budget.iterations,
            status=JobStatus.running,
        )
    )

    questions_block = "\n".join(f"- {sq.question}" for sq in sub_questions)
    draft = await structured_call(
        ctx,
        budget,
        schema=ReportDraft,
        system=SYNTH_SYSTEM,
        human=SYNTH_HUMAN.format(
            topic=request.topic,
            audience=request.audience,
            questions=questions_block,
            sources=_sources_block(sources),
        ),
        role="smart",
    )

    report = normalize_citations(draft, sources, topic=request.topic)
    if state.get("gaps"):
        # surface unresolved gaps that synthesis didn't already capture
        existing = set(report.open_questions)
        report.open_questions.extend(g for g in state["gaps"] if g not in existing)

    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="synthesize",
            message=f"Report complete: {len(report.sections)} sections, {len(report.citations)} citations.",
            iteration=budget.iterations,
            sources_found=len(sources),
            usd_spent=budget.usd_spent,
            status=JobStatus.completed,
        )
    )

    return {"report": report, "budget": budget}
