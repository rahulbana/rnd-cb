"""Summarize a web page given its URL.

Fetches the page, strips boilerplate (scripts, nav, footers, ...) and returns
the title plus the main readable text. The agent then produces the actual
summary from that content.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from .base import Tool
from .http import get_text

# How much page text to hand back to the model (characters).
_MAX_CHARS = 6000


def extract_readable(html: str, max_chars: int = _MAX_CHARS) -> tuple[str, str]:
    """Return ``(title, main_text)`` extracted from raw ``html``."""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    for tag in soup(
        ["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]
    ):
        tag.decompose()

    # Prefer the <article> / <main> region when a page exposes one.
    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = " ".join(main.get_text(" ", strip=True).split())
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return title, text


def _summarize_webpage(url: str) -> str:
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url

    html = get_text(url)
    title, text = extract_readable(html)
    if not text:
        return f"Could not extract readable text from {url}."

    header = f"Page title: {title}\n" if title else ""
    return (
        f"{header}URL: {url}\n"
        f"Extracted content (summarize this for the user):\n\n{text}"
    )


WEBPAGE_TOOL = Tool(
    name="summarize_webpage",
    description=(
        "Fetch a web page by URL and return its title and main readable text so "
        "you can summarize it for the user. Use this when the user gives a link "
        "and asks what it says or to summarize it."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full URL of the web page to summarize.",
            }
        },
        "required": ["url"],
    },
    handler=_summarize_webpage,
)

TOOLS = [WEBPAGE_TOOL]
