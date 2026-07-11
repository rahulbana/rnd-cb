"""LangGraph assembly and the top-level research runner.

Wires the seven agents into a stateful graph with an adaptive research
loop driven by the Reflection agent:

    planner → search → collector → scraper → reflection ─┐
                 ▲                                        │ (needs more)
                 └────────────────────────────────────────┘
                                     │ (sufficient)
                                     ▼
                             fact_checker → writer → END
"""
from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from deep_agent.agents import (
    CollectorAgent,
    FactCheckerAgent,
    PlannerAgent,
    ReflectionAgent,
    ScraperAgent,
    SearchAgent,
    WriterAgent,
)
from deep_agent.checkpoint import get_checkpointer
from deep_agent.config import get_settings
from deep_agent.models.schemas import ReportStatus, ResearchReport
from deep_agent.observability import flush_langfuse, get_langfuse_handler
from deep_agent.state import ResearchState
from deep_agent.utils.logging import get_logger

logger = get_logger("graph")


def _has_queries(state: ResearchState) -> bool:
    plan = state.get("plan")
    return bool(plan and plan.all_queries())


def _route_after_planner(state: ResearchState) -> str:
    """Abort early when the planner produced nothing searchable."""

    if not _has_queries(state):
        return "no_results"
    return "search"


def _route_after_reflection(state: ResearchState) -> str:
    """Loop for more research, abort if empty-handed, else write the report."""

    reflection = state.get("reflection")
    if reflection is not None and not reflection.is_sufficient:
        return "search"
    # Evidence is deemed sufficient (or the loop hit its ceiling). If nothing
    # was scraped, short-circuit instead of writing an empty report.
    if not state.get("scraped"):
        return "no_results"
    return "fact_checker"


def _no_results_node(state: ResearchState) -> dict:
    """Terminal node that emits a clear 'no report' message.

    Reached when the planner yields no queries or no source content could be
    retrieved, so the pipeline stops instead of producing an empty report.
    """

    topic = state.get("topic", "Unknown topic")
    if not _has_queries(state):
        reason = "the planner did not produce any searchable queries"
        hint = "Try rephrasing the topic to be more concrete and specific."
    else:
        reason = "no source content could be retrieved from web search/scraping"
        hint = (
            "Check your search provider API key and network access, or broaden "
            "the topic so it surfaces more sources."
        )

    logger.warning("No report generated: %s", reason)
    markdown = (
        f"# {topic}\n\n"
        "> **No report generated.**\n\n"
        f"Research stopped because {reason}.\n\n"
        f"_{hint}_\n"
    )
    return {
        "report": ResearchReport(
            topic=topic, markdown=markdown, status=ReportStatus.NO_RESULTS
        )
    }


def build_graph():
    """Construct and compile the research graph."""

    planner = PlannerAgent()
    search = SearchAgent()
    collector = CollectorAgent()
    scraper = ScraperAgent()
    reflection = ReflectionAgent()
    fact_checker = FactCheckerAgent()
    writer = WriterAgent()

    graph = StateGraph(ResearchState)
    graph.add_node("planner", planner.run)
    graph.add_node("search", search.run)
    graph.add_node("collector", collector.run)
    graph.add_node("scraper", scraper.run)
    graph.add_node("reflection", reflection.run)
    graph.add_node("fact_checker", fact_checker.run)
    graph.add_node("writer", writer.run)
    graph.add_node("no_results", _no_results_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"search": "search", "no_results": "no_results"},
    )
    graph.add_edge("search", "collector")
    graph.add_edge("collector", "scraper")
    graph.add_edge("scraper", "reflection")
    graph.add_conditional_edges(
        "reflection",
        _route_after_reflection,
        {
            "search": "search",
            "fact_checker": "fact_checker",
            "no_results": "no_results",
        },
    )
    graph.add_edge("fact_checker", "writer")
    graph.add_edge("writer", END)
    graph.add_edge("no_results", END)

    checkpointer = get_checkpointer()
    logger.info("Research graph compiled (checkpointer=%s).", type(checkpointer).__name__ if checkpointer else "none")
    return graph.compile(checkpointer=checkpointer)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "report"


def save_report(report: ResearchReport, output_dir: str | None = None) -> Path:
    """Persist a report to ``output_dir`` as a markdown file."""

    out_dir = Path(output_dir or get_settings().output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"{_slugify(report.topic)}-{stamp}.md"
    path.write_text(report.markdown, encoding="utf-8")
    logger.info("Report saved to %s", path)
    return path


def run_research(
    topic: str,
    max_iterations: int | None = None,
    thread_id: str | None = None,
    stream: bool | None = None,
    on_node: Callable[[str], None] | None = None,
) -> ResearchReport:
    """Run the full research pipeline for ``topic`` and return the report.

    Args:
        topic: The research topic.
        max_iterations: Overrides the configured research-loop ceiling.
        thread_id: Checkpoint thread id. Defaults to a slug of the topic so
            re-running the same topic resumes/reuses the saved state when a
            persistent checkpoint backend is configured.
        stream: If True, drive the graph with ``stream`` and invoke ``on_node``
            as each node completes; if False, use a single silent ``invoke``.
            Defaults to the ``STREAM_PROGRESS`` setting.
        on_node: Callback receiving the name of each node as it completes
            (only used when ``stream`` is True).
    """

    settings = get_settings()
    max_iter = max_iterations or settings.max_research_iterations
    thread = thread_id or _slugify(topic)
    use_stream = settings.stream_progress if stream is None else stream
    logger.info(
        "Starting research: topic=%r max_iterations=%d thread=%s stream=%s",
        topic,
        max_iter,
        thread,
        use_stream,
    )

    app = build_graph()
    initial: ResearchState = {"topic": topic, "max_iterations": max_iter}
    # thread_id groups checkpointed state; recursion_limit allows several loops.
    config: dict = {"recursion_limit": 50, "configurable": {"thread_id": thread}}

    # Attach Langfuse tracing when enabled; LangChain propagates the callback
    # to the LLM calls inside each agent automatically.
    handler = get_langfuse_handler()
    if handler is not None:
        config["callbacks"] = [handler]
        config["run_name"] = f"deep-research: {topic}"
        config["metadata"] = {
            "langfuse_session_id": thread,
            "langfuse_tags": ["deep-agent"],
            "topic": topic,
            "max_iterations": max_iter,
        }

    try:
        if use_stream:
            report: ResearchReport | None = None
            for chunk in app.stream(initial, config=config, stream_mode="updates"):
                for node, update in chunk.items():
                    if on_node is not None:
                        on_node(node)
                    if isinstance(update, dict) and update.get("report") is not None:
                        report = update["report"]
            if report is None:
                # Fall back to the persisted final state if we missed the update.
                report = app.get_state(config).values.get("report")
        else:
            final_state = app.invoke(initial, config=config)
            report = final_state.get("report")
    finally:
        # Ensure buffered traces are sent before the CLI process exits.
        flush_langfuse()

    if report is None:  # pragma: no cover - defensive
        raise RuntimeError("Pipeline finished without producing a report.")
    return report
