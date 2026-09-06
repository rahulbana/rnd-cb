"""Retriever port -- dense, sparse, or hybrid candidate retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.domain.models import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class Retriever(Protocol):
    """Any retrieval strategy must satisfy this."""

    name: str  # "dense" | "sparse" | "hybrid" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> Retriever:
        """Construct the adapter from application settings."""
        ...

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Return candidate chunks for a query within a namespace.

        ``document_ids``, when given, scopes retrieval to those documents
        (per-document / per-collection scoping).
        """
        ...
