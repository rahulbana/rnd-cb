"""Dense vector retrieval: embed the query, nearest-neighbour search."""
from __future__ import annotations

from .base import BaseRetriever, RetrievedChunk
from ..embeddings import get_embedder
from ..vectorstore import get_vectorstore


class SimpleRetriever(BaseRetriever):
    name = "simple"

    def retrieve(self, query: str, top_k: int,
                 query_embedding: list[float] | None = None) -> list[RetrievedChunk]:
        store = get_vectorstore()
        qvec = query_embedding if query_embedding is not None else get_embedder().embed_query(query)
        results = store.query(qvec, top_k=top_k)
        return [
            RetrievedChunk(id=r.id, text=r.text, metadata=r.metadata,
                           score=r.score, scores={"vector": r.score})
            for r in results
        ]
