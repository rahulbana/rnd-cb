"""Manage per-project sandbox directories and (for Python) isolated venvs."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ..config import get_settings
from .executor import CommandResult, run_command

_SAFE = re.compile(r"[^a-zA-Z0-9_-]+")


def slugify(name: str) -> str:
    slug = _SAFE.sub("-", name.strip().lower()).strip("-")
    return slug or "project"


class SandboxManager:
    def __init__(self, project_id: str, name: str):
        self.settings = get_settings()
        self.project_id = project_id
        # Directory is <name-slug>-<short id> so it's human-readable but unique.
        self.dir_name = f"{slugify(name)}-{project_id[:8]}"
        self.root: Path = self.settings.workspace_root_path / self.dir_name

    def create(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    # --- path helpers -------------------------------------------------

    def resolve(self, relative: str) -> Path:
        """Resolve a path *within* the sandbox, refusing escape attempts."""
        target = (self.root / relative).resolve()
        root = self.root.resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"Path escapes sandbox: {relative}")
        return target

    def write_file(self, relative: str, content: str) -> Path:
        target = self.resolve(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_file(self, relative: str) -> str:
        return self.resolve(relative).read_text(encoding="utf-8", errors="replace")

    def list_files(self) -> list[str]:
        out: list[str] = []
        skip = {".git", "__pycache__", ".venv", "node_modules", ".pytest_cache"}
        for p in sorted(self.root.rglob("*")):
            if any(part in skip for part in p.relative_to(self.root).parts):
                continue
            if p.is_file():
                out.append(str(p.relative_to(self.root)))
        return out

    # --- python venv --------------------------------------------------

    @property
    def venv_dir(self) -> Path:
        return self.root / ".venv"

    def venv_python(self) -> Path:
        if sys.platform.startswith("win"):
            return self.venv_dir / "Scripts" / "python.exe"
        return self.venv_dir / "bin" / "python"

    async def ensure_python_venv(self) -> CommandResult:
        """Create a virtualenv for the project if it doesn't exist yet."""
        if self.venv_python().exists():
            return CommandResult(command="venv (cached)", returncode=0, stdout="")
        return await run_command(
            f'"{sys.executable}" -m venv .venv',
            cwd=self.root,
            timeout=self.settings.command_timeout,
        )

    def venv_env(self) -> dict:
        """Environment that puts the venv first on PATH.

        With this, plain ``python`` / ``pip`` / ``pytest`` invocations inside
        the sandbox resolve to the project's isolated interpreter, so LLM-authored
        setup and test commands "just work" without rewriting.
        """
        bin_dir = self.venv_python().parent
        return {
            "VIRTUAL_ENV": str(self.venv_dir),
            "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
        }
