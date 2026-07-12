"""Tests for the optional Langfuse observability layer."""

from __future__ import annotations

from memory_agent.config import Settings
from memory_agent.observability import build_langfuse_handler, instrument


def test_disabled_without_keys():
    settings = Settings(langfuse_public_key="", langfuse_secret_key="")
    assert settings.langfuse_enabled is False
    assert build_langfuse_handler(settings) is None


def test_enabled_flag_requires_both_keys():
    assert Settings(langfuse_public_key="pk", langfuse_secret_key="").langfuse_enabled is False
    assert Settings(langfuse_public_key="", langfuse_secret_key="sk").langfuse_enabled is False
    assert Settings(langfuse_public_key="pk", langfuse_secret_key="sk").langfuse_enabled is True


def test_instrument_noop_when_handler_none():
    config = {"configurable": {"thread_id": "t", "user_id": "u"}}
    assert instrument(config, None, user_id="u", session_id="t") is config


def test_instrument_adds_callback_and_metadata():
    handler = object()
    base = {"configurable": {"thread_id": "sess1", "user_id": "alice"}}
    out = instrument(base, handler, user_id="alice", session_id="sess1")

    assert out is not base  # original config untouched
    assert out["callbacks"] == [handler]
    assert out["metadata"]["langfuse_user_id"] == "alice"
    assert out["metadata"]["langfuse_session_id"] == "sess1"
    assert out["metadata"]["langfuse_tags"]
    # configurable is preserved
    assert out["configurable"] == base["configurable"]


def test_instrument_preserves_existing_metadata():
    handler = object()
    base = {"configurable": {}, "metadata": {"keep": 1}}
    out = instrument(base, handler, user_id="u", session_id="s", tags=["x"])
    assert out["metadata"]["keep"] == 1
    assert out["metadata"]["langfuse_tags"] == ["x"]
