"""Synthesizer node: stream a cited report from the gathered sources."""
from __future__ import annotations

from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ...core.config import get_settings
from ...core.logging import get_logger
from ...observability.metrics import LLM_CALLS, LLM_TOKENS, observe_node
from ...providers.llm import get_llm_provider
from ...schemas.events import EventType
from ...schemas.source import Source
from ...services.event_bus import get_event_bus
from ..prompts import SYNTH_SYSTEM, synthesis_prompt
from ..state import AgentState
from ._utils import dedupe_sources

logger = get_logger(__name__)


async def synthesize(state: AgentState, config: RunnableConfig) -> Dict:
    settings = get_settings()
    bus = get_event_bus(config)
    query = state["query"]
    sources: List[Source] = state.get("sources", [])

    if bus:
        await bus.emit(
            EventType.NODE_START, node="synthesize", label="Synthesizing report",
            detail="Writing a cited answer from the collected sources.",
        )
        await bus.emit(
            EventType.TOOL_CALL, tool="llm", model=settings.openai_model,
            detail="Generating final report",
        )

    numbered = dedupe_sources(sources)
    prompt = synthesis_prompt(
        query, numbered, settings.report_target_words, settings.source_content_chars
    )

    llm = get_llm_provider(settings).chat_model(
        streaming=True, max_tokens=settings.report_max_tokens
    )

    report_parts: List[str] = []
    async with observe_node("synthesize"):
        LLM_CALLS.labels(model=settings.openai_model, kind="synthesize").inc()
        async for chunk in llm.astream(
            [SystemMessage(content=SYNTH_SYSTEM), HumanMessage(content=prompt)]
        ):
            token = chunk.content or ""
            if token:
                report_parts.append(token)
                LLM_TOKENS.labels(model=settings.openai_model).inc()
                if bus:
                    await bus.emit(EventType.TOKEN, text=token)

    report = "".join(report_parts)
    logger.info("Synthesized report (%d chars) from %d sources", len(report), len(numbered))

    if bus:
        await bus.emit(EventType.NODE_END, node="synthesize", detail="Report complete.")
        await bus.emit(
            EventType.REPORT, report=report,
            sources=[s.model_dump() for s in numbered],
        )

    return {"report": report, "sources": numbered}
