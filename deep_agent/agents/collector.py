"""Collector Agent — deduplicates and ranks search hits into a scrape list."""
from __future__ import annotations

from deep_agent.agents.base import BaseAgent
from deep_agent.config import get_settings
from deep_agent.models.schemas import SearchResult
from deep_agent.state import ResearchState


class CollectorAgent(BaseAgent):
    """Selects the most promising, not-yet-seen URLs to scrape.

    Deterministic and LLM-free: it dedups by URL, drops already-scraped
    sources and keeps the highest-scoring hits within a per-round budget.
    """

    name = "collector"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Reuse the scrape concurrency as the per-round collection budget.
        self._budget = get_settings().scrape_max_concurrency * 2

    def run(self, state: ResearchState) -> dict:
        latest = state.get("latest_results", [])
        seen_urls = set(state.get("scraped_urls", []))

        unique: dict[str, SearchResult] = {}
        for result in latest:
            if not result.url or result.url in seen_urls:
                continue
            existing = unique.get(result.url)
            # Keep the higher-scored duplicate.
            if existing is None or (result.score or 0) > (existing.score or 0):
                unique[result.url] = result

        ranked = sorted(
            unique.values(), key=lambda r: r.score or 0.0, reverse=True
        )[: self._budget]

        self.logger.info(
            "Collected %d unique new URLs (from %d hits, budget %d)",
            len(ranked),
            len(latest),
            self._budget,
        )
        return {"collected": ranked}
