"""Common agent scaffolding.

Every agent is a small, single-responsibility unit with a ``run`` method. They
are deliberately plain Python objects rather than framework-bound classes so the
pipeline runs without a live LLM or an event loop. An LLM-backed planner plugs
in behind the same interface (see :mod:`app.agents.planner`).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("dataset_agent")


class Agent(ABC):
    """Base class for all pipeline agents."""

    name: str = "agent"

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface
        ...

    def log(self, message: str) -> None:
        logger.info("[%s] %s", self.name, message)
