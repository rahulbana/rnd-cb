"""Markdown-to-HTML rendering.

A thin, well-configured wrapper around `python-markdown` that turns editor
content into the HTML shown in the live preview and in exported files.

The renderer enables a GitHub-flavoured feature set:

* fenced code blocks with syntax highlighting (Pygments)
* tables, definition lists and abbreviations
* task lists (``- [ ]`` / ``- [x]``)
* footnotes
* auto-generated header anchors and a table of contents
* smart typography, strike-through, subscript/superscript
* admonition/"callout" blocks

The public surface is intentionally tiny: :func:`render` for a body fragment
and :func:`render_document` for a full, standalone HTML page (used by export).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

import markdown
from markdown.extensions.toc import TocExtension

# Extensions that ship with python-markdown or pymdown-extensions.  Kept as a
# module-level constant so tests can assert the exact feature set.
_EXTENSIONS = [
    "markdown.extensions.extra",          # tables, fenced_code, footnotes, abbr, attr_list, def_list
    "markdown.extensions.sane_lists",
    "markdown.extensions.smarty",         # smart quotes / dashes / ellipses
    "markdown.extensions.admonition",
    "markdown.extensions.nl2br",
    "pymdownx.tasklist",
    "pymdownx.tilde",                     # ~~strike~~ and ~sub~
    "pymdownx.caret",                     # ^sup^ and ^^insert^^
    "pymdownx.superfences",               # nestable fenced code
    "pymdownx.highlight",
    "pymdownx.magiclink",                 # bare URLs become links
    TocExtension(permalink=True, baselevel=1, toc_depth="1-6"),
]

_EXTENSION_CONFIGS = {
    "pymdownx.tasklist": {"custom_checkbox": True, "clickable_checkbox": False},
    "pymdownx.highlight": {
        "use_pygments": True,
        "guess_lang": False,
        "css_class": "highlight",
        "pygments_style": "default",
    },
    "pymdownx.superfences": {},
}


@dataclass
class RenderResult:
    """The rendered output plus derived metadata used by the UI."""

    html: str
    toc: str = ""
    toc_tokens: List[dict] = field(default_factory=list)
    word_count: int = 0
    char_count: int = 0
    reading_minutes: int = 0


# A single Markdown instance is *not* thread-safe, so we create one per call.
# python-markdown is cheap to instantiate and this keeps rendering re-entrant
# for concurrent requests without a lock.
def _make_parser() -> markdown.Markdown:
    return markdown.Markdown(
        extensions=_EXTENSIONS,
        extension_configs=_EXTENSION_CONFIGS,
        output_format="html5",
        tab_length=4,
    )


_WORD_RE = re.compile(r"[A-Za-z0-9_À-￿]+")
# Strip fenced/indented code and inline code so counts reflect prose, not code.
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


def count_words(text: str) -> int:
    """Return an approximate prose word count, ignoring code spans."""
    prose = _FENCE_RE.sub(" ", text)
    prose = _INLINE_CODE_RE.sub(" ", prose)
    return len(_WORD_RE.findall(prose))


def render(text: str, *, words_per_minute: int = 200) -> RenderResult:
    """Render a Markdown *body* fragment to HTML with metadata.

    The returned :class:`RenderResult` carries the HTML for the preview pane,
    an HTML table-of-contents, the structured TOC tokens (for the outline
    sidebar) and simple document statistics.
    """
    parser = _make_parser()
    html = parser.convert(text or "")

    toc = getattr(parser, "toc", "") or ""
    toc_tokens = getattr(parser, "toc_tokens", []) or []

    words = count_words(text or "")
    reading = max(1, round(words / words_per_minute)) if words else 0

    return RenderResult(
        html=html,
        toc=toc,
        toc_tokens=toc_tokens,
        word_count=words,
        char_count=len(text or ""),
        reading_minutes=reading,
    )


def pygments_css(style: str = "default") -> str:
    """Return the Pygments stylesheet for the ``.highlight`` code blocks."""
    from pygments.formatters import HtmlFormatter

    return HtmlFormatter(style=style).get_style_defs(".highlight")


# Minimal, self-contained page shell for exported documents.  It embeds a
# readable stylesheet plus the Pygments rules so the file renders identically
# outside the app, with no network access required.
_EXPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{base_css}
{pygments_css}
</style>
</head>
<body>
<article class="markdown-body">
{body}
</article>
</body>
</html>
"""

_EXPORT_BASE_CSS = """
:root { color-scheme: light dark; }
body { margin: 0; background: #ffffff; color: #1f2328; }
.markdown-body {
  max-width: 820px; margin: 0 auto; padding: 48px 24px;
  font: 16px/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  word-wrap: break-word;
}
.markdown-body h1, .markdown-body h2 { border-bottom: 1px solid #d0d7de; padding-bottom: .3em; }
.markdown-body h1, .markdown-body h2, .markdown-body h3,
.markdown-body h4, .markdown-body h5, .markdown-body h6 {
  margin: 1.4em 0 .6em; font-weight: 600; line-height: 1.25;
}
.markdown-body a { color: #0969da; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body code {
  background: rgba(175,184,193,.2); padding: .2em .4em; border-radius: 6px;
  font: .9em/1.4 ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}
.markdown-body pre {
  background: #f6f8fa; padding: 16px; border-radius: 8px; overflow: auto;
}
.markdown-body pre code { background: none; padding: 0; }
.markdown-body blockquote {
  margin: 0 0 16px; padding: 0 1em; color: #656d76; border-left: .25em solid #d0d7de;
}
.markdown-body table { border-collapse: collapse; margin: 0 0 16px; display: block; overflow: auto; }
.markdown-body th, .markdown-body td { border: 1px solid #d0d7de; padding: 6px 13px; }
.markdown-body tr:nth-child(2n) { background: #f6f8fa; }
.markdown-body img { max-width: 100%; }
.markdown-body hr { height: .25em; background: #d0d7de; border: 0; margin: 24px 0; }
.markdown-body .admonition {
  border: 1px solid #d0d7de; border-left: .25em solid #0969da;
  border-radius: 6px; padding: 8px 16px; margin: 0 0 16px;
}
.markdown-body .admonition-title { font-weight: 600; margin: .3em 0; }
.markdown-body .task-list-item { list-style: none; }
.markdown-body .task-list-item input { margin: 0 .5em 0 -1.4em; }
@media (prefers-color-scheme: dark) {
  body { background: #0d1117; color: #e6edf3; }
  .markdown-body h1, .markdown-body h2 { border-bottom-color: #30363d; }
  .markdown-body a { color: #4493f8; }
  .markdown-body pre { background: #161b22; }
  .markdown-body blockquote { color: #9198a1; border-left-color: #30363d; }
  .markdown-body th, .markdown-body td { border-color: #30363d; }
  .markdown-body tr:nth-child(2n) { background: #161b22; }
  .markdown-body hr { background: #30363d; }
}
"""


def render_document(text: str, *, title: str = "Document", style: str = "default") -> str:
    """Render Markdown to a complete, standalone, styled HTML page."""
    result = render(text)
    return _EXPORT_TEMPLATE.format(
        title=_escape(title),
        base_css=_EXPORT_BASE_CSS,
        pygments_css=pygments_css(style),
        body=result.html,
    )


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
