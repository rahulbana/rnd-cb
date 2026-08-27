"""Graph nodes for the deep-research agent.

Each node is an async function that receives the current state and returns a
partial state update (LangGraph merges it via the state reducers). Nodes are
deliberately small and single-purpose for testability and observability.
"""
from __future__ import annotations

import logging

from app.agent.llm import get_synthesis_llm, get_worker_llm
from app.agent.prompts import (
    EXTRACT_HUMAN,
    EXTRACT_SYSTEM,
    PLANNER_HUMAN,
    PLANNER_SYSTEM,
    REFLECT_HUMAN,
    REFLECT_SYSTEM,
    SYNTHESIS_HUMAN,
    SYNTHESIS_SYSTEM,
)
from app.agent.state import Reflection, ResearchPlan, ResearchState
from app.tools.search import batch_search

logger = logging.getLogger(__name__)

# Bound the text handed to the LLM per source to control token cost/latency.
_MAX_CONTENT_CHARS = 1500


async def plan_node(state: ResearchState) -> ResearchState:
    """Decompose the topic into sub-questions and initial search queries."""
    topic = state["topic"]
    llm = get_worker_llm().with_structured_output(ResearchPlan)
    plan: ResearchPlan = await llm.ainvoke(
        [
            ("system", PLANNER_SYSTEM),
            ("human", PLANNER_HUMAN.format(topic=topic)),
        ]
    )
    max_q = state.get("max_queries_per_iteration", 4)
    queries = (plan.initial_queries or plan.sub_questions)[:max_q]
    logger.info(
        "planned research",
        extra={"topic": topic, "sub_questions": len(plan.sub_questions), "queries": len(queries)},
    )
    return {
        "plan": plan.sub_questions,
        "pending_queries": queries,
        "iteration": 0,
        "is_complete": False,
    }


def _format_results_block(results_by_query: dict) -> tuple[str, list[dict]]:
    """Render search results for the extractor prompt and collect source records."""
    lines: list[str] = []
    sources: list[dict] = []
    for query, results in results_by_query.items():
        if not results:
            continue
        lines.append(f"## Results for: {query}")
        for r in results:
            content = (r.content or "")[:_MAX_CONTENT_CHARS]
            lines.append(f"- Title: {r.title}\n  URL: {r.url}\n  Excerpt: {content}")
            sources.append({"title": r.title, "url": r.url, "provider": r.provider})
    return "\n".join(lines) if lines else "(no results)", sources


async def search_node(state: ResearchState) -> ResearchState:
    """Execute pending queries, then extract cited findings from the results."""
    topic = state["topic"]
    queries = state.get("pending_queries", [])
    if not queries:
        return {"executed_queries": [], "findings": [], "sources": []}

    results_by_query = await batch_search(queries)
    results_block, sources = _format_results_block(results_by_query)

    findings: list[str] = []
    if sources:  # only call the LLM if we actually retrieved something
        llm = get_worker_llm()
        response = await llm.ainvoke(
            [
                ("system", EXTRACT_SYSTEM),
                ("human", EXTRACT_HUMAN.format(topic=topic, results_block=results_block)),
            ]
        )
        text = (response.content or "").strip() if hasattr(response, "content") else str(response)
        findings = [ln.strip("-• ").strip() for ln in text.splitlines() if ln.strip("-• ").strip()]

    logger.info(
        "search iteration complete",
        extra={
            "queries": len(queries),
            "sources_found": len(sources),
            "findings_extracted": len(findings),
        },
    )
    return {
        "executed_queries": queries,
        "findings": findings,
        "sources": sources,
        "pending_queries": [],
    }


async def reflect_node(state: ResearchState) -> ResearchState:
    """Decide whether to continue researching or move to synthesis."""
    iteration = state.get("iteration", 0) + 1
    max_iter = state.get("max_iterations", 4)
    findings = state.get("findings", [])

    # Hard stop on budget regardless of the model's opinion.
    if iteration >= max_iter:
        logger.info("iteration budget reached, forcing completion", extra={"iteration": iteration})
        return {"iteration": iteration, "is_complete": True, "knowledge_gaps": [], "pending_queries": []}

    plan = state.get("plan", [])
    llm = get_worker_llm().with_structured_output(Reflection)
    reflection: Reflection = await llm.ainvoke(
        [
            ("system", REFLECT_SYSTEM),
            (
                "human",
                REFLECT_HUMAN.format(
                    topic=state["topic"],
                    plan_block="\n".join(f"- {q}" for q in plan) or "(none)",
                    finding_count=len(findings),
                    findings_block="\n".join(f"- {f}" for f in findings[:60]) or "(none yet)",
                ),
            ),
        ]
    )

    max_q = state.get("max_queries_per_iteration", 4)
    follow_ups = [] if reflection.is_sufficient else reflection.follow_up_queries[:max_q]
    complete = reflection.is_sufficient or not follow_ups

    logger.info(
        "reflection complete",
        extra={
            "iteration": iteration,
            "is_sufficient": reflection.is_sufficient,
            "gaps": len(reflection.knowledge_gaps),
            "follow_ups": len(follow_ups),
        },
    )
    return {
        "iteration": iteration,
        "is_complete": complete,
        "knowledge_gaps": reflection.knowledge_gaps,
        "pending_queries": follow_ups,
    }


async def synthesize_node(state: ResearchState) -> ResearchState:
    """Write the final Markdown report grounded in findings and numbered sources."""
    topic = state["topic"]
    findings = state.get("findings", [])
    sources = state.get("sources", [])

    sources_block = "\n".join(
        f"[{i}] {s.get('title') or s.get('url')} — {s.get('url')}"
        for i, s in enumerate(sources, start=1)
    ) or "(no sources)"
    findings_block = "\n".join(f"- {f}" for f in findings) or "(no findings)"

    llm = get_synthesis_llm()
    response = await llm.ainvoke(
        [
            ("system", SYNTHESIS_SYSTEM),
            (
                "human",
                SYNTHESIS_HUMAN.format(
                    topic=topic, findings_block=findings_block, sources_block=sources_block
                ),
            ),
        ]
    )
    report = response.content if hasattr(response, "content") else str(response)
    logger.info("synthesis complete", extra={"report_chars": len(report), "sources": len(sources)})
    return {"final_report": report, "is_complete": True}


def route_after_reflect(state: ResearchState) -> str:
    """Conditional edge: loop back to search, or finish."""
    if state.get("is_complete") or not state.get("pending_queries"):
        return "synthesize"
    return "search"
