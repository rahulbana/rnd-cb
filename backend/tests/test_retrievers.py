"""Dense / sparse / hybrid retriever behavior over an ingested corpus."""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.registry import get_retriever_by_name
from tests import fixtures


def _upload(client, name, body):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, fixtures.make_markdown(body=body), "text/markdown")},
    )


def _ingest(client, docs: dict[str, str]) -> dict[str, str]:
    ids = {}
    for name, body in docs.items():
        resp = _upload(client, f"{name}.md", body)
        assert resp.status_code == 202
        assert resp.json()["job"]["status"] == "completed"
        ids[name] = resp.json()["document"]["id"]
    return ids


def test_sparse_finds_exact_term_match(upload_client):
    ids = _ingest(
        upload_client,
        {
            "fin": "annual financial report revenue growth in emerging markets",
            "ml": "machine learning models require large training datasets",
            "bio": "the mitochondria is the powerhouse of the cell",
        },
    )
    sparse = get_retriever_by_name("sparse")
    hits = asyncio.run(
        sparse.retrieve("training datasets", namespace=settings.DEFAULT_ORG_ID, top_k=3)
    )
    assert hits
    assert hits[0].chunk.metadata.document_id == ids["ml"]
    assert hits[0].source == "sparse"


def test_hybrid_fuses_and_tags_source(upload_client):
    _ingest(
        upload_client,
        {
            "a": "quarterly revenue grew twenty percent year over year",
            "b": "the neural network was trained on labeled images",
        },
    )
    hybrid = get_retriever_by_name("hybrid")
    hits = asyncio.run(
        hybrid.retrieve(
            "quarterly revenue grew", namespace=settings.DEFAULT_ORG_ID, top_k=2
        )
    )
    assert hits
    assert all(h.source == "hybrid" for h in hits)


def test_document_scoping(upload_client):
    ids = _ingest(
        upload_client,
        {
            "x": "alpha content about topic one",
            "y": "alpha content about topic two",
        },
    )
    sparse = get_retriever_by_name("sparse")
    hits = asyncio.run(
        sparse.retrieve(
            "alpha content",
            namespace=settings.DEFAULT_ORG_ID,
            top_k=5,
            document_ids=[ids["x"]],
        )
    )
    assert hits
    assert all(h.chunk.metadata.document_id == ids["x"] for h in hits)
