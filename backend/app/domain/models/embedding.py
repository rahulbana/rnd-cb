"""Embedding domain model."""

from __future__ import annotations

from pydantic import BaseModel


class EmbeddingVector(BaseModel):
    """A dense vector plus the model that produced it.

    ``dim`` is tracked explicitly so the registry can detect embedding
    dimension drift when providers are swapped (see the reindex runbook).
    """

    values: list[float]
    model: str
    dim: int

    @classmethod
    def of(cls, values: list[float], model: str) -> EmbeddingVector:
        return cls(values=values, model=model, dim=len(values))
