"""Scraper Agent — fetches full page content via Celery tasks."""
from __future__ import annotations

from celery import group

from deep_agent.agents.base import BaseAgent
from deep_agent.config import get_settings
from deep_agent.models.schemas import ScrapedDocument
from deep_agent.state import ResearchState
from deep_agent.tasks.scraping import scrape_url


class ScraperAgent(BaseAgent):
    """Dispatches scraping to Celery and gathers the results.

    Scraping is parallelised through a Celery ``group``.  With
    ``CELERY_TASK_ALWAYS_EAGER`` the tasks run inline (no worker needed);
    otherwise they fan out to workers connected to the broker.
    """

    name = "scraper"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._settings = get_settings()

    def run(self, state: ResearchState) -> dict:
        targets = state.get("collected", [])
        if not targets:
            self.logger.warning("No URLs collected to scrape.")
            return {"scraped": [], "scraped_urls": []}

        timeout = self._settings.scrape_timeout_seconds
        self.logger.info("Dispatching %d scrape tasks", len(targets))

        job = group(
            scrape_url.s(result.url, timeout) for result in targets
        )
        async_result = job.apply_async()
        # ``disable_sync_subtasks`` avoids a warning when running eagerly.
        raw_docs = async_result.get(disable_sync_subtasks=False)

        docs = [ScrapedDocument.model_validate(d) for d in raw_docs]
        good = [d for d in docs if d.success and d.word_count > 0]
        self.logger.info(
            "Scraping complete: %d/%d succeeded", len(good), len(docs)
        )

        return {
            "scraped": good,
            "scraped_urls": [d.url for d in docs],
        }
