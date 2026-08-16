"""Built-in agent tools: current time, calculator, web search."""
from __future__ import annotations

import ast
import math
import operator
from datetime import datetime, timezone

from .base import Tool
from ..config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
class GetCurrentTime(Tool):
    name = "get_current_time"
    label = "🕐 Current time"
    description = (
        "Get the current date and time. Use for questions about 'now', 'today', "
        "the current time, or the date. Optionally pass an IANA timezone."
    )
    parameters = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone, e.g. 'America/New_York', 'Asia/Kolkata'. Optional.",
            }
        },
    }

    async def run(self, timezone: str | None = None, **_) -> str:
        # Note: the 'timezone' parameter shadows datetime.timezone, so use _utc().
        now_utc = datetime.now(tz=_utc())
        if timezone:
            try:
                from zoneinfo import ZoneInfo
                local = now_utc.astimezone(ZoneInfo(timezone))
                return f"Current time in {timezone}: {local.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            except Exception:
                return (f"Unknown timezone '{timezone}'. "
                        f"Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        local = now_utc.astimezone()
        return (f"Current time — UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}; "
                f"server local: {local.strftime('%Y-%m-%d %H:%M:%S %Z')}")


def _utc():
    return timezone.utc


# ---------------------------------------------------------------------------
_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}
_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "floor": math.floor,
    "ceil": math.ceil, "log": math.log, "log10": math.log10, "exp": math.exp,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "pow": math.pow,
    "min": min, "max": max,
}


class Calculator(Tool):
    name = "calculator"
    label = "🧮 Calculator"
    description = (
        "Evaluate a mathematical expression. Use for any arithmetic or math the "
        "user asks about. Supports + - * / ** % //, parentheses, and functions "
        "like sqrt, log, sin, cos, min, max. Example: '(1234 * 5.5) / 3'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "The math expression to evaluate."}
        },
        "required": ["expression"],
    }

    async def run(self, expression: str = "", **_) -> str:
        try:
            result = _safe_eval(expression)
        except Exception as exc:  # noqa: BLE001
            return f"Could not evaluate '{expression}': {exc}"
        return f"{expression} = {result}"


def _safe_eval(expr: str):
    """Evaluate arithmetic safely via a restricted AST (no eval/builtins)."""
    node = ast.parse(expr, mode="eval").body
    return _eval_node(node)


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("only numbers allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        args = [_eval_node(a) for a in node.args]
        return _FUNCS[node.func.id](*args)
    raise ValueError("unsupported expression")


# ---------------------------------------------------------------------------
class WebSearch(Tool):
    name = "web_search"
    label = "🌐 Web search"
    description = (
        "Search the public web for current information not found in the user's "
        "documents (news, live facts, general knowledge). Returns titles, "
        "snippets and URLs."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The web search query."}
        },
        "required": ["query"],
    }

    async def run(self, query: str = "", **_) -> str:
        settings = get_settings()
        provider = settings.web_search_provider
        n = settings.web_search_results
        try:
            if provider == "tavily" and settings.tavily_api_key:
                results = await _tavily_search(query, n, settings.tavily_api_key)
            elif provider == "duckduckgo":
                results = await _ddg_search(query, n)
            else:
                return "Web search is disabled."
        except Exception as exc:  # noqa: BLE001
            log.warning("web_search failed: %s", exc)
            return f"Web search failed: {exc}"
        if not results:
            return f"No web results found for '{query}'."
        lines = [f"Web results for '{query}':"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   {r['url']}")
        return "\n".join(lines)


async def _ddg_search(query: str, n: int) -> list[dict]:
    """Keyless DuckDuckGo HTML endpoint, parsed leniently."""
    import re
    import html as html_lib
    import httpx

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; DocChat/1.0)"},
        )
        resp.raise_for_status()
        page = resp.text

    results: list[dict] = []
    # Each result: an anchor with class result__a (title+url) then result__snippet.
    for m in re.finditer(
        r'result__a[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
        r'result__snippet[^>]*>(?P<snippet>.*?)</a>',
        page, re.DOTALL,
    ):
        strip = lambda s: html_lib.unescape(re.sub(r"<[^>]+>", "", s)).strip()
        results.append({
            "title": strip(m.group("title")),
            "snippet": strip(m.group("snippet")),
            "url": html_lib.unescape(m.group("url")),
        })
        if len(results) >= n:
            break
    return results


async def _tavily_search(query: str, n: int, api_key: str) -> list[dict]:
    import httpx

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "max_results": n},
        )
        resp.raise_for_status()
        data = resp.json()
    return [
        {"title": r.get("title", ""), "snippet": r.get("content", ""), "url": r.get("url", "")}
        for r in data.get("results", [])
    ]
