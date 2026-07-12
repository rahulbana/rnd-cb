"""Tests for CLI session state and command helpers."""

from __future__ import annotations

from memory_agent.cli import commands
from memory_agent.cli.session import Session


def test_session_config_scopes():
    s = Session("alice")
    assert s.thread_id == "alice::main"
    assert s.config == {"configurable": {"thread_id": "alice::main", "user_id": "alice"}}


def test_session_new_thread_changes_thread_only():
    s = Session("alice")
    before = s.thread_id
    s.new_thread()
    assert s.thread_id != before
    assert s.user_id == "alice"
    assert s.thread_id.startswith("alice::")


def test_print_memories_empty(memory, capsys):
    commands.print_memories(memory, "ghost")
    assert "no long-term memories" in capsys.readouterr().out


def test_print_memories_lists(memory, capsys):
    memory.add("alice", "User likes tea")
    commands.print_memories(memory, "alice")
    out = capsys.readouterr().out
    assert "User likes tea" in out


def test_print_history(db, capsys):
    db.log_message("alice", "t1", "user", "hello")
    db.log_message("alice", "t1", "assistant", "hi")
    commands.print_history(db, "alice")
    out = capsys.readouterr().out
    assert "[you] hello" in out
    assert "[bot] hi" in out


def test_print_tools(memory, capsys):
    from memory_agent.tools.memory import make_memory_tools

    commands.print_tools(make_memory_tools(memory))
    out = capsys.readouterr().out
    assert "save_memory" in out
    assert "search_long_term_memory" in out


def test_prompt_user_id(monkeypatch, db):
    # empty input is rejected, then a real username accepted
    answers = iter(["", "alice"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert commands.prompt_user_id(db) == "alice"
