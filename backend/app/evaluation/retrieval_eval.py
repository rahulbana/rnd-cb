"""Retrieval evaluation harness.

Measures a retriever against a small labeled query set: recall@k and MRR. Used
to compare strategies (e.g. hybrid vs dense-only) with numbers, not assertions.
The RAGAS/DeepEval answer-quality suite lands in Phase 9; this scores retrieval
in isolation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.core.logging import get_logger
from app.domain.interfaces import Retriever

logger = get_logger("eval.retrieval")

# (query, set of relevant document ids)
LabeledQuery = tuple[str, set[str]]


@dataclass
class RetrievalMetrics:
    strategy: str
    recall_at_k: float
    mrr: float
    k: int


async def evaluate_retriever(
    retriever: Retriever,
    labeled: Sequence[LabeledQuery],
    *,
    namespace: str,
    k: int = 5,
) -> RetrievalMetrics:
    """Compute mean recall@k and MRR for ``retriever`` over ``labeled``."""
    recall_sum = 0.0
    rr_sum = 0.0
    for query, relevant in labeled:
        hits = await retriever.retrieve(query, namespace=namespace, top_k=k)
        retrieved = [h.chunk.metadata.document_id for h in hits][:k]

        if relevant:
            found = relevant & set(retrieved)
            recall_sum += len(found) / len(relevant)

        for rank, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant:
                rr_sum += 1.0 / rank
                break

    n = max(len(labeled), 1)
    metrics = RetrievalMetrics(
        strategy=retriever.name,
        recall_at_k=recall_sum / n,
        mrr=rr_sum / n,
        k=k,
    )
    logger.info(
        "retrieval_eval",
        strategy=metrics.strategy,
        recall_at_k=round(metrics.recall_at_k, 4),
        mrr=round(metrics.mrr, 4),
        k=k,
        queries=len(labeled),
    )
    return metrics
