"""Cross-platform helpers to open a file or reveal it in the OS file manager.

Used by the desktop app so the UI can offer "Open file" / "Open directory"
buttons for files that tools produce (e.g. saved research, resized images).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .logging_config import get_logger

logger = get_logger("desktop")


class OpenError(Exception):
    """The target exists but could not be opened (e.g. no opener command)."""


def _resolve(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _open_default(target: Path) -> None:
    """Open a file or folder with the OS default handler."""
    if sys.platform.startswith("win"):
        # os.startfile is the reliable way to open with the default app on Windows.
        import os
        os.startfile(str(target))  # noqa: S606 - trusted local path
    elif sys.platform == "darwin":
        subprocess.run(["open", str(target)], check=False)
    else:
        subprocess.run(["xdg-open", str(target)], check=False)


def _reveal_in_folder(target: Path) -> None:
    """Open the containing folder, selecting the file where the OS supports it."""
    if sys.platform.startswith("win"):
        # explorer returns a non-zero exit code even on success, so don't check.
        subprocess.run(["explorer", "/select,", str(target)], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", str(target)], check=False)
    else:
        # Most Linux file managers can't reliably select a file from the CLI;
        # opening the parent directory is the portable behavior.
        parent = target if target.is_dir() else target.parent
        subprocess.run(["xdg-open", str(parent)], check=False)


def open_target(path: str, reveal: bool = False) -> Path:
    """Open ``path`` (reveal=False) or reveal it in its folder (reveal=True).

    Returns the resolved path. Raises FileNotFoundError if it does not exist.
    """
    target = _resolve(path)
    if not target.exists():
        raise FileNotFoundError(str(target))
    try:
        if reveal:
            _reveal_in_folder(target)
        else:
            # Opening a directory path directly just opens the folder.
            _open_default(target)
    except FileNotFoundError as exc:
        # Raised when the OPENER command itself is missing (e.g. no xdg-open on
        # a headless Linux box). The target file/dir exists — this is different
        # from a missing path.
        raise OpenError(
            f"No file-opener command available on this system ({exc})."
        ) from exc
    except OSError as exc:
        raise OpenError(str(exc)) from exc
    logger.info("Opened %s (reveal=%s)", target, reveal)
    return target
