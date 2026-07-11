"""Search Agent — runs the pending queries through the search provider."""
from __future__ import annotations

from celery import group

from deep_agent.agents.base import BaseAgent
from deep_agent.config import get_settings
from deep_agent.models.schemas import SearchResult
from deep_agent.state import ResearchState
from deep_agent.tasks.search import search_query


class SearchAgent(BaseAgent):
    """Executes web searches for the current round's pending queries.

    Queries are fanned out as a Celery ``group`` so they run in parallel
    across workers (mirroring the scraper); under eager mode they run
    inline.  This agent does not use the LLM.
    """

    name = "search"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        settings = get_settings()
        self._provider = settings.search_provider.value
        self._max_results = settings.search_max_results

    def run(self, state: ResearchState) -> dict:
        queries = state.get("pending_queries", [])
        if not queries:
            self.logger.warning("No pending queries to search.")
            return {"latest_results": []}

        self.logger.info(
            "Dispatching %d parallel searches via %s", len(queries), self._provider
        )
        job = group(search_query.s(q, self._max_results) for q in queries)
        raw_batches = job.apply_async().get(disable_sync_subtasks=False)

        results = [
            SearchResult.model_validate(item)
            for batch in raw_batches
            for item in batch
        ]
        self.logger.info("Collected %d raw search hits", len(results))

        return {
            "latest_results": results,
            "all_results": results,
        }
