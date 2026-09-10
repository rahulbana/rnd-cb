"""Centralized configuration, loaded from the environment (and an optional .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load ./.env into the environment if present. No-op when the file is missing,
# so deployments that inject real env vars work unchanged.
load_dotenv()


@dataclass(frozen=True)
class Config:
    port: int
    #: Model used for every summarization request.
    model: str
    #: Above this many input tokens we switch from a single pass to a chunked
    #: map-reduce pass. gpt-4o / gpt-4o-mini have a 128k-token window, so this
    #: default leaves room for the summary output; lower it to watch the chunking
    #: path engage on smaller documents.
    chunk_threshold_tokens: int
    #: Approximate characters per chunk when map-reduce is used (~4 chars/token,
    #: so ~24k tokens/chunk) — comfortably inside one request.
    chars_per_chunk: int


config = Config(
    port=int(os.getenv("PORT", "3000")),
    model=os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini"),
    chunk_threshold_tokens=int(os.getenv("CHUNK_THRESHOLD_TOKENS", "100000")),
    chars_per_chunk=96_000,
)
