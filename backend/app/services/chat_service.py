"""Chat orchestration -- retrieval-grounded, cited, streamed generation.

Pipeline: retrieve -> rerank -> assemble context -> sanitize -> render versioned
prompt -> generate/stream -> persist the turn with citations, provider, tokens,
latency, and cost. If nothing relevant is retrieved, answer with the explicit
"not found in context" fallback rather than hallucinating.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.adapters.tracers import NoopTracer
from app.core.logging import get_logger
from app.domain.interfaces import LLMProvider, Reranker, Tracer
from app.domain.models import ChatMessage, Citation, Role
from app.prompts.renderer import PromptRenderer
from app.services.context_assembly import AssembledContext, ContextAssembler
from app.services.conversation_memory import ConversationMemory
from app.services.cost import estimate_cost
from app.services.prompt_safety import sanitize_context
from app.services.retrieval_service import RetrievalService

logger = get_logger("service.chat")


@dataclass
class ChatResult:
    conversation_id: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    provider: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    prompt_version: str = "v1"
    found: bool = True


@dataclass
class StreamHandle:
    """Citations/metadata known up front; ``tokens`` streams the answer."""

    conversation_id: str
    citations: list[Citation]
    found: bool
    tokens: AsyncIterator[str]


class ChatService:
    """Coordinates retrieval-grounded generation over injected ports."""

    def __init__(
        self,
        llm: LLMProvider,
        retrieval: RetrievalService,
        reranker: Reranker,
        memory: ConversationMemory,
        *,
        renderer: PromptRenderer | None = None,
        assembler: ContextAssembler | None = None,
        temperature: float = 0.2,
        top_k: int = 5,
        fetch_k: int = 20,
        not_found_message: str = "I couldn't find that in the provided documents.",
        user_id: str = "",
        tracer: Tracer | None = None,
    ) -> None:
        self._llm = llm
        self._retrieval = retrieval
        self._reranker = reranker
        self._memory = memory
        self._renderer = renderer or PromptRenderer()
        self._assembler = assembler or ContextAssembler()
        self._tracer = tracer or NoopTracer()
        self._temp = temperature
        self._top_k = top_k
        self._fetch_k = fetch_k
        self._not_found = not_found_message
        self._user_id = user_id

    # --- pipeline helpers ----------------------------------------------------

    async def _assemble(
        self, question: str, *, namespace: str
    ) -> AssembledContext | None:
        with self._tracer.span("rag.retrieve", namespace=namespace):
            results, plan = await self._retrieval.retrieve(
                question, namespace=namespace, top_k=self._fetch_k
            )
        with self._tracer.span(
            "rag.rerank", candidates=len(results), reranker=self._reranker.name
        ):
            reranked = await self._reranker.rerank(plan.text, results, top_k=self._top_k)
        if not reranked:
            return None
        with self._tracer.span(
            "rag.assemble",
            chunk_ids=",".join(rc.chunk.id for rc in reranked),
            scores=",".join(f"{rc.score:.4f}" for rc in reranked),
            prompt_version=self._renderer.version,
        ):
            assembled = self._assembler.assemble(plan.text, reranked)
        clean, flagged = sanitize_context(assembled.text)
        if flagged:
            logger.warning("prompt_injection_flagged", namespace=namespace)
        return AssembledContext(
            text=clean, citations=assembled.citations, chunks=assembled.chunks
        )

    def _build_messages(
        self, history: list[ChatMessage], question: str, context: str
    ) -> list[ChatMessage]:
        return [
            ChatMessage(
                role=Role.SYSTEM,
                content=self._renderer.system(not_found_message=self._not_found),
            ),
            *history,
            ChatMessage(
                role=Role.USER,
                content=self._renderer.user(question=question, context=context),
            ),
        ]

    # --- public API ----------------------------------------------------------

    async def answer(
        self, question: str, *, namespace: str, conversation_id: str | None = None
    ) -> ChatResult:
        conv = self._memory.ensure_conversation(
            conversation_id, user_id=self._user_id, title=question
        )
        history = await self._memory.history(conv.id)
        self._memory.persist(conv.id, role=Role.USER, content=question)

        assembled = await self._assemble(question, namespace=namespace)
        if assembled is None:
            self._memory.persist(
                conv.id,
                role=Role.ASSISTANT,
                content=self._not_found,
                provider=self._llm.name,
            )
            return ChatResult(
                conversation_id=conv.id,
                answer=self._not_found,
                provider=self._llm.name,
                prompt_version=self._renderer.version,
                found=False,
            )

        messages = self._build_messages(history, question, assembled.text)
        resp = await self._llm.generate(messages, temperature=self._temp)
        cost = estimate_cost(resp.provider, resp.tokens_in, resp.tokens_out)
        logger.info(
            "chat_generated",
            conversation_id=conv.id,
            provider=resp.provider,
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            latency_ms=round(resp.latency_ms, 1),
            cost_usd=round(cost, 6),
            prompt_version=self._renderer.version,
            citations=len(assembled.citations),
        )
        self._memory.persist(
            conv.id,
            role=Role.ASSISTANT,
            content=resp.content,
            citations=assembled.citations,
            provider=resp.provider,
            prompt_version=self._renderer.version,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            latency_ms=int(resp.latency_ms),
        )
        return ChatResult(
            conversation_id=conv.id,
            answer=resp.content,
            citations=assembled.citations,
            contexts=[c.chunk.text for c in assembled.chunks],
            provider=resp.provider,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            latency_ms=resp.latency_ms,
            cost_usd=cost,
            prompt_version=self._renderer.version,
        )

    async def stream(
        self, question: str, *, namespace: str, conversation_id: str | None = None
    ) -> StreamHandle:
        conv = self._memory.ensure_conversation(
            conversation_id, user_id=self._user_id, title=question
        )
        history = await self._memory.history(conv.id)
        self._memory.persist(conv.id, role=Role.USER, content=question)

        assembled = await self._assemble(question, namespace=namespace)
        if assembled is None:

            async def _not_found_gen() -> AsyncIterator[str]:
                yield self._not_found
                self._memory.persist(
                    conv.id,
                    role=Role.ASSISTANT,
                    content=self._not_found,
                    provider=self._llm.name,
                )

            return StreamHandle(conv.id, [], False, _not_found_gen())

        messages = self._build_messages(history, question, assembled.text)

        async def _gen() -> AsyncIterator[str]:
            parts: list[str] = []
            async for token in self._llm.stream(messages, temperature=self._temp):
                parts.append(token)
                yield token
            content = "".join(parts)
            tokens_in = sum(self._llm.count_tokens(m.content) for m in messages)
            tokens_out = self._llm.count_tokens(content)
            self._memory.persist(
                conv.id,
                role=Role.ASSISTANT,
                content=content,
                citations=assembled.citations,
                provider=self._llm.name,
                prompt_version=self._renderer.version,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            logger.info(
                "chat_streamed",
                conversation_id=conv.id,
                provider=self._llm.name,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=round(estimate_cost(self._llm.name, tokens_in, tokens_out), 6),
                prompt_version=self._renderer.version,
            )

        return StreamHandle(conv.id, assembled.citations, True, _gen())
