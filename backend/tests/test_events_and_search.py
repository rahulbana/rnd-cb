"""Tests for event mapping, the SSE broker, and search provider fallback."""
from __future__ import annotations

import app.tools.search as search_mod
from app.services.events import EventBroker
from app.services.research_service import ResearchService
from app.tools.search import SearchResult, web_search


def test_event_mapping_for_each_node():
    plan = ResearchService._to_event("plan", {"plan": ["q"], "pending_queries": ["a", "b"]})
    assert plan["phase"] == "planning" and plan["queries"] == ["a", "b"]

    searched = ResearchService._to_event(
        "search", {"executed_queries": ["a"], "sources": [{}, {}], "findings": ["f"]}
    )
    assert searched["new_sources"] == 2 and searched["new_findings"] == 1

    reflected = ResearchService._to_event(
        "reflect", {"iteration": 2, "is_complete": True, "knowledge_gaps": []}
    )
    assert reflected["iteration"] == 2 and reflected["is_complete"] is True

    assert ResearchService._to_event("synthesize", {})["phase"] == "synthesizing"
    assert ResearchService._to_event("unknown", {}) is None


async def test_broker_replays_history_then_terminates():
    broker = EventBroker()
    broker.publish("t1", {"type": "run_started", "terminal": False})
    broker.publish("t1", {"type": "completed", "terminal": True})

    seen = [e async for e in broker.subscribe("t1")]
    assert [e["type"] for e in seen] == ["run_started", "completed"]
    assert broker.is_terminated("t1")


async def test_search_falls_back_to_ddg_when_tavily_fails(monkeypatch):
    monkeypatch.setattr(search_mod.get_settings(), "tavily_api_key", "present", raising=False)

    async def _boom(query, limit):
        raise RuntimeError("tavily down")

    async def _ddg(query, limit):
        return [SearchResult(title="t", url="u", content="c", provider="duckduckgo")]

    monkeypatch.setattr(search_mod, "_tavily_search", _boom)
    monkeypatch.setattr(search_mod, "_ddg_search", _ddg)

    results = await web_search("anything")
    assert len(results) == 1 and results[0].provider == "duckduckgo"


async def test_search_returns_empty_when_all_providers_fail(monkeypatch):
    async def _ddg(query, limit):
        raise RuntimeError("ddg down")

    monkeypatch.setattr(search_mod.get_settings(), "tavily_api_key", "", raising=False)
    monkeypatch.setattr(search_mod, "_ddg_search", _ddg)

    assert await web_search("anything") == []
