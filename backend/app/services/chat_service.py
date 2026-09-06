"""Chat orchestration -- retrieval-grounded generation over injected ports.

Phase 7 adds prompt templates, streaming, memory, and citation formatting.
This sets the seam: the service depends on the LLMProvider port only.
"""

from __future__ import annotations

from app.domain.interfaces import LLMProvider
from app.domain.models import ChatMessage, LLMResponse, Role
from app.services.retrieval_service import RetrievalService


class ChatService:
    """Coordinates retrieval + generation into a grounded answer."""

    def __init__(self, llm: LLMProvider, retrieval: RetrievalService) -> None:
        self._llm = llm
        self._retrieval = retrieval

    async def answer(self, question: str, *, namespace: str) -> LLMResponse:
        context = await self._retrieval.search(question, namespace=namespace)
        context_text = "\n\n".join(rc.chunk.text for rc in context)
        messages = [
            ChatMessage(
                role=Role.SYSTEM,
                content="Answer only from the provided context; cite sources.",
            ),
            ChatMessage(
                role=Role.USER,
                content=f"Context:\n{context_text}\n\nQuestion: {question}",
            ),
        ]
        return await self._llm.generate(messages)
