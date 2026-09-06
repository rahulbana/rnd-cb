"""Standalone /retrieve endpoint: strategy override, scoping, filters."""

from __future__ import annotations

from tests import fixtures

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _upload(client, name, data, ctype):
    return client.post("/api/v1/documents", files={"file": (name, data, ctype)})


def test_retrieve_default_and_strategies(upload_client):
    _upload(
        upload_client,
        "a.md",
        fixtures.make_markdown(body="alpha beta gamma"),
        "text/markdown",
    )
    for strategy in (None, "dense", "sparse", "hybrid"):
        params = {"q": "alpha beta gamma", "top_k": 3}
        if strategy:
            params["strategy"] = strategy
        resp = upload_client.post("/api/v1/retrieve", params=params)
        assert resp.status_code == 200, strategy
        body = resp.json()
        assert body["strategy"] == (strategy or "hybrid")
        assert body["hits"]


def test_retrieve_invalid_strategy_400(upload_client):
    resp = upload_client.post("/api/v1/retrieve", params={"q": "x", "strategy": "nope"})
    assert resp.status_code == 400


def test_retrieve_reflects_extracted_filters(upload_client):
    resp = upload_client.post(
        "/api/v1/retrieve", params={"q": "the pdf about revenue from 2023"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["filters"]["doc_type"] == "pdf"
    assert body["filters"]["year"] == 2023


def test_retrieve_doc_type_filter_scopes(upload_client):
    # A PDF and a markdown doc, both mentioning "budget".
    _upload(
        upload_client, "b.pdf", fixtures.make_pdf("the budget report"), "application/pdf"
    )
    _upload(
        upload_client,
        "b.md",
        fixtures.make_markdown(body="the budget notes"),
        "text/markdown",
    )
    resp = upload_client.post(
        "/api/v1/retrieve", params={"q": "pdf about the budget", "top_k": 5}
    )
    assert resp.status_code == 200
    hits = resp.json()["hits"]
    assert hits  # only the PDF is in scope
    assert all("budget" in h["text"] for h in hits)
