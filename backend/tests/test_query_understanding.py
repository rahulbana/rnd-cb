"""QueryProcessor: rewriting + metadata-filter extraction."""

from __future__ import annotations

from app.services.query_understanding import QueryProcessor


def test_extracts_year():
    plan = QueryProcessor().process("show invoices from 2023 please")
    assert plan.filters.year == 2023
    assert plan.filters.doc_type is None


def test_extracts_pdf_doc_type():
    plan = QueryProcessor().process("find the pdf about quarterly revenue")
    assert plan.filters.doc_type == "pdf"
    assert plan.filters.mime_prefixes == ("application/pdf",)


def test_extracts_word_doc_type():
    plan = QueryProcessor().process("word documents on the hiring policy")
    assert plan.filters.doc_type == "word"


def test_no_filters_for_plain_query():
    plan = QueryProcessor().process("what is the powerhouse of the cell")
    assert plan.filters.is_empty()


def test_normalizes_whitespace():
    plan = QueryProcessor().process("  spaced    out\tquery  ")
    assert plan.text == "spaced out query"
    assert plan.original == "  spaced    out\tquery  "
