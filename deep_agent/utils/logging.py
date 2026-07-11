"""Centralised logging configuration.

Provides a single :func:`setup_logging` entry point (idempotent) and a
:func:`get_logger` helper.  Logs are emitted to both a colourised console
(via ``rich``) and a rotating file handler under ``LOG_DIR``.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

from deep_agent.config import get_settings

_CONFIGURED = False
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(force: bool = False) -> None:
    """Configure root logging handlers once per process.

    Args:
        force: Reconfigure even if logging was already set up.
    """

    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)
    # Clear existing handlers to avoid duplicate lines on reconfigure.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    # Console handler — rich, human friendly.
    console = RichHandler(
        rich_tracebacks=True,
        show_path=False,
        markup=False,
        log_time_format="%H:%M:%S",
    )
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(name)s | %(message)s"))
    root.addHandler(console)

    # File handler — full detail, rotated.
    file_handler = RotatingFileHandler(
        log_dir / "deep_agent.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(file_handler)

    # Quieten noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "urllib3", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger, ensuring logging is configured first."""

    if not _CONFIGURED:
        setup_logging()
    # Prefix so every module shares a discoverable namespace.
    logger_name = name if name.startswith("deep_agent") else f"deep_agent.{name}"
    return logging.getLogger(logger_name)
