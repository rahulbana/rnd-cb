"""A minimal, readable Graph RAG implementation for learning.

Pipeline:
    text files -> chunks -> LLM entity/relation extraction -> NetworkX graph
    question -> entities -> graph traversal -> context -> LLM answer

Everything is graph-only (no vector store) so you can see exactly how the
knowledge graph drives retrieval.
"""

__all__ = [
    "config",
    "ingest",
    "extract",
    "graph_store",
    "retrieve",
    "answer",
]
