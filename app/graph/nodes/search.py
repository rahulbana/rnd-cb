"""Search node — fan out current queries across backends; dedup + score sources."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.budget import BudgetTracker
from app.graph.context import RuntimeContext
from app.graph.state import ResearchState
from app.models.schemas import JobStatus, ProgressEvent


async def search_node(state: ResearchState, config: RunnableConfig) -> dict:
    ctx = RuntimeContext.from_config(config)
    budget: BudgetTracker = state["budget"]
    queries: list[str] = state.get("current_queries", [])

    # One search cycle = one iteration for the purposes of the iteration cap.
    # (plan runs once at START; the reflection loop re-enters at `search`.)
    budget.start_iteration()

    # Respect the per-iteration search cap and taper as budget depletes.
    cap = ctx.settings.max_searches_per_iteration
    frac = budget.remaining_budget_fraction()
    effective_cap = max(1, int(round(cap * max(0.34, frac))))
    queries = queries[:effective_cap]

    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="search",
            message=f"Searching {len(queries)} queries across {len(ctx.aggregator.backends)} backends…",
            iteration=budget.iterations,
            status=JobStatus.running,
        )
    )

    sources = await ctx.aggregator.multi_search(
        queries, per_backend=ctx.settings.max_searches_per_iteration
    )
    # Each (query × backend) call is billed once.
    budget.record_searches(len(queries) * len(ctx.aggregator.backends))

    # Keep only the top-N most credible new sources to bound context growth.
    sources = sources[: ctx.settings.max_sources]

    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="search",
            message=f"Found {len(sources)} unique sources.",
            iteration=budget.iterations,
            sources_found=len(sources),
            usd_spent=budget.usd_spent,
        )
    )

    return {"sources": sources, "budget": budget}
