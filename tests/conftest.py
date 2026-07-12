"""Shared pytest fixtures.

Everything here keeps tests fully offline: no OpenAI calls, no network. The
OpenAI models are replaced with deterministic fakes, and HTTP-backed tools are
monkeypatched in their own test modules.
"""

from __future__ import annotations

import os

# The OpenAI key is read at import time by config.py; set a dummy before any
# memory_agent import so construction never fails during collection.
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

import pytest
from langchain_core.messages import AIMessage

from memory_agent.config import Settings
from memory_agent.storage import Database, LongTermMemory


# --------------------------------------------------------------------------
# fake models
# --------------------------------------------------------------------------

class FakeEmbeddings:
    """Deterministic keyword-presence embeddings.

    Each text maps to a 0/1 vector over a fixed keyword vocabulary, so texts
    sharing a keyword score high (cosine ~1) and unrelated texts score ~0. That
    makes semantic-recall assertions stable without any real model.
    """

    KEYWORDS = ["peanut", "spanish", "tea", "dog", "python", "secret", "hiking"]

    def embed_query(self, text: str) -> list[float]:
        t = text.lower()
        return [1.0 if kw in t else 0.0 for kw in self.KEYWORDS]


class FakeChat:
    """Scriptable chat model. `responses` is a list of AIMessages returned in
    order; the last one repeats once exhausted."""

    def __init__(self, responses: list[AIMessage] | None = None):
        self.responses = responses or [AIMessage(content="ok")]
        self.calls = 0
        self.bound_tools: list[str] = []

    def bind_tools(self, tools):
        self.bound_tools = [t.name for t in tools]
        return self

    def invoke(self, messages):
        idx = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        # Return a fresh copy so each turn is a distinct message (a reused
        # instance would get deduped by add_messages once it has an id).
        return self.responses[idx].model_copy()


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def fake_embeddings():
    return FakeEmbeddings()


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    yield database
    database.close()


@pytest.fixture
def memory(db, fake_embeddings):
    return LongTermMemory(db, fake_embeddings, top_k=5, min_score=-1.0)


@pytest.fixture
def make_agent(monkeypatch, db, settings):
    """Factory: build a real graph with a scripted FakeChat and FakeEmbeddings.

    Usage: ``app, memory, tools = make_agent([AIMessage(...), ...])``.
    """
    from memory_agent.agent import graph as graph_mod
    from memory_agent.agent import build_agent

    def _make(responses=None):
        chat = FakeChat(responses)
        monkeypatch.setattr(graph_mod, "make_chat_model", lambda s: chat)
        monkeypatch.setattr(graph_mod, "make_embeddings", lambda s: FakeEmbeddings())
        from langgraph.checkpoint.memory import MemorySaver

        return build_agent(db, settings, MemorySaver())

    return _make
