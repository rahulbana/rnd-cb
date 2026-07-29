"""Tests for the tool-usage tracker's classification and summary logic."""

from __future__ import annotations

import asyncio

from agentic_app.tracking import ToolUsageTracker


class _FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name


def _tracker() -> ToolUsageTracker:
    return ToolUsageTracker(
        mcp_tool_names={"add_client", "search_clients"},
        web_tool_names={"web_search_tavily", "web_search_duckduckgo"},
        custom_tool_names={"convert_currency"},
        live=False,
    )


def test_classify():
    t = _tracker()
    assert t.classify("add_client") == "mcp"
    assert t.classify("web_search_tavily") == "web_search"
    assert t.classify("convert_currency") == "custom"
    assert t.classify("unknown_tool") == "other"


def test_records_and_summary():
    t = _tracker()

    async def drive():
        for name, result in [
            ("search_clients", '{"count": 2}'),
            ("web_search_duckduckgo", '{"results": []}'),
            ("search_clients", '{"count": 0}'),
        ]:
            tool = _FakeTool(name)
            await t.on_tool_start(None, None, tool)
            await t.on_tool_end(None, None, tool, result)

    asyncio.run(drive())
    counts = t.counts()
    assert counts["mcp"] == 2
    assert counts["web_search"] == 1
    assert t.summary_line() == "MCP×2, WEB×1"
    assert all(c.duration_ms is not None for c in t.calls)


def test_error_detection():
    t = _tracker()

    async def drive():
        tool = _FakeTool("convert_currency")
        await t.on_tool_start(None, None, tool)
        await t.on_tool_end(None, None, tool, '{"error": "unreachable"}')

    asyncio.run(drive())
    assert t.calls[0].ok is False
