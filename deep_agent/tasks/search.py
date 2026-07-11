"""Celery task for a single search query.

Running each query as an independent task lets the Search agent fan queries
out across Celery workers via a ``group`` (mirroring the scraper), instead
of issuing them sequentially.  Under ``CELERY_TASK_ALWAYS_EAGER`` the tasks
run inline.
"""
from __future__ import annotations

from deep_agent.search import get_search_client
from deep_agent.tasks.celery_app import celery_app
from deep_agent.utils.logging import get_logger

logger = get_logger("tasks.search")


@celery_app.task(name="deep_agent.search_query", bind=True)
def search_query(self, query: str, max_results: int | None = None) -> list[dict]:
    """Run one search query and return JSON-safe ``SearchResult`` dicts."""

    client = get_search_client()
    try:
        results = client.search(query, max_results)
    except Exception as exc:  # noqa: BLE001 - reported as empty result set
        logger.error("Search task failed for %r: %s", query, exc)
        return []
    return [r.model_dump(mode="json") for r in results]
