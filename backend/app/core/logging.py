"""Application logging configuration.

We configure a dedicated ``app`` logger (rather than the root logger) so we do
not interfere with uvicorn's own handlers. Module loggers obtained via
``get_logger(__name__)`` are children of ``app`` and inherit its handler.
"""
from __future__ import annotations

import logging
import sys

_LOGGER_NAME = "app"
_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str = "INFO") -> None:
    """Attach a stdout handler to the ``app`` logger (idempotent)."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level.upper())
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
        logger.addHandler(handler)
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a child logger of the ``app`` logger."""
    if name == _LOGGER_NAME or name.startswith(_LOGGER_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_LOGGER_NAME}.{name}")
