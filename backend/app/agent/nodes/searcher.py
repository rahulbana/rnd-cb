"""Searcher node: run each sub-query through the web-search provider."""
from __future__ import annotations

from typing import Dict, List, Set

from langchain_core.runnables import RunnableConfig

from ...core.config import get_settings
from ...core.exceptions import SearchProviderError
from ...core.logging import get_logger
from ...observability.metrics import SEARCH_CALLS, SEARCH_RESULTS, observe_node
from ...providers.search import get_search_provider
from ...schemas.events import EventType
from ...schemas.source import Source
from ...services.event_bus import get_event_bus
from ..state import AgentState

logger = get_logger(__name__)


async def search(state: AgentState, config: RunnableConfig) -> Dict:
    settings = get_settings()
    bus = get_event_bus(config)
    provider = get_search_provider(settings)
    subqueries: List[str] = state["subqueries"]
    per_query = settings.results_per_query

    if bus:
        await bus.emit(
            EventType.NODE_START, node="search", label="Searching the web",
            detail=f"Running {len(subqueries)} searches via '{provider.name}'.",
        )

    all_sources: List[Source] = []
    seen_urls: Set[str] = set()

    async with observe_node("search"):
        for idx, sq in enumerate(subqueries):
            if bus:
                await bus.emit(
                    EventType.TOOL_CALL, tool=provider.name, query=sq,
                    index=idx, total=len(subqueries), detail=f'Searching: "{sq}"',
                )
            try:
                results = await provider.search(sq, per_query)
            except SearchProviderError as exc:
                SEARCH_CALLS.labels(provider=provider.name, status="error").inc()
                logger.warning("Search failed for '%s': %s", sq, exc)
                if bus:
                    await bus.emit(
                        EventType.TOOL_ERROR, tool=provider.name, query=sq, error=str(exc)
                    )
                continue

            SEARCH_CALLS.labels(provider=provider.name, status="ok").inc()
            SEARCH_RESULTS.labels(provider=provider.name).inc(len(results))
            if bus:
                await bus.emit(
                    EventType.TOOL_RESULT, tool=provider.name, query=sq,
                    count=len(results), detail=f'Found {len(results)} results for "{sq}".',
                )

            for r in results:
                source = Source(title=r.title or r.url, url=r.url, content=r.content, subquery=sq)
                all_sources.append(source)
                if source.url and source.url not in seen_urls:
                    seen_urls.add(source.url)
                    if bus:
                        await bus.emit(EventType.SOURCE, source=source.model_dump())

    logger.info("Collected %d sources (%d unique)", len(all_sources), len(seen_urls))
    if bus:
        await bus.emit(
            EventType.NODE_END, node="search",
            detail=f"Collected {len(all_sources)} sources ({len(seen_urls)} unique).",
        )

    return {"sources": all_sources}
