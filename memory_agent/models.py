"""Factories for the OpenAI models used across the app.

Centralising construction here keeps model configuration in one place and gives
tests a single seam to stub the LLM / embeddings.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .config import Settings


def make_chat_model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.chat_model,
        temperature=settings.temperature,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def make_embeddings(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
