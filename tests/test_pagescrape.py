"""Tests for web-page scraping helpers (no network)."""

from m3u8_downloader.pagescrape import (
    extract_title,
    find_m3u8_urls,
    height_hint_from_url,
    sanitize_filename,
)

BASE = "https://site.example/watch?v=abc"


def test_find_plain_absolute_url():
    html = '<video><source src="https://cdn.example/a/master.m3u8?t=1"></video>'
    assert find_m3u8_urls(html, BASE) == ["https://cdn.example/a/master.m3u8?t=1"]


def test_find_escaped_json_url():
    # URL as it appears inside an embedded JSON/JS blob
    html = r'{"hls":"https:\/\/cdn.example\/v\/master.m3u8?token=x&q=2"}'
    assert find_m3u8_urls(html, BASE) == [
        "https://cdn.example/v/master.m3u8?token=x&q=2"
    ]


def test_find_protocol_relative_and_root_relative():
    html = (
        'a="//cdn.example/x/stream.m3u8" '
        "b='/local/path/index.m3u8?s=1'"
    )
    urls = find_m3u8_urls(html, BASE)
    assert "https://cdn.example/x/stream.m3u8" in urls
    assert "https://site.example/local/path/index.m3u8?s=1" in urls


def test_dedupe_preserves_order():
    html = "u1=//c/a.m3u8 u2=//c/a.m3u8 u3=//c/b.m3u8"
    assert find_m3u8_urls(html, BASE) == ["https://c/a.m3u8", "https://c/b.m3u8"]


def test_extract_title_prefers_og_title():
    html = (
        "<title>My Video - SomeSite</title>"
        '<meta property="og:title" content="My Awesome Video &amp; More">'
    )
    assert extract_title(html) == "My Awesome Video & More"


def test_extract_title_falls_back_to_title_tag():
    assert extract_title("<title>Just A Title</title>") == "Just A Title"


def test_sanitize_filename_strips_illegal_chars():
    assert sanitize_filename('My: Video / "Clip" ?') == "My Video Clip"
    assert sanitize_filename("   ") == "video"
    assert sanitize_filename("", default="fallback") == "fallback"


def test_height_hint_from_url():
    assert height_hint_from_url("https://c/1080P_4000K_123.mp4/master.m3u8") == 1080
    assert height_hint_from_url("https://c/v/1920x1080/index.m3u8") == 1080
    assert height_hint_from_url("https://c/v/index.m3u8") == 0
