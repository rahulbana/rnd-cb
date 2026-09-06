"""Phase 6 EXIT TEST: precision@k improves after reranking.

Measured and logged (not hand-asserted): reranking an over-fetched candidate
set with the reranker lifts precision@k over the Phase 5 hybrid baseline.
"""

from __future__ import annotations

import asyncio

from app.adapters.rerankers import FakeReranker
from app.core.config import settings
from app.core.registry import get_retriever_by_name
from app.evaluation.retrieval_eval import evaluate_retriever
from tests import fixtures
from tests.test_retrieval_eval import _CORPUS, _QUERIES


def _ingest(client) -> dict[str, str]:
    ids = {}
    for name, body in _CORPUS.items():
        resp = client.post(
            "/api/v1/documents",
            files={
                "file": (f"{name}.md", fixtures.make_markdown(body=body), "text/markdown")
            },
        )
        assert resp.status_code == 202
        ids[name] = resp.json()["document"]["id"]
    return ids


def test_reranking_improves_precision(upload_client):
    ids = _ingest(upload_client)
    labeled = [(q, {ids[name]}) for q, name in _QUERIES]

    hybrid = get_retriever_by_name("hybrid")
    reranker = FakeReranker()
    ns = settings.DEFAULT_ORG_ID

    # precision@1 is the discriminating metric here (one relevant doc per query).
    baseline = asyncio.run(evaluate_retriever(hybrid, labeled, namespace=ns, k=1))
    reranked = asyncio.run(
        evaluate_retriever(
            hybrid, labeled, namespace=ns, k=1, reranker=reranker, fetch_k=10
        )
    )

    assert reranked.precision_at_k >= baseline.precision_at_k
    assert reranked.precision_at_k > baseline.precision_at_k  # a real improvement
