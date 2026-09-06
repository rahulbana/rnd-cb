"""Embedder adapters."""

from app.adapters.embedders.fake_embedder import FakeEmbedder, FakeHashEmbedder
from app.adapters.embedders.openai_embedder import OpenAIEmbedder
from app.adapters.embedders.sentence_transformers_embedder import (
    SentenceTransformersEmbedder,
)

__all__ = [
    "FakeEmbedder",
    "FakeHashEmbedder",
    "OpenAIEmbedder",
    "SentenceTransformersEmbedder",
]
