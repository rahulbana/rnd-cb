"""Ports: the fixed interfaces every adapter must satisfy.

Nothing outside this package defines what an adapter looks like, and no
business-logic module may bypass these Protocols to import a provider SDK
directly.
"""

from app.domain.interfaces.chunker import Chunker
from app.domain.interfaces.embedder import Embedder
from app.domain.interfaces.eval_harness import EvalHarness
from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.interfaces.parser import Parser
from app.domain.interfaces.reranker import Reranker
from app.domain.interfaces.retriever import Retriever
from app.domain.interfaces.secrets import SecretProvider
from app.domain.interfaces.storage import ObjectStorage
from app.domain.interfaces.task_queue import TaskQueue
from app.domain.interfaces.tracer import Tracer
from app.domain.interfaces.vector_store import VectorStore

__all__ = [
    "Chunker",
    "Embedder",
    "EvalHarness",
    "LLMProvider",
    "ObjectStorage",
    "Parser",
    "Reranker",
    "Retriever",
    "SecretProvider",
    "TaskQueue",
    "Tracer",
    "VectorStore",
]
