"""The agent: a custom OpenAI function-calling loop (no orchestration library).

The loop is deliberately small and readable:

    1. Send the running message list + tool schemas to the model.
    2. If the model asks to call tools, run each one (handling the parallel
       tool-call case), append the results, and loop again.
    3. When the model returns a plain message, that's the answer.

A ``max_steps`` guard bounds tool-calling so a misbehaving turn can't spin
forever. Conversation history is kept on the instance so the CLI can hold a
multi-turn chat.
"""

from __future__ import annotations

import json
from typing import Callable

from .llm import LLMClient
from .tools import ToolRegistry

SYSTEM_PROMPT = """\
You are a capable personal assistant for an ecommerce business owner.

You have tools for:
- Querying a local ecommerce SQL database (customers, products, orders, \
inventory, payments, reviews). Inspect the schema before writing SQL.
- Quick web search and slower in-depth web research.
- Reading and writing files in a private workspace sandbox.
- Sending email over SMTP.
- Exact calculations.

Operating principles:
- Prefer tools over guessing. For any question about the business's own data, \
query the database rather than assuming.
- Use the calculator for arithmetic (totals, margins, tax) instead of doing \
mental math.
- Choose web_search for quick facts and deep_web_search for research that \
needs multiple sources or detail.
- Before sending real email, make sure the recipient and content are what the \
user intends.
- When you present numbers from the database, be precise and cite what you \
queried. Keep answers concise and well organised.
"""


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        max_steps: int = 12,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps
        self.messages: list[dict] = [{"role": "system", "content": system_prompt}]

    def reset(self) -> None:
        """Clear conversation history, keeping the system prompt."""
        self.messages = self.messages[:1]

    def send(
        self,
        user_message: str,
        on_tool_call: Callable[[str, dict], None] | None = None,
    ) -> str:
        """Run one user turn to completion and return the assistant's answer.

        ``on_tool_call`` is an optional callback (name, args) so a UI can show
        tool activity as it happens.
        """
        self.messages.append({"role": "user", "content": user_message})
        tools = self.registry.openai_schema()

        for _ in range(self.max_steps):
            message = self.llm.chat(self.messages, tools=tools)
            self.messages.append(message.model_dump(exclude_none=True))

            tool_calls = message.tool_calls or []
            if not tool_calls:
                return message.content or ""

            for call in tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if on_tool_call:
                    on_tool_call(name, args)
                result = self.registry.dispatch(name, args)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": name,
                        "content": result,
                    }
                )

        return (
            "I stopped after reaching the maximum number of tool steps for this "
            "turn. Please refine your request or ask me to continue."
        )
