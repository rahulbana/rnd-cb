"""Unit tests for state reducers and graph routing (pure logic, no I/O)."""
from __future__ import annotations

from app.agent.nodes import route_after_reflect
from app.agent.state import merge_sources


def test_merge_sources_dedupes_by_url_and_preserves_order():
    existing = [{"url": "a", "title": "A"}, {"url": "b", "title": "B"}]
    new = [{"url": "b", "title": "B-dup"}, {"url": "c", "title": "C"}]
    merged = merge_sources(existing, new)
    assert [s["url"] for s in merged] == ["a", "b", "c"]
    # First occurrence wins.
    assert next(s for s in merged if s["url"] == "b")["title"] == "B"


def test_merge_sources_handles_none_and_missing_url():
    merged = merge_sources(None, [{"title": "no url"}, {"url": "x"}])
    assert [s.get("url") for s in merged] == ["x"]


def test_route_to_search_when_gaps_remain():
    state = {"is_complete": False, "pending_queries": ["q1"]}
    assert route_after_reflect(state) == "search"


def test_route_to_synthesize_when_complete():
    assert route_after_reflect({"is_complete": True, "pending_queries": ["q"]}) == "synthesize"


def test_route_to_synthesize_when_no_pending_queries():
    assert route_after_reflect({"is_complete": False, "pending_queries": []}) == "synthesize"
