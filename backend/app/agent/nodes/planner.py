"""Planner node: expand the user's question into multiple search queries."""
from __future__ import annotations

from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ...core.config import get_settings
from ...core.logging import get_logger
from ...observability.metrics import LLM_CALLS, observe_node
from ...providers.llm import get_llm_provider
from ...schemas.events import EventType
from ...services.event_bus import get_event_bus
from ..prompts import PLANNER_SYSTEM, planner_prompt
from ..state import AgentState
from ._utils import parse_query_list

logger = get_logger(__name__)


async def plan_queries(state: AgentState, config: RunnableConfig) -> Dict:
    settings = get_settings()
    bus = get_event_bus(config)
    query = state["query"]
    n = state.get("num_subqueries") or settings.num_subqueries

    if bus:
        await bus.emit(
            EventType.NODE_START,
            node="plan_queries",
            label="Planning search strategy",
            detail=f"Decomposing the question into {n} sub-queries with the LLM.",
        )
        await bus.emit(
            EventType.TOOL_CALL, tool="llm", model=settings.openai_model,
            detail="Generating sub-queries",
        )

    async with observe_node("plan_queries"):
        llm = get_llm_provider(settings).chat_model()
        LLM_CALLS.labels(model=settings.openai_model, kind="plan").inc()
        resp = await llm.ainvoke(
            [SystemMessage(content=PLANNER_SYSTEM),
             HumanMessage(content=planner_prompt(query, n))]
        )
        subqueries = parse_query_list(resp.content, fallback=query, n=n)
    logger.info("Planned %d sub-queries for query: %s", len(subqueries), query)

    if bus:
        await bus.emit(EventType.SUBQUERIES, subqueries=subqueries)
        await bus.emit(
            EventType.NODE_END, node="plan_queries",
            detail=f"Created {len(subqueries)} sub-queries.",
        )

    return {"subqueries": subqueries}
