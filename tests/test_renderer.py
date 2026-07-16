"""Tests for the Markdown rendering layer."""

from markdown_editor import renderer


def test_basic_formatting():
    r = renderer.render("# Title\n\nSome **bold** and *italic* text.")
    assert "<h1" in r.html
    assert "<strong>bold</strong>" in r.html
    assert "<em>italic</em>" in r.html


def test_tables_render():
    md = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    r = renderer.render(md)
    assert "<table>" in r.html
    assert "<td>1</td>" in r.html


def test_task_list():
    r = renderer.render("- [x] done\n- [ ] todo")
    assert "task-list-item" in r.html


def test_fenced_code_highlight():
    md = "```python\nprint('hi')\n```"
    r = renderer.render(md)
    assert 'class="highlight"' in r.html
    # Pygments token span for the builtin/keyword
    assert "<span" in r.html


def test_strikethrough_and_footnote():
    r = renderer.render("~~gone~~\n\nText[^1]\n\n[^1]: note")
    assert "<del>gone</del>" in r.html
    assert "footnote" in r.html


def test_toc_tokens_and_ids():
    r = renderer.render("# One\n\n## Two\n\n## Three")
    ids = [t["id"] for t in r.toc_tokens]
    assert "one" in ids
    # nested children present
    assert r.toc_tokens[0]["children"]
    assert 'id="one"' in r.html


def test_word_and_char_count_ignores_code():
    text = "one two three\n\n```\nignored code words here\n```"
    r = renderer.render(text)
    assert r.word_count == 3
    assert r.char_count == len(text)


def test_reading_time_minimum_one_for_short_text():
    r = renderer.render("hello world")
    assert r.reading_minutes == 1
    empty = renderer.render("")
    assert empty.reading_minutes == 0


def test_render_document_is_standalone():
    html = renderer.render_document("# Hello", title="My Doc")
    assert html.startswith("<!DOCTYPE html>")
    assert "<title>My Doc</title>" in html
    assert ".markdown-body" in html  # embedded CSS
    assert "<h1" in html


def test_render_document_escapes_title():
    html = renderer.render_document("x", title="<script>")
    assert "<title>&lt;script&gt;</title>" in html


def test_admonition_block():
    r = renderer.render('!!! note "Heads up"\n    Body text')
    assert "admonition" in r.html
