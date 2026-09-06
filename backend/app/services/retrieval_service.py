"""Retrieval orchestration (Phase 5): query understanding + scoped retrieval.

Retrieval is independent of generation so its quality can be measured on its
own. Query preprocessing extracts metadata filters (year, document type) which
are resolved to a document-id scope before the retriever runs. Reranking and
context assembly arrive in Phase 6.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Document
from app.domain.interfaces import Retriever
from app.domain.models import RetrievedChunk
from app.services.query_understanding import QueryFilters, QueryPlan, QueryProcessor

logger = get_logger("service.retrieval")


class RetrievalService:
    """Coordinates query understanding, scoping, and retrieval."""

    def __init__(
        self,
        retriever: Retriever,
        db: Session,
        processor: QueryProcessor | None = None,
    ) -> None:
        self._retriever = retriever
        self._db = db
        self._processor = processor or QueryProcessor()

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> tuple[list[RetrievedChunk], QueryPlan]:
        plan = self._processor.process(query)
        scope = self._resolve_scope(namespace, plan.filters, document_ids)

        results = await self._retriever.retrieve(
            plan.text, namespace=namespace, top_k=top_k, document_ids=scope
        )
        logger.info(
            "retrieved",
            retriever=self._retriever.name,
            namespace=namespace,
            top_k=top_k,
            year=plan.filters.year,
            doc_type=plan.filters.doc_type,
            scoped_docs=None if scope is None else len(scope),
            hits=len(results),
        )
        return results, plan

    def _resolve_scope(
        self,
        namespace: str,
        filters: QueryFilters,
        explicit: list[str] | None,
    ) -> list[str] | None:
        """Turn metadata filters into a document-id scope.

        Returns None for no scoping, or a (possibly empty) id list. An empty
        list means "filters matched nothing" -> retrieval returns nothing.
        """
        if filters.is_empty():
            return explicit

        stmt = select(Document).where(Document.org_id == namespace)
        if filters.mime_prefixes:
            stmt = stmt.where(
                or_(*(Document.mime_type.like(f"{p}%") for p in filters.mime_prefixes))
            )
        docs = list(self._db.execute(stmt).scalars().all())
        if filters.year is not None:
            docs = [d for d in docs if d.created_at and d.created_at.year == filters.year]

        matched = [d.id for d in docs]
        if explicit is not None:
            allowed = set(explicit)
            matched = [i for i in matched if i in allowed]
        return matched
