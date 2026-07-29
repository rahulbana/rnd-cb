"""Tool-usage tracking via the Agents SDK lifecycle hooks.

`ToolUsageTracker` subscribes to `on_tool_start` / `on_tool_end` and labels every
tool call with a category — MCP (client directory), WEB (web search), or CUSTOM
(currency, etc.) — so you can see exactly which capability answered a query.

It prints a live line as each tool fires and can emit a per-turn summary. It also
keeps a structured record (`.calls`) for logging/telemetry.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass

from agents import RunHooks
from rich.console import Console

console = Console()

# category -> (short label, rich style)
_CATEGORY_STYLE: dict[str, tuple[str, str]] = {
    "mcp": ("MCP", "bold blue"),
    "web_search": ("WEB", "bold green"),
    "custom": ("CUSTOM", "bold magenta"),
    "other": ("TOOL", "dim"),
}


@dataclass
class ToolCall:
    name: str
    category: str
    duration_ms: float | None = None
    ok: bool | None = None


class ToolUsageTracker(RunHooks):
    """Records and (optionally) prints which tool category handles each step."""

    def __init__(
        self,
        mcp_tool_names: set[str] | None = None,
        web_tool_names: set[str] | None = None,
        custom_tool_names: set[str] | None = None,
        *,
        live: bool = True,
    ) -> None:
        self.mcp_tool_names = set(mcp_tool_names or ())
        self.web_tool_names = set(web_tool_names or ())
        self.custom_tool_names = set(custom_tool_names or ())
        self.live = live
        self.calls: list[ToolCall] = []
        # name -> stack of start timestamps (handles repeated / nested calls)
        self._starts: dict[str, list[float]] = {}

    def classify(self, tool_name: str) -> str:
        if tool_name in self.web_tool_names:
            return "web_search"
        if tool_name in self.custom_tool_names:
            return "custom"
        if tool_name in self.mcp_tool_names:
            return "mcp"
        return "other"

    def _tag(self, category: str) -> str:
        label, style = _CATEGORY_STYLE.get(category, _CATEGORY_STYLE["other"])
        return f"[{style}]\\[{label}][/]"

    async def on_tool_start(self, context, agent, tool) -> None:  # noqa: ANN001 - SDK types
        category = self.classify(tool.name)
        self._starts.setdefault(tool.name, []).append(time.perf_counter())
        if self.live:
            console.print(f"  {self._tag(category)} → [bold]{tool.name}[/]")

    async def on_tool_end(self, context, agent, tool, result) -> None:  # noqa: ANN001
        category = self.classify(tool.name)
        started = self._starts.get(tool.name)
        duration_ms = None
        if started:
            duration_ms = (time.perf_counter() - started.pop()) * 1000.0
        ok = self._looks_ok(result)
        self.calls.append(
            ToolCall(name=tool.name, category=category, duration_ms=duration_ms, ok=ok)
        )
        if self.live and duration_ms is not None:
            status = "" if ok else " [red](error)[/]"
            console.print(
                f"  {self._tag(category)} ✓ [dim]{tool.name} · {duration_ms:.0f}ms[/]{status}"
            )

    @staticmethod
    def _looks_ok(result: object) -> bool:
        """Best-effort success detection: tools return JSON with an "error" key on failure."""
        text = result if isinstance(result, str) else str(result)
        return '"error"' not in text

    # ---- reporting ----
    def counts(self) -> Counter:
        return Counter(c.category for c in self.calls)

    def summary_line(self) -> str:
        counts = self.counts()
        if not counts:
            return "no tools used"
        order = ["mcp", "web_search", "custom", "other"]
        parts = [
            f"{_CATEGORY_STYLE[cat][0]}×{counts[cat]}"
            for cat in order
            if counts.get(cat)
        ]
        return ", ".join(parts)

    def print_summary(self) -> None:
        if not self.live:
            return
        console.print(f"  [dim]tools used → {self.summary_line()}[/]")
