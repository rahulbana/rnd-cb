"""Ingestion pipeline: parse -> chunk -> embed -> index, with step events.

Runs as a background task. Each stage publishes start/done events onto the
job's channel so the frontend renders live progress.
"""
from __future__ import annotations

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
    try:
        await emitter.step_start("upload", f"Received '{source_name}'")
        await emitter.step_done("upload")

        # 1. Parse ----------------------------------------------------------
        await emitter.step_start("parse", "Detecting format and extracting content")
        if raw_text is not None:
            doc = parse_text(raw_text, source_name)
        else:
            doc = parse_file(path, source_name)
        await emitter.step_done(
            "parse",
            f"{len(doc.elements)} elements via {doc.parser}",
            data={"parser": doc.parser, "elements": len(doc.elements)},
        )

        # 2. Chunk ----------------------------------------------------------
        await emitter.step_start("chunk", "Splitting into retrievable chunks")
        chunker = Chunker()
        chunks = chunker.chunk(doc)
        if not chunks:
            await emitter.step_error("chunk", "No text content found to index")
            await emitter.error("Document produced no indexable text.")
            return
        await emitter.step_done(
            "chunk",
            f"{len(chunks)} chunks ({chunker.strategy}, ~{chunker.size} tokens)",
            data={"chunks": len(chunks), "strategy": chunker.strategy},
        )

        # 3. Embed ----------------------------------------------------------
        await emitter.step_start("embed", "Computing embeddings")
        embedder = get_embedder()
        vectors = embedder.embed([c.text for c in chunks])
        await emitter.step_done("embed", f"{len(vectors)} vectors "
                                         f"(dim {embedder.dimension})")

        # 4. Index ----------------------------------------------------------
        await emitter.step_start("index", "Writing to vector store")
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
        await emitter.step_done("index", f"Indexed {len(records)} chunks; "
                                         f"collection now {store.count()} total")

        await emitter.step_done("complete", f"'{source_name}' ready for questions")
        await emitter.done()
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        log.exception("Ingestion failed for %s", source_name)
        await emitter.error(f"Ingestion failed: {exc}")
    finally:
        await bus.close(channel)
