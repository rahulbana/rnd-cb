"""Configuration: language definitions and run-time settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# Map a user-facing language name to the file extensions we should collect.
# Keys are normalised to lowercase.
LANGUAGE_EXTENSIONS: Dict[str, List[str]] = {
    "python": [".py"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "go": [".go"],
    "ruby": [".rb"],
    "php": [".php"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hh"],
    "csharp": [".cs"],
    "rust": [".rs"],
    "kotlin": [".kt", ".kts"],
    "swift": [".swift"],
    "scala": [".scala"],
}

# Common aliases the user might type.
LANGUAGE_ALIASES: Dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "node": "javascript",
    "ts": "typescript",
    "golang": "go",
    "c++": "cpp",
    "cplusplus": "cpp",
    "c#": "csharp",
    "cs": "csharp",
    "rs": "rust",
    "kt": "kotlin",
}

# Directories we never want to walk into.
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "vendor",
}


def normalize_language(language: str) -> str:
    """Resolve aliases and casing to a canonical language key."""
    key = language.strip().lower()
    key = LANGUAGE_ALIASES.get(key, key)
    return key


def extensions_for(language: str) -> List[str]:
    """Return file extensions for a language, raising if unsupported."""
    key = normalize_language(language)
    if key not in LANGUAGE_EXTENSIONS:
        supported = ", ".join(sorted(LANGUAGE_EXTENSIONS))
        raise ValueError(
            f"Unsupported language '{language}'. Supported: {supported}"
        )
    return LANGUAGE_EXTENSIONS[key]


@dataclass
class Settings:
    """Run-time settings for a single review invocation."""

    path: str
    language: str
    model: str = "gpt-4o-mini"
    max_file_bytes: int = 60_000
    max_workers: int = 8
    exclude_dirs: set = field(default_factory=lambda: set(DEFAULT_EXCLUDE_DIRS))
