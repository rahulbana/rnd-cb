"""Chat RAG pipeline: embed_query -> retrieve -> rerank -> generate.

Emits step events and streams LLM tokens onto the request's channel. Retrieval
strategy, reranking, and LLM provider are all overridable per request so the UI
can switch techniques live.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from ..config import get_settings
from ..core.events import Phase, StepEmitter, bus
from ..core.logging import get_logger
from ..llm import get_llm
from ..rag.prompt import build_messages, sources_payload
from ..reranking import get_reranker
from ..retrieval import get_retriever

log = get_logger(__name__)


@dataclass
class ChatOptions:
    retrieval_strategy: str | None = None
    rerank_enabled: bool | None = None
    rerank_models: list[str] | None = None
    llm_provider: str | None = None
    top_k: int | None = None          # candidates to retrieve
    final_top_k: int | None = None    # passages to send to the LLM

    @classmethod
    def from_dict(cls, d: dict | None) -> "ChatOptions":
        d = d or {}
        return cls(
            retrieval_strategy=d.get("retrieval_strategy"),
            rerank_enabled=d.get("rerank_enabled"),
            rerank_models=d.get("rerank_models"),
            llm_provider=d.get("llm_provider"),
            top_k=d.get("top_k"),
            final_top_k=d.get("final_top_k"),
        )


async def run_chat(channel: str, query: str, options: ChatOptions) -> None:
    settings = get_settings()
    emitter = StepEmitter(channel, Phase.CHAT)
    top_k = options.top_k or settings.retrieval_top_k
    final_k = options.final_top_k or settings.final_top_k

    try:
        strategy = options.retrieval_strategy or settings.retrieval_strategy

        # 1. Embed the query (timed; runs off the event loop so the "start"
        #    event flushes to the client before the CPU work begins). ---------
        embedder = get_embedder()
        await emitter.step_start("embed_query", "Embedding your question")
        t0 = time.perf_counter()
        qvec = await asyncio.to_thread(embedder.embed_query, query)
        await emitter.step_done("embed_query", f"dim {len(qvec)}",
                                data={"seconds": round(time.perf_counter() - t0, 3)})

        # 2. Retrieve -------------------------------------------------------
        await emitter.step_start("retrieve", f"{strategy} search, top {top_k}")
        retriever = get_retriever(strategy)
        t0 = time.perf_counter()
        candidates = await asyncio.to_thread(retriever.retrieve, query, top_k, qvec)
        await emitter.step_done(
            "retrieve", f"{len(candidates)} candidate passages",
            data={"strategy": strategy, "count": len(candidates),
                  "seconds": round(time.perf_counter() - t0, 3)},
        )

        if not candidates:
            await emitter.step_done("rerank", "skipped (no candidates)")
            await emitter.sources([])
            await _generate(emitter, query, [], options)
            return

        # 3. Rerank ---------------------------------------------------------
        rerank_on = settings.rerank_enabled if options.rerank_enabled is None \
            else options.rerank_enabled
        if rerank_on:
            reranker = get_reranker(enabled=True, models=options.rerank_models)
            await emitter.step_start("rerank", f"{reranker.name}: {len(candidates)} → {final_k}")
            t0 = time.perf_counter()
            top = await asyncio.to_thread(reranker.rerank, query, candidates, final_k)
            await emitter.step_done("rerank", f"selected top {len(top)}",
                                    data={"reranker": reranker.name,
                                          "seconds": round(time.perf_counter() - t0, 3)})
        else:
            top = candidates[:final_k]
            await emitter.step_done("rerank", "disabled — using retrieval order")

        # Surface the passages the answer is grounded in before streaming.
        await emitter.sources(sources_payload(top))

        # 3. Generate -------------------------------------------------------
        await _generate(emitter, query, top, options)
    except Exception as exc:  # noqa: BLE001
        log.exception("Chat pipeline failed")
        await emitter.error(f"Error: {exc}")
    finally:
        await bus.close(channel)


async def _generate(emitter: StepEmitter, query, chunks, options: ChatOptions) -> None:
    provider = options.llm_provider or get_settings().llm_provider
    await emitter.step_start("generate", f"Generating answer with {provider}")
    llm = get_llm(provider)
    messages = build_messages(query, chunks)
    produced = False
    t0 = time.perf_counter()
    async for token in llm.stream(messages):
        produced = True
        await emitter.token(token)
    if not produced:
        await emitter.token("(the model returned an empty response)")
    await emitter.step_done("generate", f"model: {llm.model}",
                            data={"seconds": round(time.perf_counter() - t0, 3)})
    await emitter.step_done("complete", "done")
    await emitter.done()
