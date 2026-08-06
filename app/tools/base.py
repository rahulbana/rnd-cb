"""Core primitives shared by every tool: the Tool descriptor and helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import httpx

# A shared, reasonably-timed HTTP client factory used by network tools.
DEFAULT_TIMEOUT = 20.0
USER_AGENT = "AI-Agent/1.0 (+https://github.com/rahulbana/rnd-cb)"


def http_get(url: str, *, params: dict | None = None, headers: dict | None = None,
             timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Perform a GET request with sane defaults and raise on HTTP errors."""
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    resp = httpx.get(url, params=params, headers=h, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return resp


def http_get_json(url: str, *, params: dict | None = None,
                  headers: dict | None = None, timeout: float = DEFAULT_TIMEOUT) -> Any:
    """GET a URL and return parsed JSON."""
    return http_get(url, params=params, headers=headers, timeout=timeout).json()


@dataclass
class Tool:
    """A single capability the agent can call.

    Attributes:
        name: Unique tool identifier exposed to the LLM.
        description: Natural-language description guiding when to use the tool.
        parameters: JSON-schema object describing the tool's arguments.
        func: The Python callable implementing the tool. Receives keyword
            arguments matching `parameters` and returns a JSON-serializable value.
        category: UI grouping label.
    """

    name: str
    description: str
    parameters: dict
    func: Callable[..., Any]
    category: str = "General"

    def openai_schema(self) -> dict:
        """Return the OpenAI `tools` entry for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def run(self, **kwargs) -> Any:
        return self.func(**kwargs)


def ok(data: Any, **extra) -> dict:
    """Standard success envelope."""
    out = {"ok": True, "data": data}
    out.update(extra)
    return out


def err(message: str, **extra) -> dict:
    """Standard error envelope (tools should not raise; return this instead)."""
    out = {"ok": False, "error": message}
    out.update(extra)
    return out


# A minimal JSON-schema object with no parameters (for zero-arg tools).
NO_PARAMS = {"type": "object", "properties": {}, "additionalProperties": False}
