"""FastAPI dependencies -> registry.

Routes depend on these, which depend on the registry factories -- never on a
concrete provider. Overriding a dependency in a test swaps the whole stack.
"""

from __future__ import annotations

from app.core.registry import (
    get_chunker,
    get_embedder,
    get_llm_provider,
    get_parser,
    get_reranker,
    get_retriever,
    get_storage,
    get_task_queue,
    get_vector_store,
)
from app.domain.interfaces import (
    Chunker,
    Embedder,
    LLMProvider,
    ObjectStorage,
    Parser,
    Reranker,
    Retriever,
    TaskQueue,
    VectorStore,
)


def llm_provider() -> LLMProvider:
    return get_llm_provider()


def embedder() -> Embedder:
    return get_embedder()


def vector_store() -> VectorStore:
    return get_vector_store()


def reranker() -> Reranker:
    return get_reranker()


def retriever() -> Retriever:
    return get_retriever()


def parser() -> Parser:
    return get_parser()


def chunker() -> Chunker:
    return get_chunker()


def storage() -> ObjectStorage:
    return get_storage()


def task_queue() -> TaskQueue:
    return get_task_queue()
