"""The registry: resolves each PORT to an ADAPTER, driven by settings.

This is the *only* module allowed to import concrete adapters. Routes,
services, and workers depend on the ``get_*`` factories, never on a provider
class. A test can register a fake in the same registry and every consumer
becomes testable without a network call.

Adding a real provider later is a one-line registry entry -- no consumer
changes. Flipping one ``.env`` value swaps the implementation.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from app.adapters.chunkers import FakeChunker
from app.adapters.embedders import FakeEmbedder, FakeHashEmbedder
from app.adapters.llm_providers import FakeLLMProvider
from app.adapters.parsers import (
    DoclingParser,
    DocxParser,
    FakeParser,
    ParserRouter,
    PlainTextParser,
    PyMuPDFParser,
    TesseractImageParser,
    UnstructuredParser,
)
from app.adapters.rerankers import FakeReranker
from app.adapters.retrievers import FakeRetriever
from app.adapters.storage import FakeObjectStorage, LocalDiskStorage
from app.adapters.task_queues import FakeTaskQueue
from app.adapters.vector_stores import FakeVectorStore
from app.core.config import Settings, settings
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

# --- Registries: name -> adapter class ------------------------------------

_LLM_REGISTRY: dict[str, type[LLMProvider]] = {
    "fake": FakeLLMProvider,
}

_EMBEDDER_REGISTRY: dict[str, type[Embedder]] = {
    "fake": FakeEmbedder,
    "fake_hash": FakeHashEmbedder,
}

_VECTOR_STORE_REGISTRY: dict[str, type[VectorStore]] = {
    "fake": FakeVectorStore,
}

_RERANKER_REGISTRY: dict[str, type[Reranker]] = {
    "fake": FakeReranker,
}

_RETRIEVER_REGISTRY: dict[str, type[Retriever]] = {
    "fake": FakeRetriever,
}

_PARSER_REGISTRY: dict[str, type[Parser]] = {
    "fake": FakeParser,
    "plain": PlainTextParser,
    "pymupdf": PyMuPDFParser,
    "docx": DocxParser,
    "tesseract_image": TesseractImageParser,
    "docling": DoclingParser,
    "unstructured": UnstructuredParser,
    "router": ParserRouter,
}

_CHUNKER_REGISTRY: dict[str, type[Chunker]] = {
    "fake": FakeChunker,
}

_STORAGE_REGISTRY: dict[str, type[ObjectStorage]] = {
    "fake": FakeObjectStorage,
    "local_disk": LocalDiskStorage,
}

_TASK_QUEUE_REGISTRY: dict[str, type[TaskQueue]] = {
    "fake": FakeTaskQueue,
}


def _resolve(registry: Mapping[str, Any], key: str, kind: str, cfg: Settings) -> Any:
    try:
        cls = registry[key]
    except KeyError:
        available = ", ".join(sorted(registry)) or "(none)"
        raise ValueError(
            f"Unknown {kind} provider {key!r}. Available: {available}."
        ) from None
    return cls.from_settings(cfg)


# --- Factories: the single call sites every consumer depends on -----------


@lru_cache
def get_llm_provider() -> LLMProvider:
    return _resolve(_LLM_REGISTRY, settings.LLM_PROVIDER, "LLM", settings)


@lru_cache
def get_embedder() -> Embedder:
    return _resolve(_EMBEDDER_REGISTRY, settings.EMBEDDER_PROVIDER, "embedder", settings)


@lru_cache
def get_vector_store() -> VectorStore:
    return _resolve(
        _VECTOR_STORE_REGISTRY, settings.VECTOR_STORE_PROVIDER, "vector store", settings
    )


@lru_cache
def get_reranker() -> Reranker:
    return _resolve(_RERANKER_REGISTRY, settings.RERANKER_PROVIDER, "reranker", settings)


@lru_cache
def get_retriever() -> Retriever:
    return _resolve(
        _RETRIEVER_REGISTRY, settings.RETRIEVER_STRATEGY, "retriever", settings
    )


@lru_cache
def get_parser() -> Parser:
    return _resolve(_PARSER_REGISTRY, settings.PARSER_STRATEGY, "parser", settings)


def build_parser_chain(cfg: Settings) -> list[Parser]:
    """Instantiate the ordered parser fallback chain from ``PARSER_PRIORITY``.

    Names are resolved against the parser registry (excluding ``router`` to
    avoid recursion). Unknown names are a clear configuration error.
    """
    names = [n.strip() for n in cfg.PARSER_PRIORITY.split(",") if n.strip()]
    chain: list[Parser] = []
    for name in names:
        if name == "router":
            continue
        try:
            cls = _PARSER_REGISTRY[name]
        except KeyError:
            available = ", ".join(sorted(n for n in _PARSER_REGISTRY if n != "router"))
            raise ValueError(
                f"Unknown parser {name!r} in PARSER_PRIORITY. Available: {available}."
            ) from None
        chain.append(cls.from_settings(cfg))
    return chain


@lru_cache
def get_chunker() -> Chunker:
    return _resolve(_CHUNKER_REGISTRY, settings.CHUNKER_STRATEGY, "chunker", settings)


@lru_cache
def get_storage() -> ObjectStorage:
    return _resolve(_STORAGE_REGISTRY, settings.STORAGE_PROVIDER, "storage", settings)


@lru_cache
def get_task_queue() -> TaskQueue:
    return _resolve(
        _TASK_QUEUE_REGISTRY, settings.TASK_QUEUE_PROVIDER, "task queue", settings
    )


def clear_registry_caches() -> None:
    """Reset all cached factory instances.

    Used by tests that flip an env var at runtime and need the registry to
    re-resolve against fresh settings.
    """
    for factory in (
        get_llm_provider,
        get_embedder,
        get_vector_store,
        get_reranker,
        get_retriever,
        get_parser,
        get_chunker,
        get_storage,
        get_task_queue,
    ):
        factory.cache_clear()
