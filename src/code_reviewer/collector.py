"""Walk a directory and collect source files for a given language."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Set

from .config import Settings, extensions_for


@dataclass
class CodeFile:
    """A single source file ready to be reviewed."""

    path: str
    relpath: str
    content: str
    truncated: bool = False


def collect_files(settings: Settings) -> List[CodeFile]:
    """Return all matching source files under ``settings.path``.

    Accepts either a single file or a directory. Files larger than
    ``max_file_bytes`` are truncated (and flagged) so a single huge file
    cannot blow up the token budget.
    """
    root = os.path.abspath(settings.path)
    if not os.path.exists(root):
        raise FileNotFoundError(f"Path does not exist: {root}")

    exts = set(extensions_for(settings.language))
    exclude: Set[str] = settings.exclude_dirs

    collected: List[CodeFile] = []

    if os.path.isfile(root):
        candidate = _maybe_read(root, os.path.basename(root), exts, settings)
        if candidate:
            collected.append(candidate)
        return collected

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories in place so os.walk skips them.
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for filename in filenames:
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, root)
            candidate = _maybe_read(full, rel, exts, settings)
            if candidate:
                collected.append(candidate)

    collected.sort(key=lambda f: f.relpath)
    return collected


def _maybe_read(
    full: str, rel: str, exts: Set[str], settings: Settings
) -> CodeFile | None:
    _, ext = os.path.splitext(full)
    if ext.lower() not in exts:
        return None
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except (OSError, UnicodeError):
        return None

    truncated = False
    if len(content.encode("utf-8")) > settings.max_file_bytes:
        content = content[: settings.max_file_bytes]
        truncated = True

    return CodeFile(path=full, relpath=rel, content=content, truncated=truncated)
