"""ConversationMemory: persistence, sliding window, summarization."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.llm_providers import FakeLLMProvider
from app.db.base import Base
from app.domain.models import Role
from app.services.conversation_memory import ConversationMemory


@pytest.fixture
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'mem.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, future=True)()
    yield db
    db.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_persist_and_history_order(session):
    mem = ConversationMemory(session, FakeLLMProvider(), window=10)
    conv = mem.ensure_conversation(None, user_id="u1", title="hi")
    mem.persist(conv.id, role=Role.USER, content="first question")
    mem.persist(conv.id, role=Role.ASSISTANT, content="first answer", provider="fake")

    history = await mem.history(conv.id)
    assert [m.role for m in history] == [Role.USER, Role.ASSISTANT]
    assert history[0].content == "first question"


@pytest.mark.asyncio
async def test_sliding_window_summarizes_overflow(session):
    mem = ConversationMemory(session, FakeLLMProvider(), window=2, summarize=True)
    conv = mem.ensure_conversation(None, user_id="u1", title="hi")
    for i in range(5):
        mem.persist(conv.id, role=Role.USER, content=f"msg {i}")

    history = await mem.history(conv.id)
    # A summary system message + the last 2 verbatim.
    assert history[0].role == Role.SYSTEM
    assert "Summary of earlier conversation" in history[0].content
    assert [m.content for m in history[-2:]] == ["msg 3", "msg 4"]


@pytest.mark.asyncio
async def test_persist_records_cost_trail(session):
    mem = ConversationMemory(session, FakeLLMProvider(), window=10)
    conv = mem.ensure_conversation(None, user_id="u1", title="hi")
    msg = mem.persist(
        conv.id,
        role=Role.ASSISTANT,
        content="answer",
        provider="openai",
        tokens_in=100,
        tokens_out=42,
        latency_ms=1234,
    )
    assert msg.provider == "openai"
    assert msg.tokens_in == 100
    assert msg.tokens_out == 42
    assert msg.latency_ms == 1234
