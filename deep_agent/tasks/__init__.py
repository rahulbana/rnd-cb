"""Celery application and distributed tasks."""

from deep_agent.tasks.celery_app import celery_app
from deep_agent.tasks.scraping import scrape_url
from deep_agent.tasks.search import search_query

__all__ = ["celery_app", "scrape_url", "search_query"]
