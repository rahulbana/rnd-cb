"""Versioned prompt rendering."""

from __future__ import annotations

from app.prompts.renderer import PromptRenderer


def test_system_prompt_has_grounding_and_citation_rules():
    system = PromptRenderer("v1").system(not_found_message="NOT FOUND")
    lower = system.lower()
    assert "cite" in lower
    assert "context" in lower
    assert "NOT FOUND" in system  # fallback string injected
    assert "untrusted" in lower  # injection guardrail


def test_user_prompt_wraps_context_and_question():
    user = PromptRenderer("v1").user(question="what is X?", context="[1] X is a thing")
    assert "<context>" in user
    assert "[1] X is a thing" in user
    assert "what is X?" in user
