"""Search Agent — runs the pending queries through the search provider."""
from __future__ import annotations

from deep_agent.agents.base import BaseAgent
from deep_agent.search import get_search_client
from deep_agent.state import ResearchState


class SearchAgent(BaseAgent):
    """Executes web searches for the current round's pending queries.

    This agent does not use the LLM; it bridges the plan/reflection queries
    to the configured (switchable) search provider.
    """

    name = "search"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.client = get_search_client()

    def run(self, state: ResearchState) -> dict:
        queries = state.get("pending_queries", [])
        if not queries:
            self.logger.warning("No pending queries to search.")
            return {"latest_results": []}

        self.logger.info(
            "Searching %d queries via %s", len(queries), self.client.name
        )
        results = self.client.batch_search(queries)
        self.logger.info("Collected %d raw search hits", len(results))

        return {
            "latest_results": results,
            "all_results": results,
        }
