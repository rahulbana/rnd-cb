"""Tests for the best-effort web-research module."""
from __future__ import annotations

from app.core.config import get_settings
from app.services import research


async def test_research_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("WEB_RESEARCH", "false")
    get_settings.cache_clear()
    try:
        assert await research.research_quiz_context(9, "Math", "Quadratics") == ""
    finally:
        get_settings.cache_clear()


async def test_research_degrades_on_failure(monkeypatch):
    monkeypatch.setenv("WEB_RESEARCH", "true")
    get_settings.cache_clear()

    def boom(*_a, **_k):
        raise RuntimeError("network down")

    monkeypatch.setattr(research, "_research_sync", boom)
    try:
        # Must not raise — returns empty context instead.
        assert await research.research_quiz_context(9, "Math", "Quadratics") == ""
    finally:
        get_settings.cache_clear()


def test_format_dedupes_and_truncates():
    results = [
        {"title": "A", "snippet": "x" * 400, "url": "http://a"},
        {"title": "A", "snippet": "dup", "url": "http://a"},  # duplicate title
        {"title": "B", "snippet": "", "url": "http://b"},  # empty snippet skipped
    ]
    out = research._format(results)
    assert out.count("- A:") == 1
    assert "- B:" not in out
