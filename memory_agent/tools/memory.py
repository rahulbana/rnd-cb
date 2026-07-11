"""Tools the agent uses to read and write its long-term memory.

`user_id` is injected from the graph config (never chosen by the model), so
memories are always scoped to the current user.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from ..storage import LongTermMemory


def make_memory_tools(memory: LongTermMemory) -> list:
    @tool
    def save_memory(fact: str, config: RunnableConfig) -> str:
        """Store a durable fact or preference about the user for future chats.

        Provide a single, self-contained fact (e.g. "User is learning Spanish").
        """
        user_id = config["configurable"]["user_id"]
        memory.add(user_id, fact)
        return f"Saved to long-term memory: {fact}"

    @tool
    def search_long_term_memory(query: str, config: RunnableConfig) -> str:
        """Search this user's long-term memory for facts relevant to `query`."""
        user_id = config["configurable"]["user_id"]
        hits = memory.search(user_id, query)
        if not hits:
            return "No relevant long-term memories found."
        return "\n".join(f"- {h}" for h in hits)

    return [save_memory, search_long_term_memory]
