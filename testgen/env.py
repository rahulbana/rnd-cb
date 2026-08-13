"""Minimal .env loader (no third-party dependency).

Reads simple KEY=VALUE lines from a .env file and populates os.environ.
Existing environment variables always win, so an explicit export or a shell
override is never clobbered by the file.
"""

from __future__ import annotations

import os
from pathlib import Path


def _parse_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export "):].lstrip()
    if "=" not in line:
        return None
    key, _, value = line.partition("=")
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    # Strip matching surrounding quotes, keeping inner content verbatim.
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def load_dotenv(path: str | os.PathLike | None = None, *, override: bool = False) -> bool:
    """Load variables from a .env file into ``os.environ``.

    If ``path`` is omitted, searches the current directory and its parents for
    a file named ``.env``. Returns ``True`` if a file was found and read.
    Existing env vars are preserved unless ``override`` is set.
    """
    env_path = _resolve(path)
    if env_path is None or not env_path.is_file():
        return False

    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = _parse_line(raw)
        if parsed is None:
            continue
        key, value = parsed
        if override or key not in os.environ:
            os.environ[key] = value
    return True


def _resolve(path: str | os.PathLike | None) -> Path | None:
    if path is not None:
        return Path(path).expanduser()
    # Walk up from the current working directory looking for a .env file.
    for directory in (Path.cwd(), *Path.cwd().parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None
