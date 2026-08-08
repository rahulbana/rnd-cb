"""A tiny, dependency-free tool framework.

Each tool is described by a JSON Schema (so OpenAI can call it) and backed by a
plain Python callable. The ``ToolRegistry`` exposes the schema list for the API
and dispatches incoming tool calls to the right handler with error isolation —
a tool that raises never crashes the agent loop, it just returns an error
string the model can read and react to.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema for the arguments object
    handler: Callable[..., Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return list(self._tools)

    def openai_schema(self) -> list[dict]:
        """The ``tools=[...]`` payload for the Chat Completions API."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def dispatch(self, name: str, arguments: dict[str, Any] | None) -> str:
        """Run a tool by name and always return a string for the model."""
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'."

        args = arguments or {}
        if not isinstance(args, dict):
            return f"Error: arguments for '{name}' must be a JSON object."

        # Reject unexpected kwargs cleanly rather than raising a TypeError.
        sig = inspect.signature(tool.handler)
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if not accepts_kwargs:
            allowed = set(sig.parameters)
            unknown = set(args) - allowed
            if unknown:
                return (
                    f"Error: unknown argument(s) for '{name}': "
                    f"{', '.join(sorted(unknown))}. Allowed: {', '.join(sorted(allowed))}."
                )

        try:
            result = tool.handler(**args)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the model
            return f"Error executing '{name}': {exc}"

        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(result)
