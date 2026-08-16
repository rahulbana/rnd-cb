"""The RAG retrieval pipeline exposed as an agent tool.

When the agent calls ``search_documents``, this runs embed → retrieve → rerank
over the user's uploaded documents and returns the top passages as context. The
passages are also stashed on ``last_sources`` so the agent can surface them as
citations in the UI.
"""
from __future__ import annotations

from .base import Tool
from ..config import get_settings
from ..embeddings import get_embedder
from ..rag.prompt import build_context_block, sources_payload
from ..reranking import get_reranker
from ..retrieval import get_retriever


class SearchDocuments(Tool):
    name = "search_documents"
    label = "📄 Search documents"
    description = (
        "Search the user's uploaded documents (PDF, Word, Excel, etc.) for "
        "relevant passages. Use this for any question that may be answered by "
        "the user's own files. Returns numbered passages you should cite as [n]."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for in the documents."}
        },
        "required": ["query"],
    }

    def __init__(self, options=None) -> None:
        self.options = options
        self.last_sources: list[dict] = []

    async def run(self, query: str = "", **_) -> str:
        import asyncio
        return await asyncio.to_thread(self._run_sync, query)

    def _run_sync(self, query: str) -> str:
        settings = get_settings()
        opts = self.options
        strategy = (opts and opts.retrieval_strategy) or settings.retrieval_strategy
        top_k = (opts and opts.top_k) or settings.retrieval_top_k
        final_k = (opts and opts.final_top_k) or settings.final_top_k

        embedder = get_embedder()
        qvec = embedder.embed_query(query)
        candidates = get_retriever(strategy).retrieve(query, top_k, qvec)
        if not candidates:
            self.last_sources = []
            return "No relevant passages found in the uploaded documents."

        rerank_on = settings.rerank_enabled if (opts is None or opts.rerank_enabled is None) \
            else opts.rerank_enabled
        if rerank_on:
            top = get_reranker(enabled=True,
                               models=(opts.rerank_models if opts else None)).rerank(
                query, candidates, top_k=final_k)
        else:
            top = candidates[:final_k]

        self.last_sources = sources_payload(top)
        return build_context_block(top)
