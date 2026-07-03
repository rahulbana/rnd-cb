"""File discovery: turn a file/directory path + language into review targets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

# Map of language name -> file extensions. Extending this dict is all that is
# needed to teach the collector about a new language.
LANGUAGE_EXTENSIONS: Dict[str, Set[str]] = {
    "python": {".py", ".pyi"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx"},
    "java": {".java"},
    "go": {".go"},
    "ruby": {".rb"},
    "php": {".php"},
    "c": {".c", ".h"},
    "cpp": {".cpp", ".cc", ".cxx", ".hpp", ".hh"},
    "csharp": {".cs"},
    "rust": {".rs"},
    "kotlin": {".kt", ".kts"},
    "swift": {".swift"},
    "scala": {".scala"},
    "shell": {".sh", ".bash"},
    "sql": {".sql"},
    "html": {".html", ".htm"},
    "css": {".css", ".scss", ".sass"},
    "yaml": {".yaml", ".yml"},
    "json": {".json"},
}

# Directories that are almost never worth reviewing.
DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
    "vendor",
}


@dataclass
class TargetFile:
    """A single file selected for review."""

    path: str
    language: str
    content: str


class CollectorError(Exception):
    """Raised when the input path is invalid or nothing can be reviewed."""


def normalize_language(language: str) -> str:
    """Normalise a user-supplied language name (aliases -> canonical)."""

    lang = language.strip().lower()
    aliases = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "c++": "cpp",
        "cxx": "cpp",
        "c#": "csharp",
        "cs": "csharp",
        "golang": "go",
        "rb": "ruby",
        "rs": "rust",
        "kt": "kotlin",
        "sh": "shell",
        "bash": "shell",
        "yml": "yaml",
    }
    return aliases.get(lang, lang)


def extensions_for(language: str) -> Set[str]:
    """Return the known extensions for *language* (empty if unknown)."""

    return LANGUAGE_EXTENSIONS.get(normalize_language(language), set())


def _read_text(path: str, max_bytes: int) -> Optional[str]:
    """Read *path* as UTF-8 text, returning ``None`` for binary/oversized files."""

    try:
        if os.path.getsize(path) > max_bytes:
            return None
    except OSError:
        return None

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except (UnicodeDecodeError, OSError):
        return None


def collect(
    path: str,
    language: str,
    *,
    max_file_bytes: int = 200_000,
    ignore_dirs: Optional[Iterable[str]] = None,
) -> List[TargetFile]:
    """Collect review targets from *path*.

    * If *path* is a file, it is reviewed regardless of extension (the caller
      explicitly named it) but skipped if it is binary/oversized.
    * If *path* is a directory, every file whose extension matches *language*
      is collected recursively, skipping ignored directories.
    """

    canonical_lang = normalize_language(language)
    exts = extensions_for(canonical_lang)
    ignore = set(DEFAULT_IGNORE_DIRS)
    if ignore_dirs:
        ignore.update(ignore_dirs)

    if not os.path.exists(path):
        raise CollectorError(f"Path does not exist: {path}")

    targets: List[TargetFile] = []

    if os.path.isfile(path):
        content = _read_text(path, max_file_bytes)
        if content is None:
            raise CollectorError(
                f"Cannot review '{path}': file is binary, unreadable, or larger "
                f"than {max_file_bytes} bytes."
            )
        targets.append(TargetFile(path=path, language=canonical_lang, content=content))
        return targets

    # Directory walk.
    for root, dirs, files in os.walk(path):
        # Prune ignored directories in-place for efficiency.
        dirs[:] = [d for d in dirs if d not in ignore]
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            # When the language is unknown to us, fall back to reviewing every
            # readable text file so the tool still works for niche languages.
            if exts and ext not in exts:
                continue
            full = os.path.join(root, name)
            content = _read_text(full, max_file_bytes)
            if content is None or not content.strip():
                continue
            targets.append(
                TargetFile(path=full, language=canonical_lang, content=content)
            )

    if not targets:
        hint = (
            f" No files with extensions {sorted(exts)} were found."
            if exts
            else " No readable text files were found."
        )
        raise CollectorError(f"Nothing to review under '{path}'.{hint}")

    return targets
