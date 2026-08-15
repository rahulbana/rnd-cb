"""Health and configuration endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..ingestion.router import SUPPORTED_EXTENSIONS
from ..vectorstore import get_vectorstore

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/api/config")
async def config() -> dict:
    """Expose the effective, non-secret configuration to the frontend so it can
    render defaults and available switches."""
    s = get_settings()
    try:
        indexed = get_vectorstore().count()
    except Exception:
        indexed = None
    return {
        "supported_extensions": SUPPORTED_EXTENSIONS,
        "defaults": {
            "retrieval_strategy": s.retrieval_strategy,
            "rerank_enabled": s.rerank_enabled,
            "rerank_models": s.rerank_models,
            "llm_provider": s.llm_provider,
            "llm_model": s.llm_model,
            "chunk_strategy": s.chunk_strategy,
            "top_k": s.retrieval_top_k,
            "final_top_k": s.final_top_k,
        },
        "options": {
            "retrieval_strategy": ["simple", "hybrid"],
            "llm_provider": ["openai", "ollama"],
        },
        "indexed_chunks": indexed,
        "openai_configured": bool(s.openai_api_key),
    }
