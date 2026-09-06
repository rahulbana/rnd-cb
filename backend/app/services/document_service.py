"""Document upload orchestration (Phase 2, synchronous path).

Store the raw file, dedup by checksum, persist metadata, and parse into the
canonical ``ParsedDocument`` shape. Depends only on the ObjectStorage and
Parser ports plus a DB session -- never a concrete provider.

Async ingestion (off the request thread) arrives in Phase 4; chunking,
embedding and indexing in Phase 3. Here the parse runs inline.
"""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import ChunkMeta, Document
from app.domain.interfaces import ObjectStorage, Parser
from app.domain.models import ParsedDocument
from app.services.ingestion_service import IngestionService

logger = get_logger("service.document")

# Extension -> MIME fallbacks for types Python's mimetypes misses or varies on.
_EXT_MIME = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".eml": "message/rfc822",
}


def compute_checksum(data: bytes) -> str:
    """SHA-256 hex digest used for content-addressed dedup."""
    return hashlib.sha256(data).hexdigest()


def guess_mime_type(filename: str, provided: str | None) -> str:
    """Resolve a usable MIME type from the client value or the filename."""
    if provided and provided not in {"application/octet-stream", ""}:
        return provided
    suffix = Path(filename).suffix.lower()
    if suffix in _EXT_MIME:
        return _EXT_MIME[suffix]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or provided or "application/octet-stream"


@dataclass
class UploadResult:
    document: Document
    parsed: ParsedDocument | None
    deduped: bool
    chunk_count: int = 0


class DocumentService:
    """Upload, parse, and index a document synchronously (Phases 2-3)."""

    def __init__(
        self,
        storage: ObjectStorage,
        parser: Parser,
        ingestion: IngestionService,
        db: Session,
    ) -> None:
        self._storage = storage
        self._parser = parser
        self._ingestion = ingestion
        self._db = db

    def _find_existing(self, org_id: str, checksum: str) -> Document | None:
        stmt = select(Document).where(
            Document.org_id == org_id, Document.checksum == checksum
        )
        return self._db.execute(stmt).scalar_one_or_none()

    async def upload(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str | None,
        org_id: str,
        owner_id: str,
    ) -> UploadResult:
        mime_type = guess_mime_type(filename, content_type)
        checksum = compute_checksum(data)

        existing = self._find_existing(org_id, checksum)
        if existing is not None:
            logger.info(
                "upload_deduped",
                document_id=existing.id,
                checksum=checksum,
                filename=filename,
            )
            return UploadResult(document=existing, parsed=None, deduped=True)

        suffix = Path(filename).suffix
        key = f"{org_id}/{checksum}{suffix}"
        storage_uri = await self._storage.put(key, data, content_type=mime_type)

        document = Document(
            org_id=org_id,
            owner_id=owner_id,
            filename=filename,
            mime_type=mime_type,
            checksum=checksum,
            storage_uri=storage_uri,
            status="uploaded",
        )
        self._db.add(document)
        self._db.commit()
        self._db.refresh(document)

        parsed = await self._parser.parse(data, filename=filename, mime_type=mime_type)
        document.status = "parsed"
        self._db.commit()

        # Chunk -> embed -> index within the org namespace, then persist the
        # citation metadata for each chunk (vectors live in the vector store).
        chunks = await self._ingestion.index(
            parsed, document_id=document.id, namespace=org_id
        )
        for chunk in chunks:
            self._db.add(
                ChunkMeta(
                    document_id=document.id,
                    page=chunk.metadata.page,
                    heading_path=chunk.metadata.heading_path,
                    vector_id=chunk.id,
                )
            )
        document.status = "indexed"
        self._db.commit()
        self._db.refresh(document)

        logger.info(
            "upload_indexed",
            document_id=document.id,
            mime_type=mime_type,
            parser=parsed.parser_name,
            used_fallback=parsed.used_fallback,
            blocks=len(parsed.text_blocks),
            chunks=len(chunks),
        )
        return UploadResult(
            document=document,
            parsed=parsed,
            deduped=False,
            chunk_count=len(chunks),
        )
