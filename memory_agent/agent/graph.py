"""Assembles the LangGraph agent.

Graph shape::

    START -> recall -> agent -> (tools -> agent)* -> END

* ``recall`` performs semantic lookup of long-term memories for the latest
  user message and stashes them in state.
* ``agent`` builds a system prompt (with recalled memories), trims the running
  conversation to a short-term window, and calls the tool-enabled LLM.
* ``tools`` executes any tool the model asked for, then returns to ``agent``.

Short-term memory (the running conversation) is persisted per-thread by the
LangGraph SQLite checkpointer, so a conversation survives restarts.
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from ..config import Settings
from ..models import make_chat_model, make_embeddings
from ..storage import Database, LongTermMemory
from ..tools import build_tools
from .prompts import SYSTEM_PROMPT, render_memories
from .state import AgentState


def build_agent(db: Database, settings: Settings, checkpointer):
    """Compile the LangGraph app.

    Returns ``(app, memory, tools)`` — the compiled graph, the long-term memory
    store, and the list of tools bound to the agent.
    """
    llm = make_chat_model(settings)
    embeddings = make_embeddings(settings)
    memory = LongTermMemory(
        db,
        embeddings,
        top_k=settings.memory_top_k,
        min_score=settings.memory_min_score,
    )

    tools = build_tools(settings, llm, memory)
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
            SYSTEM_PROMPT.format(memories=render_memories(state.get("recalled_memories", [])))
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
    graph.set_entry_point("recall")
    graph.add_edge("recall", "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    app = graph.compile(checkpointer=checkpointer)
    return app, memory, tools
