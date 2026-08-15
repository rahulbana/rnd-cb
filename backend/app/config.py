"""Application configuration.

All tunables are exposed via environment variables (prefix ``RAG_``) so the
system can be reconfigured for different environments without code changes.
Values here are safe production-shaped defaults for local development.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "Intelligent RAG Chatbot"
    environment: Literal["development", "staging", "production"] = "development"
    data_dir: str = "./data"
    upload_dir: str = "./data/uploads"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Embeddings ---
    embedding_provider: Literal["sentence_transformer"] = "sentence_transformer"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32

    # --- Vector store ---
    vectorstore_provider: Literal["chroma"] = "chroma"
    chroma_persist_dir: str = "./data/chroma"
    collection_name: str = "documents"

    # --- Chunking ---
    chunk_strategy: Literal["recursive", "by_element", "semantic"] = "recursive"
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64

    # --- Retrieval ---
    retrieval_strategy: Literal["simple", "hybrid"] = "hybrid"
    retrieval_top_k: int = 20  # candidates fetched before reranking
    final_top_k: int = 5       # passages sent to the LLM
    hybrid_alpha: float = 0.5  # weight of vector vs. keyword in fusion (0..1)

    # --- Reranking ---
    rerank_enabled: bool = True
    # Comma-separated list of cross-encoder model names (chained in order).
    rerank_models: list[str] = Field(
        default_factory=lambda: ["cross-encoder/ms-marco-MiniLM-L-6-v2"]
    )

    # --- Parsing backends (switchable) ---
    pdf_backend: Literal["pymupdf", "pdfplumber", "unstructured", "docling"] = "pymupdf"
    pdf_ocr_fallback: bool = True  # OCR pages that yield no extractable text
    ocr_language: str = "eng"

    # --- LLM ---
    llm_provider: Literal["openai", "ollama"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024

    openai_api_key: str | None = None
    openai_base_url: str | None = None  # override for Azure/compatible gateways

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
