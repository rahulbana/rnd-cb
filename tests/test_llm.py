"""Tests for the provider-agnostic LLM layer.

The hosted providers are exercised with an injected fake client, so these tests
need neither the ``openai``/``anthropic`` packages nor network access.
"""

import json
import types

import pytest

from product_intel.llm import OfflineLLM, get_llm
from product_intel.llm.openai_client import OpenAILLM


def test_factory_offline_default():
    assert isinstance(get_llm(), OfflineLLM)
    assert isinstance(get_llm("offline"), OfflineLLM)


def test_factory_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_llm("does-not-exist")


class _FakeChatCompletions:
    """Minimal stand-in for openai's client.chat.completions."""

    def __init__(self, content):
        self._content = content

    def create(self, **kwargs):
        msg = types.SimpleNamespace(content=self._content)
        choice = types.SimpleNamespace(message=msg)
        return types.SimpleNamespace(choices=[choice])


def _fake_client(content):
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=_FakeChatCompletions(content)))


def test_openai_client_uses_injected_response():
    story_json = json.dumps({"user_story": "As a user...", "acceptance_criteria": ["c1", "c2"]})
    llm = OpenAILLM(client=_fake_client(story_json))
    story, criteria = llm.draft_user_story("Fix pairing", "defect", ["evidence"])
    assert story == "As a user..."
    assert criteria == ["c1", "c2"]


def test_openai_client_falls_back_on_bad_json():
    # draft_user_story expects JSON; garbage should trigger the offline fallback.
    llm = OpenAILLM(client=_fake_client("not json at all"))
    story, criteria = llm.draft_user_story("Fix pairing", "defect", ["evidence"])
    assert story  # non-empty fallback story
    assert criteria  # non-empty fallback criteria


def test_openai_client_summarize_gap_returns_text():
    llm = OpenAILLM(client=_fake_client("The feature underdelivers on pairing."))
    out = llm.summarize_gap("Multipoint Pairing", ["stutters when switching"])
    assert "pairing" in out.lower()


def test_openai_model_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    llm = OpenAILLM(client=_fake_client("x"))
    assert llm.model == "gpt-4o"
