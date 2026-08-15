"""Application configuration.

All tunables are exposed via environment variables (prefix ``RAG_``) so the
system can be reconfigured for different environments without code changes.
Values here are safe production-shaped defaults for local development.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# List fields populated from env/.env should accept a plain comma-separated
# string (e.g. RAG_RERANK_MODELS=a,b) instead of requiring JSON. NoDecode tells
# the settings source to hand us the raw string so our validator can split it.
CsvList = Annotated[list[str], NoDecode]


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
    cors_origins: CsvList = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Database (chat history) ---
    # SQLite by default; switch to Postgres later with e.g.
    #   RAG_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str = "sqlite:///./data/app.db"

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
    rerank_models: CsvList = Field(
        default_factory=lambda: ["cross-encoder/ms-marco-MiniLM-L-6-v2"]
    )

    # --- Parsing backends (switchable) ---
    pdf_backend: Literal["pymupdf", "pdfplumber", "unstructured", "docling"] = "pymupdf"
    pdf_ocr_fallback: bool = True  # OCR pages that yield no extractable text
    pdf_ocr_dpi: int = 200  # lower (e.g. 120-150) is faster but less accurate
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

    @field_validator("cors_origins", "rerank_models", mode="before")
    @classmethod
    def _split_csv(cls, value):
        """Accept a JSON list, a comma-separated string, or a real list."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                import json

                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
