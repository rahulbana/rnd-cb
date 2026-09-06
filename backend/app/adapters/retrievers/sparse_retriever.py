"""Sparse (lexical) retriever -- BM25 over chunk text stored in Postgres.

BM25 complements dense retrieval: it nails exact terms, rare tokens, codes, and
names that embeddings can miss. The corpus is the ``chunks_meta.text`` column,
scoped by org namespace (and optionally by document). A Postgres full-text
variant can replace this behind the same port later.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import ChunkMeta, Document
from app.domain.models import Chunk, ChunkMetadata, RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class SparseRetriever:
    """BM25 lexical retrieval over chunk text in the relational store."""

    name = "sparse"

    @classmethod
    def from_settings(cls, settings: Settings) -> SparseRetriever:
        return cls()

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        from rank_bm25 import BM25Okapi  # lazy import

        rows = self._load_corpus(namespace, document_ids)
        if not rows:
            return []

        corpus_tokens = [_tokenize(r.text) for r in rows]
        bm25 = BM25Okapi(corpus_tokens)
        query_tokens = _tokenize(query)
        scores = bm25.get_scores(query_tokens)

        # Keep only chunks that actually share a query term. (BM25 scores can go
        # non-positive on tiny or uniform corpora due to negative IDF, so gate on
        # lexical overlap rather than score sign; rank by BM25.)
        query_set = set(query_tokens)
        ranked = sorted(
            zip(rows, corpus_tokens, scores, strict=True),
            key=lambda rcs: rcs[2],
            reverse=True,
        )
        results: list[RetrievedChunk] = []
        for row, tokens, score in ranked:
            if len(results) >= top_k:
                break
            if not query_set.intersection(tokens):
                continue
            results.append(
                RetrievedChunk(
                    chunk=Chunk(
                        id=row.vector_id,
                        text=row.text,
                        metadata=ChunkMetadata(
                            document_id=row.document_id,
                            page=row.page,
                            heading_path=row.heading_path,
                        ),
                    ),
                    score=float(score),
                    source="sparse",
                )
            )
        return results

    def _load_corpus(
        self, namespace: str, document_ids: list[str] | None
    ) -> list[ChunkMeta]:
        db = SessionLocal()
        try:
            stmt = (
                select(ChunkMeta)
                .join(Document, Document.id == ChunkMeta.document_id)
                .where(Document.org_id == namespace)
            )
            if document_ids is not None:
                stmt = stmt.where(ChunkMeta.document_id.in_(document_ids))
            return list(db.execute(stmt).scalars().all())
        finally:
            db.close()
