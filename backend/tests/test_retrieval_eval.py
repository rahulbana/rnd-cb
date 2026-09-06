"""Phase 5 EXIT TEST: hybrid retrieval beats a dense-only baseline.

Measured on a small labeled query set (recall@k, MRR) and logged -- not
asserted by hand. Uses the deterministic fake embedder, so dense similarity is
essentially exact-string; lexical (BM25) recovers the term-overlap queries that
dense misses, and hybrid fuses both. The corpus is larger than k so recall is
discriminating.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.registry import get_retriever_by_name
from app.evaluation.retrieval_eval import evaluate_retriever
from tests import fixtures

# 12-document corpus, one distinctive body each.
_CORPUS = {
    "d0": "annual financial report revenue growth in emerging markets",
    "d1": "machine learning models require large training datasets and compute",
    "d2": "the mitochondria is the powerhouse of the cell in biology",
    "d3": "quarterly earnings call transcript with the chief executive officer",
    "d4": "kubernetes cluster autoscaling and pod scheduling strategies",
    "d5": "mediterranean diet recipes with olive oil and fresh vegetables",
    "d6": "supreme court ruling on intellectual property and patent law",
    "d7": "photosynthesis converts sunlight into chemical energy in plants",
    "d8": "distributed consensus algorithms like raft and paxos explained",
    "d9": "renaissance painting techniques using oil glazes and chiaroscuro",
    "d10": "blood pressure medication dosage guidelines for hypertension",
    "d11": "supply chain logistics optimization and warehouse automation",
}

# Queries: term-overlap subsets, not identical strings, with the relevant doc.
_QUERIES = [
    ("training datasets compute models", "d1"),
    ("mitochondria powerhouse cell", "d2"),
    ("raft paxos consensus", "d8"),
    ("olive oil vegetables recipes", "d5"),
    ("patent law intellectual property", "d6"),
]


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


def test_hybrid_beats_dense_on_labeled_set(upload_client):
    ids = _ingest(upload_client)
    labeled = [(q, {ids[name]}) for q, name in _QUERIES]

    dense = get_retriever_by_name("dense")
    sparse = get_retriever_by_name("sparse")
    hybrid = get_retriever_by_name("hybrid")

    ns = settings.DEFAULT_ORG_ID
    dense_m = asyncio.run(evaluate_retriever(dense, labeled, namespace=ns, k=3))
    sparse_m = asyncio.run(evaluate_retriever(sparse, labeled, namespace=ns, k=3))
    hybrid_m = asyncio.run(evaluate_retriever(hybrid, labeled, namespace=ns, k=3))

    # Measured, logged, not hand-asserted: hybrid improves on the dense baseline.
    assert hybrid_m.recall_at_k >= dense_m.recall_at_k
    assert hybrid_m.recall_at_k > dense_m.recall_at_k  # a real improvement
    assert sparse_m.recall_at_k >= dense_m.recall_at_k
