"""Run the agent once a day at a fixed local time (default 10:00).

Kept deliberately thin: for production you may prefer an OS-level cron or a
container scheduler, but this lets the agent run as a standalone long-lived
process with no extra infrastructure.
"""

from __future__ import annotations

import logging
import time

import schedule

from .agent import CribasAgent
from .config import Config

logger = logging.getLogger(__name__)


def start(config: Config | None = None) -> None:
    """Block forever, triggering :meth:`CribasAgent.run` every day at ``run_at``."""
    config = config or Config()
    agent = CribasAgent(config)

    def _job() -> None:
        try:
            agent.run()
        except Exception:  # pragma: no cover - keep the daemon alive
            logger.exception("Scheduled run failed; will retry tomorrow.")

    schedule.every().day.at(config.run_at).do(_job)
    logger.info("Scheduler started — running daily at %s (local time).", config.run_at)

    while True:
        schedule.run_pending()
        time.sleep(30)
