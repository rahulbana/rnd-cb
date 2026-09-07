"""Minimal, dependency-free ``.env`` loader.

Loads ``KEY=VALUE`` pairs from a ``.env`` file into ``os.environ`` so that
``product-intel run --llm openai`` can pick up ``OPENAI_API_KEY`` (and friends)
without requiring the third-party ``python-dotenv`` package. Existing environment
variables always win, so a value exported in the shell overrides the file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional


def find_dotenv(start: Optional[Path] = None, filename: str = ".env") -> Optional[Path]:
    """Search ``start`` (default: cwd) and its parents for ``filename``."""

    here = (start or Path.cwd()).resolve()
    for directory in [here, *here.parents]:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def parse_dotenv(text: str) -> Dict[str, str]:
    """Parse ``.env`` text into a dict. Tolerant of comments, blanks, quotes."""

    values: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        # strip a trailing inline comment only for unquoted values
        if val and val[0] not in ("'", '"') and " #" in val:
            val = val.split(" #", 1)[0].rstrip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        values[key] = val
    return values


def load_dotenv(
    path: Optional[Path] = None, *, override: bool = False
) -> Optional[Path]:
    """Load a ``.env`` file into ``os.environ``.

    Returns the path that was loaded, or ``None`` if no file was found. By
    default, variables already present in the environment are left untouched.
    """

    dotenv_path = path or find_dotenv()
    if dotenv_path is None or not dotenv_path.is_file():
        return None
    for key, val in parse_dotenv(dotenv_path.read_text(encoding="utf-8")).items():
        if override or key not in os.environ:
            os.environ[key] = val
    return dotenv_path
