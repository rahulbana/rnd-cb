"""The LangGraph agent wiring short-term and long-term memory together.

Graph shape::

    START -> recall -> agent -> (tools -> agent)* -> END

* ``recall`` performs semantic lookup of long-term memories for the latest
  user message and stashes them in state.
* ``agent`` builds a system prompt (with recalled memories), trims the running
  conversation to a short-term window, and calls the tool-enabled LLM.
* ``tools`` executes ``save_memory`` / ``search_long_term_memory`` when the
  model asks for them, then control returns to ``agent``.

Short-term memory (the running conversation) is persisted per-thread by the
LangGraph SQLite checkpointer, so a conversation survives restarts.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from .config import Settings
from .db import Database
from .memory import LongTermMemory
from .tools import build_extra_tools


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    recalled_memories: list[str]


SYSTEM_PROMPT = """\
You are a helpful, friendly CLI assistant with memory.

You have two kinds of memory:
- Short-term: the current conversation (already visible in the messages).
- Long-term: durable facts about this specific user, recalled below.

Use the `save_memory` tool whenever the user shares something worth remembering
for future conversations: their name, preferences, ongoing projects, important
people/pets, goals, or recurring context. Save one concise fact per call, phrased
so it makes sense on its own later (e.g. "User prefers concise answers").
Do NOT save trivia, one-off requests, or anything the user asks you to forget.

Use `search_long_term_memory` if you need to recall something not already shown.

You also have utility tools: `web_search` (current info), `convert_currency`,
`convert_units`, `current_time` (by timezone/city/country), `ip_lookup` (domain
or URL), `draft_email`, `summarize_text`, and `translate_text`. Call a tool when
it clearly helps; don't guess at facts a tool can look up.

Relevant long-term memories about this user:
{memories}
"""


def _render_memories(memories: list[str]) -> str:
    if not memories:
        return "(none recalled for this message)"
    return "\n".join(f"- {m}" for m in memories)


def build_agent(db: Database, settings: Settings, checkpointer):
    """Compile and return the LangGraph app plus the long-term memory store."""

    llm = ChatOpenAI(
        model=settings.chat_model,
        temperature=settings.temperature,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    memory = LongTermMemory(
        db,
        embeddings,
        top_k=settings.memory_top_k,
        min_score=settings.memory_min_score,
    )

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

    tools = [save_memory, search_long_term_memory]
    # Utility tools reuse the base (tool-free) LLM for their internal sub-tasks.
    tools += build_extra_tools(settings, llm)
    llm_with_tools = llm.bind_tools(tools)

    def recall(state: AgentState, config: RunnableConfig) -> dict:
        user_id = config["configurable"]["user_id"]
        last_human = next(
            (m for m in reversed(state["messages"]) if m.type == "human"), None
        )
        recalled = memory.search(user_id, last_human.content) if last_human else []
        return {"recalled_memories": recalled}

    def agent(state: AgentState, config: RunnableConfig) -> dict:
        system = SystemMessage(
            SYSTEM_PROMPT.format(
                memories=_render_memories(state.get("recalled_memories", []))
            )
        )
        # Short-term window: only the most recent turns go to the model, kept on
        # valid boundaries so tool-call/tool-result pairs are never split.
        window = trim_messages(
            state["messages"],
            token_counter=len,  # count messages, not tokens
            max_tokens=settings.short_term_window,
            strategy="last",
            start_on="human",
            end_on=("human", "tool"),
            include_system=False,
        )
        response = llm_with_tools.invoke([system, *window])
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("recall", recall)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "recall")
    graph.add_edge("recall", "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    app = graph.compile(checkpointer=checkpointer)
    return app, memory
