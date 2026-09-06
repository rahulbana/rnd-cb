"""Chunker strategy tests."""

from __future__ import annotations

from app.adapters.chunkers import (
    FixedSizeChunker,
    RecursiveChunker,
    StructureAwareChunker,
)
from app.adapters.chunkers._textsplit import char_windows, recursive_split
from app.domain.models import ParsedDocument, TableBlock, TextBlock


def _doc() -> ParsedDocument:
    return ParsedDocument(
        source_filename="d.md",
        mime_type="text/markdown",
        text_blocks=[
            TextBlock(text="Introduction", page=1, heading_path="Introduction"),
            TextBlock(text="alpha beta gamma", page=1, heading_path="Introduction"),
            TextBlock(text="Methods", page=2, heading_path="Methods"),
            TextBlock(text="delta epsilon zeta", page=2, heading_path="Methods"),
        ],
        tables=[TableBlock(rows=[["a", "b"], ["1", "2"]], page=3, caption="T1")],
        page_count=3,
    )


def test_char_windows_overlap():
    windows = char_windows("abcdefghij", size=4, overlap=1)
    assert windows[0] == "abcd"
    # step = size - overlap = 3
    assert windows[1] == "defg"


def test_recursive_split_respects_size():
    text = "para one.\n\npara two is a bit longer.\n\npara three."
    pieces = recursive_split(text, size=20, overlap=5)
    assert all(len(p) <= 20 for p in pieces)
    assert "".join(pieces).replace(" ", "") != ""


def test_structure_aware_groups_by_heading_and_keeps_tables():
    chunks = StructureAwareChunker(size=800, overlap=100).chunk(
        _doc(), document_id="doc1"
    )
    # One chunk per heading group + one for the table.
    headings = [c.metadata.heading_path for c in chunks]
    assert "Introduction" in headings
    assert "Methods" in headings
    assert any("a | b" in c.text for c in chunks)  # table serialized
    # Provenance preserved.
    intro = next(c for c in chunks if c.metadata.heading_path == "Introduction")
    assert intro.metadata.page == 1
    assert intro.metadata.document_id == "doc1"
    # Ids are ordinal-stable.
    assert chunks[0].id == "doc1:0"


def test_structure_aware_splits_oversized_group():
    big = TextBlock(text="word " * 400, page=1, heading_path="Big")
    doc = ParsedDocument(
        source_filename="d.txt", mime_type="text/plain", text_blocks=[big]
    )
    chunks = StructureAwareChunker(size=200, overlap=20).chunk(doc, document_id="d")
    assert len(chunks) > 1
    assert all(len(c.text) <= 200 for c in chunks)


def test_fixed_size_chunker():
    doc = ParsedDocument(
        source_filename="d.txt",
        mime_type="text/plain",
        text_blocks=[TextBlock(text="x" * 1000, page=1)],
    )
    chunks = FixedSizeChunker(size=300, overlap=50).chunk(doc, document_id="d")
    assert len(chunks) > 1
    assert all(len(c.text) <= 300 for c in chunks)


def test_recursive_chunker():
    doc = ParsedDocument(
        source_filename="d.txt",
        mime_type="text/plain",
        text_blocks=[TextBlock(text="sentence. " * 100, page=1)],
    )
    chunks = RecursiveChunker(size=120, overlap=20).chunk(doc, document_id="d")
    assert len(chunks) > 1
    assert all(len(c.text) <= 120 for c in chunks)
    assert all(c.metadata.document_id == "d" for c in chunks)
