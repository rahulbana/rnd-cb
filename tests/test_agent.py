"""Tests for the compiled LangGraph agent."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage


def _cfg(user="alice", thread="alice::main"):
    return {"configurable": {"thread_id": thread, "user_id": user}}


def test_build_agent_binds_all_tools(make_agent):
    app, memory, tools = make_agent()
    assert len(tools) == 10
    assert app is not None


def test_plain_reply_no_tools(make_agent):
    app, memory, tools = make_agent([AIMessage(content="Hello!")])
    result = app.invoke({"messages": [HumanMessage("hi")]}, config=_cfg())
    assert result["messages"][-1].content == "Hello!"
    assert [m.type for m in result["messages"]] == ["human", "ai"]


def test_tool_call_routes_through_toolnode(make_agent):
    responses = [
        AIMessage(
            content="",
            tool_calls=[{"name": "save_memory",
                         "args": {"fact": "User likes tea"}, "id": "c1"}],
        ),
        AIMessage(content="Noted!"),
    ]
    app, memory, tools = make_agent(responses)
    result = app.invoke({"messages": [HumanMessage("I like tea")]}, config=_cfg())
    assert result["messages"][-1].content == "Noted!"
    assert [m.type for m in result["messages"]] == ["human", "ai", "tool", "ai"]
    # The tool actually persisted the fact.
    assert "User likes tea" in memory.list_all("alice")


def test_short_term_memory_persists_across_turns(make_agent):
    app, memory, tools = make_agent([AIMessage(content="ok")])
    cfg = _cfg()
    app.invoke({"messages": [HumanMessage("first")]}, config=cfg)
    result = app.invoke({"messages": [HumanMessage("second")]}, config=cfg)
    # human, ai, human, ai — the checkpointer kept the earlier turn.
    assert len(result["messages"]) == 4


def test_recall_injected_into_state(make_agent):
    app, memory, tools = make_agent([AIMessage(content="ok")])
    memory.add("alice", "User is allergic to peanuts")
    result = app.invoke({"messages": [HumanMessage("peanut snack?")]}, config=_cfg())
    assert "User is allergic to peanuts" in result["recalled_memories"]
