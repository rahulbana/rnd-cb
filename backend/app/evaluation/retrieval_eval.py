"""Retrieval evaluation harness.

Measures a retriever against a small labeled query set: recall@k and MRR. Used
to compare strategies (e.g. hybrid vs dense-only) with numbers, not assertions.
The RAGAS/DeepEval answer-quality suite lands in Phase 9; this scores retrieval
in isolation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.domain.interfaces import Retriever

if TYPE_CHECKING:
    from app.domain.interfaces import Reranker

logger = get_logger("eval.retrieval")

# (query, set of relevant document ids)
LabeledQuery = tuple[str, set[str]]


@dataclass
class RetrievalMetrics:
    strategy: str
    recall_at_k: float
    precision_at_k: float
    mrr: float
    k: int


async def evaluate_retriever(
    retriever: Retriever,
    labeled: Sequence[LabeledQuery],
    *,
    namespace: str,
    k: int = 5,
    reranker: Reranker | None = None,
    fetch_k: int | None = None,
) -> RetrievalMetrics:
    """Compute mean recall@k, precision@k and MRR over ``labeled``.

    When ``reranker`` is given, ``fetch_k`` candidates are retrieved and reranked
    down to ``k`` -- so a reranked pipeline can be compared to the raw retriever.
    """
    recall_sum = 0.0
    precision_sum = 0.0
    rr_sum = 0.0
    strategy = retriever.name

    for query, relevant in labeled:
        candidates = await retriever.retrieve(
            query, namespace=namespace, top_k=fetch_k or k
        )
        if reranker is not None:
            candidates = await reranker.rerank(query, candidates, top_k=k)
            strategy = f"{retriever.name}+{reranker.name}"

        retrieved = [h.chunk.metadata.document_id for h in candidates][:k]

        relevant_found = [d for d in retrieved if d in relevant]
        if relevant:
            recall_sum += len(set(relevant_found)) / len(relevant)
        precision_sum += len(relevant_found) / k

        for rank, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant:
                rr_sum += 1.0 / rank
                break

    n = max(len(labeled), 1)
    metrics = RetrievalMetrics(
        strategy=strategy,
        recall_at_k=recall_sum / n,
        precision_at_k=precision_sum / n,
        mrr=rr_sum / n,
        k=k,
    )
    logger.info(
        "retrieval_eval",
        strategy=metrics.strategy,
        recall_at_k=round(metrics.recall_at_k, 4),
        precision_at_k=round(metrics.precision_at_k, 4),
        mrr=round(metrics.mrr, 4),
        k=k,
        queries=len(labeled),
    )
    return metrics
