"""Provider-agnostic domain models.

Every object that crosses an adapter boundary is one of these Pydantic models.
Provider-specific request/response shapes never leak past the adapter boundary.
"""

from app.domain.models.chat import ChatMessage, Citation, LLMResponse, Role
from app.domain.models.chunk import Chunk, ChunkMetadata
from app.domain.models.document import (
    BoundingBox,
    ParsedDocument,
    TableBlock,
    TextBlock,
)
from app.domain.models.embedding import EmbeddingVector
from app.domain.models.retrieval import RetrievedChunk

__all__ = [
    "BoundingBox",
    "ChatMessage",
    "Chunk",
    "ChunkMetadata",
    "Citation",
    "EmbeddingVector",
    "LLMResponse",
    "ParsedDocument",
    "RetrievedChunk",
    "Role",
    "TableBlock",
    "TextBlock",
]
