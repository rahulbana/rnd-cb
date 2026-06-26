"""Centralised logging configuration.

Logs always go to the console; optionally they are also written to a rotating
log file (controlled via settings: LOG_TO_FILE / LOG_FILE / LOG_*).
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_CONFIGURED = False

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: str = "INFO",
    *,
    log_to_file: bool = False,
    log_file: str = "logs/app.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    resolved_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    root = logging.getLogger()
    root.setLevel(resolved_level)

    # Console handler.
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Optional rotating file handler.
    if log_to_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
        logging.getLogger(__name__).info("Logging to file: %s", path.resolve())

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name)
