"""Extract HLS stream URLs and a title from a web page.

Given the HTML of a page that embeds an HLS video, this module locates the
``.m3u8`` URLs (including ones buried in escaped JSON/JS), pulls out a human
title, and turns that title into a safe filename.
"""

from __future__ import annotations

import html as _html
import re
import urllib.parse

# Absolute or protocol-relative .m3u8 URLs (stop at quotes/space/brackets).
_M3U8_ABS = re.compile(r'(?:https?:)?//[^\s"\'<>()\\]+?\.m3u8[^\s"\'<>()\\]*', re.I)
# Quoted root-relative paths: "/path/to/master.m3u8?token=..."
_M3U8_REL = re.compile(r'''["'](/[^"'<>()\\\s]+?\.m3u8[^"'<>()\\\s]*)["']''', re.I)

_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_OG_TITLE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
    re.I,
)
_OG_TITLE_REV = re.compile(
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:property|name)=["\']og:title["\']',
    re.I,
)

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_HEIGHT_RES = re.compile(r"(\d{3,4})x(\d{3,4})")
_HEIGHT_P = re.compile(r"(\d{3,4})\s*[pP](?:[^0-9a-zA-Z]|$)")


def _normalize(text: str) -> str:
    """Undo the common JS/JSON escapes that hide URLs from a plain regex."""
    return (
        text.replace("\\/", "/")
        .replace("\\u0026", "&")
        .replace("\\u003d", "=")
        .replace("\\u003D", "=")
    )


def find_m3u8_urls(html_text: str, base_url: str) -> list:
    """Return de-duplicated, absolute ``.m3u8`` URLs found in ``html_text``."""
    text = _html.unescape(_normalize(html_text))
    out: list = []
    seen: set = set()

    def add(candidate: str) -> None:
        absolute = urllib.parse.urljoin(base_url, candidate)
        if absolute not in seen:
            seen.add(absolute)
            out.append(absolute)

    for match in _M3U8_ABS.finditer(text):
        add(match.group(0))
    for match in _M3U8_REL.finditer(text):
        add(match.group(1))
    return out


def extract_title(html_text: str) -> str:
    """Best-effort page title, preferring ``og:title`` over ``<title>``."""
    for rx in (_OG_TITLE, _OG_TITLE_REV):
        match = rx.search(html_text)
        if match and match.group(1).strip():
            return _html.unescape(match.group(1)).strip()
    match = _TITLE.search(html_text)
    if match and match.group(1).strip():
        return _html.unescape(match.group(1)).strip()
    return ""


def sanitize_filename(name: str, default: str = "video", max_len: int = 150) -> str:
    """Turn an arbitrary title into a filesystem-safe base filename."""
    name = _html.unescape(name or "").strip()
    name = _ILLEGAL.sub("", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or default


def height_hint_from_url(url: str) -> int:
    """Guess a vertical resolution from a URL (e.g. ``1080P`` or ``1920x1080``).

    Used to rank stream candidates that are plain media playlists (no master
    playlist to read a RESOLUTION from).
    """
    match = _HEIGHT_RES.search(url)
    if match:
        return int(match.group(2))
    match = _HEIGHT_P.search(url)
    if match:
        return int(match.group(1))
    return 0
