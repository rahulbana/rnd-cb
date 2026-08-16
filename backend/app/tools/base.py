"""Tool interface for the agent.

A tool exposes a name, a natural-language description (the model reads this to
decide when to use it), a JSON-Schema for its parameters, and an async ``run``.
``schema()`` renders the OpenAI/Ollama function-tool format.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    name: str = "tool"
    description: str = ""
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    # A short human label + emoji for the UI trace.
    label: str = "🔧 Tool"

    @abstractmethod
    async def run(self, **kwargs) -> str:
        """Execute the tool and return a string result for the model."""

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
