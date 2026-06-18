"""The orchestrator that wires the pipeline stages together."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import Config
from .fetcher import fetch_recent_articles
from .summarizer import OpenAISummarizer
from .writer import save_brief

logger = logging.getLogger(__name__)


class CribasAgent:
    """End-to-end: fetch → summarise → write a UPSC current-affairs brief."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self._summarizer = OpenAISummarizer(self.config)

    def run(self) -> Path | None:
        """Execute one full cycle. Returns the saved file path, or ``None``."""
        self.config.validate()

        logger.info("Fetching news from the last %dh…", self.config.lookback_hours)
        articles = fetch_recent_articles(
            sources=self.config.sources,
            lookback_hours=self.config.lookback_hours,
            max_articles=self.config.max_articles,
            request_timeout=self.config.request_timeout,
            keep_undated=self.config.keep_undated,
        )
        if not articles:
            logger.warning("No articles found in the lookback window; nothing to do.")
            return None

        logger.info("Summarising %d articles with %s…", len(articles), self.config.model)
        brief = self._summarizer.summarize(articles)

        path = save_brief(brief, self.config.output_dir)
        logger.info("Done. Brief written to %s", path)
        return path
