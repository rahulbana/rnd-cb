"""Web search tool with two depths: 'normal' and 'deep'.

* ``normal`` -- returns the titles, URLs and snippets of the top results.
* ``deep``   -- additionally fetches the top pages and extracts their main
  text so the model has the actual content to reason over.

Search is powered by DuckDuckGo's key-less HTML endpoint, so no API key is
required.
"""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from .base import Tool
from .http import get_text, post_text

_DDG_HTML = "https://html.duckduckgo.com/html/"
_MAX_PAGE_CHARS = 2000


def _clean_ddg_url(href: str) -> str:
    """DuckDuckGo wraps result links in a redirect -- unwrap it."""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [])
        if target:
            return unquote(target[0])
    return href


def _search(query: str, max_results: int) -> List[dict]:
    html = post_text(_DDG_HTML, data={"q": query})
    soup = BeautifulSoup(html, "html.parser")
    results: List[dict] = []
    for result in soup.select("div.result")[: max_results * 2]:
        link = result.select_one("a.result__a")
        if not link:
            continue
        snippet_el = result.select_one(".result__snippet")
        results.append(
            {
                "title": link.get_text(" ", strip=True),
                "url": _clean_ddg_url(link.get("href", "")),
                "snippet": snippet_el.get_text(" ", strip=True) if snippet_el else "",
            }
        )
        if len(results) >= max_results:
            break
    return results


def _extract_page_text(url: str) -> str:
    try:
        html = get_text(url)
    except Exception as exc:  # noqa: BLE001
        return f"(could not fetch page: {exc})"
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    return text[:_MAX_PAGE_CHARS] + ("..." if len(text) > _MAX_PAGE_CHARS else "")


def _web_search(query: str, depth: str = "normal", max_results: Optional[int] = None) -> str:
    depth = (depth or "normal").lower()
    if depth not in ("normal", "deep"):
        depth = "normal"

    limit = max_results or (3 if depth == "deep" else 5)
    results = _search(query, limit)
    if not results:
        return f"No web results found for {query!r}."

    lines = [f"Search results for {query!r} (depth={depth}):", ""]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   URL: {r['url']}")
        if r["snippet"]:
            lines.append(f"   Snippet: {r['snippet']}")
        if depth == "deep" and r["url"].startswith("http"):
            lines.append(f"   Page extract: {_extract_page_text(r['url'])}")
        lines.append("")

    return "\n".join(lines).strip()


SEARCH_TOOL = Tool(
    name="web_search",
    description=(
        "Search the web. Use depth='normal' for a quick search returning the "
        "top results with titles, URLs and snippets. Use depth='deep' for a "
        "more thorough search that also fetches and extracts the text of the "
        "top pages so you can read their actual content."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "depth": {
                "type": "string",
                "enum": ["normal", "deep"],
                "description": "'normal' for quick results, 'deep' to also read page content.",
            },
            "max_results": {
                "type": "integer",
                "description": "Optional cap on the number of results (default 5 normal / 3 deep).",
            },
        },
        "required": ["query"],
    },
    handler=_web_search,
)

TOOLS = [SEARCH_TOOL]
