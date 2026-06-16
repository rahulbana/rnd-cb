"""The Ye'ai agent: an OpenAI chat loop with tool calling.

The agent keeps a running conversation, exposes the registered tools to the
model, and executes any tool calls the model requests until it produces a
final natural-language answer.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from openai import OpenAI

from . import config
from .tools.base import Tool, build_registry

SYSTEM_PROMPT = (
    "You are Ye'ai Assistant, a helpful CLI AI agent built by the Olympic "
    "Ye'ai team. You can use tools to search the web (normal or deep), convert "
    "currencies, do calculations, convert length units, summarise countries, "
    "report the current time, timezone and temperature for a place, and "
    "summarise a web page or a YouTube video from its URL. "
    "Prefer using a tool when a question needs fresh data or precise "
    "computation rather than guessing. When you use a tool, base your answer on "
    "its result and briefly cite what you found. Keep answers concise and "
    "clear."
)


class AgentError(RuntimeError):
    """Raised for configuration problems (e.g. a missing API key)."""


class YeaiAgent:
    def __init__(
        self,
        client: Optional[OpenAI] = None,
        model: Optional[str] = None,
        registry: Optional[Dict[str, Tool]] = None,
    ) -> None:
        self.model = model or config.OPENAI_MODEL
        self.registry: Dict[str, Tool] = registry or build_registry()
        self._tool_schemas = [t.openai_schema() for t in self.registry.values()]
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        if client is not None:
            self.client = client
        else:
            if not config.OPENAI_API_KEY:
                raise AgentError(
                    "OPENAI_API_KEY is not set. Add it to your environment or a "
                    ".env file (see .env.example)."
                )
            self.client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
            )

    @property
    def tool_names(self) -> List[str]:
        return list(self.registry.keys())

    def reset(self) -> None:
        """Forget the conversation so far (keeps the system prompt)."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def ask(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> str:
        """Send ``user_message`` and return the assistant's final answer.

        ``on_tool_call`` is an optional callback invoked with the tool name and
        its arguments whenever a tool is about to run -- handy for showing
        progress in the CLI.
        """
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(config.MAX_AGENT_STEPS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self._tool_schemas,
                tool_choice="auto",
            )
            message = response.choices[0].message

            if not message.tool_calls:
                content = message.content or ""
                self.messages.append({"role": "assistant", "content": content})
                return content

            # Record the assistant turn that requested the tool calls.
            self.messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )

            for tool_call in message.tool_calls:
                result = self._run_tool_call(tool_call, on_tool_call)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return (
            "I reached the maximum number of reasoning steps without finishing. "
            "Please try rephrasing or narrowing your request."
        )

    def _run_tool_call(
        self,
        tool_call: Any,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]],
    ) -> str:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            return f"ERROR: could not parse arguments for tool '{name}': {exc}"

        if on_tool_call is not None:
            on_tool_call(name, args)

        tool = self.registry.get(name)
        if tool is None:
            return f"ERROR: unknown tool '{name}'."
        return tool.run(**args)
