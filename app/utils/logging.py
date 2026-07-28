"""Logging setup for step-by-step pipeline visibility.

All agents log through the ``dataset_agent`` logger. By default that logger is
quiet (WARNING); calling :func:`configure_logging` with ``verbose=True`` routes
INFO-level step messages to stderr so a caller (typically the CLI's
``--verbose`` flag) can watch each stage as it runs.
"""

from __future__ import annotations

import logging
import sys

LOGGER_NAME = "dataset_agent"


def configure_logging(verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO if verbose else logging.WARNING)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False
    return logger
