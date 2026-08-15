"""Ingestion pipeline: parse -> chunk -> embed -> index, with step events.

Runs as a background task. Each stage publishes start/done events onto the
job's channel so the frontend renders live progress. Every stage is timed and
its elapsed seconds are reported in the step detail (and logged) so a slow
upload can be localized to the exact stage.
"""
from __future__ import annotations

import time
import uuid

from ..chunking.chunker import Chunker
from ..core.events import Phase, StepEmitter, bus
from ..core.logging import get_logger
from ..embeddings import get_embedder
from ..ingestion.router import parse_file, parse_text
from ..vectorstore import get_vectorstore
from ..vectorstore.base import VectorRecord

log = get_logger(__name__)


async def ingest(channel: str, *, path: str | None = None,
                 source_name: str, raw_text: str | None = None) -> None:
    emitter = StepEmitter(channel, Phase.INGEST)
    t_total = time.perf_counter()
    try:
        await emitter.step_start("upload", f"Received '{source_name}'")
        await emitter.step_done("upload")

        # 1. Parse ----------------------------------------------------------
        await emitter.step_start("parse", "Detecting format and extracting content")
        t0 = time.perf_counter()
        if raw_text is not None:
            doc = parse_text(raw_text, source_name)
        else:
            doc = parse_file(path, source_name)
        dt = time.perf_counter() - t0
        log.info("[%s] parse: %d elements via %s in %.1fs",
                 source_name, len(doc.elements), doc.parser, dt)
        await emitter.step_done(
            "parse",
            f"{len(doc.elements)} elements via {doc.parser} ({dt:.1f}s)",
            data={"parser": doc.parser, "elements": len(doc.elements),
                  "seconds": round(dt, 2)},
        )

        # 2. Chunk ----------------------------------------------------------
        await emitter.step_start("chunk", "Splitting into retrievable chunks")
        t0 = time.perf_counter()
        chunker = Chunker()
        chunks = chunker.chunk(doc)
        dt = time.perf_counter() - t0
        if not chunks:
            await emitter.step_error("chunk", "No text content found to index")
            await emitter.error("Document produced no indexable text.")
            return
        await emitter.step_done(
            "chunk",
            f"{len(chunks)} chunks ({chunker.strategy}, ~{chunker.size} tok) ({dt:.1f}s)",
            data={"chunks": len(chunks), "strategy": chunker.strategy,
                  "seconds": round(dt, 2)},
        )

        # 3. Embed ----------------------------------------------------------
        await emitter.step_start("embed", f"Computing embeddings for {len(chunks)} chunks")
        t0 = time.perf_counter()
        embedder = get_embedder()
        vectors = embedder.embed([c.text for c in chunks])
        dt = time.perf_counter() - t0
        rate = len(vectors) / dt if dt > 0 else 0
        log.info("[%s] embed: %d vectors in %.1fs (%.0f/s)",
                 source_name, len(vectors), dt, rate)
        await emitter.step_done(
            "embed",
            f"{len(vectors)} vectors, dim {embedder.dimension} ({dt:.1f}s, {rate:.0f}/s)",
            data={"seconds": round(dt, 2)},
        )

        # 4. Index ----------------------------------------------------------
        await emitter.step_start("index", "Writing to vector store")
        t0 = time.perf_counter()
        store = get_vectorstore()
        records = [
            VectorRecord(
                id=f"{source_name}:{uuid.uuid4().hex[:12]}",
                text=chunk.text,
                embedding=vec,
                metadata={**chunk.metadata, "source": source_name,
                          "n_tokens": chunk.n_tokens},
            )
            for chunk, vec in zip(chunks, vectors)
        ]
        store.add(records)
        dt = time.perf_counter() - t0
        await emitter.step_done(
            "index",
            f"Indexed {len(records)} chunks; collection now {store.count()} ({dt:.1f}s)",
            data={"seconds": round(dt, 2)},
        )

        total = time.perf_counter() - t_total
        log.info("[%s] ingestion complete in %.1fs", source_name, total)
        await emitter.step_done("complete", f"Ready in {total:.1f}s")
        await emitter.done()
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        log.exception("Ingestion failed for %s", source_name)
        await emitter.error(f"Ingestion failed: {exc}")
    finally:
        await bus.close(channel)
