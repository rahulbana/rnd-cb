"""Dense vector retrieval: embed the query, nearest-neighbour search."""
from __future__ import annotations

from .base import BaseRetriever, RetrievedChunk
from ..embeddings import get_embedder
from ..vectorstore import get_vectorstore


class SimpleRetriever(BaseRetriever):
    name = "simple"

    def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        embedder = get_embedder()
        store = get_vectorstore()
        qvec = embedder.embed_query(query)
        results = store.query(qvec, top_k=top_k)
        return [
            RetrievedChunk(id=r.id, text=r.text, metadata=r.metadata,
                           score=r.score, scores={"vector": r.score})
            for r in results
        ]
