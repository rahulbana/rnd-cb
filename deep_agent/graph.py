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
from deep_agent.config import get_settings
from deep_agent.models.schemas import ResearchReport
from deep_agent.state import ResearchState
from deep_agent.utils.logging import get_logger

logger = get_logger("graph")


def _route_after_reflection(state: ResearchState) -> str:
    """Loop back to search when more research is needed, else finish."""

    reflection = state.get("reflection")
    if reflection is not None and not reflection.is_sufficient:
        return "search"
    return "fact_checker"


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

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "search")
    graph.add_edge("search", "collector")
    graph.add_edge("collector", "scraper")
    graph.add_edge("scraper", "reflection")
    graph.add_conditional_edges(
        "reflection",
        _route_after_reflection,
        {"search": "search", "fact_checker": "fact_checker"},
    )
    graph.add_edge("fact_checker", "writer")
    graph.add_edge("writer", END)

    logger.info("Research graph compiled.")
    return graph.compile()


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


def run_research(topic: str, max_iterations: int | None = None) -> ResearchReport:
    """Run the full research pipeline for ``topic`` and return the report."""

    settings = get_settings()
    max_iter = max_iterations or settings.max_research_iterations
    logger.info("Starting research: topic=%r max_iterations=%d", topic, max_iter)

    app = build_graph()
    initial: ResearchState = {"topic": topic, "max_iterations": max_iter}
    # Allow enough supersteps for several research loops.
    final_state = app.invoke(initial, config={"recursion_limit": 50})

    report = final_state.get("report")
    if report is None:  # pragma: no cover - defensive
        raise RuntimeError("Pipeline finished without producing a report.")
    return report
