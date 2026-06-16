"""Tool abstraction shared by every Ye'ai tool.

A :class:`Tool` bundles together the metadata OpenAI needs to know a tool
exists (name, description, JSON-schema parameters) with the Python callable
that actually runs it. The :func:`build_registry` helper collects all of the
tools the agent should expose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List


# A handler receives the already-parsed keyword arguments and returns a string
# that is fed back to the model as the tool result.
Handler = Callable[..., str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Handler

    def openai_schema(self) -> Dict[str, Any]:
        """Return the schema in the shape the OpenAI Chat API expects."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def run(self, **kwargs: Any) -> str:
        """Execute the tool, never raising -- errors come back as text."""
        try:
            return self.handler(**kwargs)
        except Exception as exc:  # noqa: BLE001 - surface errors to the model.
            return f"ERROR while running tool '{self.name}': {exc}"


def build_registry() -> Dict[str, Tool]:
    """Import every tool module and return a {name: Tool} mapping."""
    # Imported lazily to avoid import cycles and to keep optional deps local.
    from . import (
        calculator,
        country,
        currency,
        search,
        time_weather,
        units,
        webpage,
        youtube,
    )

    tools: List[Tool] = []
    for module in (
        search,
        currency,
        calculator,
        units,
        country,
        time_weather,
        webpage,
        youtube,
    ):
        tools.extend(module.TOOLS)

    return {tool.name: tool for tool in tools}
