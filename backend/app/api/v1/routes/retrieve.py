"""Standalone retrieval endpoint (retrieval without generation).

Lets retrieval quality be exercised and measured on its own, and the strategy
(dense / sparse / hybrid) chosen per request for comparison.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.schemas import RetrieveFilters, RetrieveHit, RetrieveResponse
from app.core.config import settings
from app.core.registry import get_reranker, get_retriever, get_retriever_by_name
from app.db.base import get_db
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["retrieval"])


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(
    q: str,
    top_k: int = 5,
    strategy: str | None = None,
    rerank: bool = False,
    document_ids: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RetrieveResponse:
    """Retrieve candidate chunks for a query.

    ``strategy`` overrides the configured retriever (dense | sparse | hybrid);
    ``rerank`` re-scores an over-fetched candidate set with the configured
    reranker; ``document_ids`` scopes retrieval to specific documents.
    """
    try:
        retriever = get_retriever_by_name(strategy) if strategy else get_retriever()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = RetrievalService(retriever, db)
    fetch_k = settings.RERANK_FETCH_K if rerank else top_k
    results, plan = await service.retrieve(
        q,
        namespace=settings.DEFAULT_ORG_ID,
        top_k=fetch_k,
        document_ids=document_ids,
    )
    strategy_name = retriever.name
    if rerank:
        reranker = get_reranker()
        results = await reranker.rerank(plan.text, results, top_k=top_k)
        strategy_name = f"{retriever.name}+{reranker.name}"

    return RetrieveResponse(
        query=q,
        strategy=strategy_name,
        filters=RetrieveFilters(year=plan.filters.year, doc_type=plan.filters.doc_type),
        hits=[
            RetrieveHit(
                chunk_id=h.chunk.id,
                document_id=h.chunk.metadata.document_id,
                text=h.chunk.text,
                score=h.score,
                source=h.source,
                page=h.chunk.metadata.page,
                heading_path=h.chunk.metadata.heading_path,
            )
            for h in results
        ],
    )
