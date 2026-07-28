"""Shared test fixtures.

Tests must be deterministic and offline: they never depend on a real OpenAI key
or network access, regardless of what a local ``.env`` sets. This autouse
fixture pins the planner backend to the heuristic (offline) planner for every
test. Tests that specifically exercise the LLM planner construct it directly and
mock the network call (see ``test_llm_planner.py``).
"""

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _force_offline_planner(monkeypatch):
    monkeypatch.setattr(settings, "planner_backend", "heuristic", raising=False)
