"""Collect the source files to generate tests for."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from .languages import SUPPORTED_EXTENSIONS

# Directories we never want to walk into when scanning a project.
DEFAULT_IGNORES = {
    ".git", ".hg", ".svn",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "dist", "build", "target", "vendor",
    ".venv", "venv", "env", ".env",
    ".idea", ".vscode", ".tox", ".next", "coverage",
}

# Files that live next to source but aren't worth testing directly.
_SKIP_FILENAMES = {"__init__.py", "setup.py", "conftest.py"}


def _looks_like_test(path: Path) -> bool:
    stem = path.stem.lower()
    return (
        stem.startswith("test_")
        or stem.endswith("_test")
        or stem.endswith(".test")
        or stem.endswith("_spec")
        or stem.endswith(".spec")
        or "test" in path.parts  # inside a tests/ directory
        or "tests" in path.parts
    )


def collect(
    root: Path,
    *,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[Path]:
    """Return the source files under ``root`` eligible for test generation.

    ``root`` may be a single file or a directory. ``include``/``exclude`` are
    glob patterns matched against each file's path.
    """
    root = root.expanduser().resolve()
    if root.is_file():
        return [root] if _is_source(root) else []

    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in DEFAULT_IGNORES for part in path.parts):
            continue
        if not _is_source(path):
            continue
        if _looks_like_test(path):
            continue
        rel = path.relative_to(root).as_posix()
        if include and not any(fnmatch.fnmatch(rel, pat) for pat in include):
            continue
        if exclude and any(fnmatch.fnmatch(rel, pat) for pat in exclude):
            continue
        files.append(path)
    return files


def _is_source(path: Path) -> bool:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False
    if path.name in _SKIP_FILENAMES:
        return False
    return True
