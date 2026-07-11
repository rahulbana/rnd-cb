"""Celery application and distributed tasks."""

from deep_agent.tasks.celery_app import celery_app
from deep_agent.tasks.scraping import scrape_url

__all__ = ["celery_app", "scrape_url"]
