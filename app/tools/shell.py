"""Shell command tool.

Executes shell commands on the host. This is the most powerful — and most
dangerous — tool, so it is **disabled by default** and only registered when
``SHELL_TOOL_ENABLED=true``. Even when enabled it runs with a timeout, bounded
output, and a fixed working directory (the workspace sandbox unless
``SHELL_WORKDIR`` is set).

Note: this grants the agent the ability to run arbitrary commands with your
user's privileges. Only enable it in an environment you trust.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .base import Tool, ToolRegistry

_MAX_OUTPUT = 20_000


def register(registry: ToolRegistry, config) -> None:
    # Opt-in only: if not explicitly enabled, the tool is never advertised.
    if not config.shell_enabled:
        return

    workdir = Path(config.shell_workdir).resolve() if config.shell_workdir else config.workspace_path
    workdir.mkdir(parents=True, exist_ok=True)
    default_timeout = config.shell_timeout

    def run_shell(command: str, timeout: int | None = None) -> str:
        limit = max(1, min(int(timeout or default_timeout), 300))
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=limit,
            )
        except subprocess.TimeoutExpired:
            return f"Command timed out after {limit}s."
        except Exception as exc:  # noqa: BLE001
            return f"Failed to run command: {exc}"

        def _clip(text: str) -> str:
            if len(text) > _MAX_OUTPUT:
                return text[:_MAX_OUTPUT] + "\n... (output truncated)"
            return text

        parts = [f"exit_code: {proc.returncode}"]
        if proc.stdout:
            parts.append("stdout:\n" + _clip(proc.stdout.rstrip()))
        if proc.stderr:
            parts.append("stderr:\n" + _clip(proc.stderr.rstrip()))
        if not proc.stdout and not proc.stderr:
            parts.append("(no output)")
        return "\n".join(parts)

    registry.register(
        Tool(
            name="run_shell",
            description=(
                "Run a shell command on the host and return its exit code, "
                f"stdout and stderr. Commands run in '{workdir}' with a timeout. "
                "Use for inspecting files, running scripts, git, or system tasks. "
                "Prefer the dedicated tools (db, filesystem) when they fit. "
                "State clearly what you intend to run before doing anything "
                "destructive."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command line to execute.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": f"Seconds before the command is killed (default {default_timeout}, max 300).",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            handler=run_shell,
        )
    )
