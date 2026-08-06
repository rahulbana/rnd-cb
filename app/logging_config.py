"""Application logging: date-wise log files for errors and exceptions.

Writes two rolling files per day into the ``logs/`` directory:

    logs/agent-YYYY-MM-DD.log    all INFO+ activity (tool calls, requests)
    logs/errors-YYYY-MM-DD.log   ERROR+ only (exceptions and failures)

The file name always carries the current date, and the handler switches to a
new file automatically at midnight, so logs are naturally partitioned by day.
Files older than ``LOG_RETENTION_DAYS`` are pruned on startup.
"""
from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import config

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class DailyFileHandler(logging.Handler):
    """A handler that writes to ``<prefix>-<YYYY-MM-DD>.log``, rolling at midnight."""

    def __init__(self, directory: Path, prefix: str) -> None:
        super().__init__()
        self.directory = Path(directory)
        self.prefix = prefix
        self._current_date: str | None = None
        self._stream = None

    def _ensure_stream(self) -> None:
        today = date.today().isoformat()
        # Reopen when the day rolls over, on first use, or if the stream was
        # closed out from under us (e.g. uvicorn's dictConfig closes existing
        # handlers on startup, and external log rotation can do the same).
        needs_open = (
            self._stream is None
            or getattr(self._stream, "closed", False)
            or today != self._current_date
        )
        if needs_open:
            if self._stream is not None and not getattr(self._stream, "closed", False):
                self._stream.close()
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"{self.prefix}-{today}.log"
            self._stream = open(path, "a", encoding="utf-8")
            self._current_date = today

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._ensure_stream()
            self._stream.write(self.format(record) + "\n")
            self._stream.flush()
        except Exception:  # never let logging crash the app
            self.handleError(record)

    def close(self) -> None:
        try:
            if self._stream is not None:
                self._stream.close()
        finally:
            super().close()


def _prune_old_logs(directory: Path, retention_days: int) -> None:
    """Delete log files older than the retention window (best-effort)."""
    if retention_days <= 0:
        return
    cutoff = datetime.now() - timedelta(days=retention_days)
    for f in directory.glob("*.log"):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
        except OSError:
            pass


_configured = False


def setup_logging() -> logging.Logger:
    """Configure the root application logger. Idempotent."""
    global _configured
    logger = logging.getLogger("agent")
    if _configured:
        return logger

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    _prune_old_logs(config.LOG_DIR, config.LOG_RETENTION_DAYS)

    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    logger.setLevel(logging.DEBUG)  # handlers decide what they keep
    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    # All activity at the configured level.
    all_handler = DailyFileHandler(config.LOG_DIR, "agent")
    all_handler.setLevel(level)
    all_handler.setFormatter(formatter)

    # Errors and exceptions only, in a dedicated file.
    err_handler = DailyFileHandler(config.LOG_DIR, "errors")
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(formatter)

    # Console (warnings and above) so problems are visible when run in a terminal.
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.WARNING)
    console.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(all_handler)
    logger.addHandler(err_handler)
    logger.addHandler(console)
    logger.propagate = False

    # Route uncaught exceptions to the log as well.
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _excepthook

    _configured = True
    logger.info("Logging initialized (level=%s, dir=%s)", config.LOG_LEVEL, config.LOG_DIR)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under the ``agent`` namespace."""
    return logging.getLogger("agent" if not name else f"agent.{name}")
