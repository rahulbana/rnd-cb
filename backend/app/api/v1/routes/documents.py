"""Document upload + retrieval routes (Phase 2, synchronous path)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.parsers import ParserError
from app.api.v1.deps import chunker, embedder, parser, storage, vector_store
from app.api.v1.schemas import (
    DocumentOut,
    SearchHit,
    SearchResponse,
    UploadResponse,
)
from app.core.config import settings
from app.db.base import get_db
from app.db.models import Document
from app.domain.interfaces import Chunker, Embedder, ObjectStorage, Parser, VectorStore
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        org_id=document.org_id,
        owner_id=document.owner_id,
        filename=document.filename,
        mime_type=document.mime_type,
        checksum=document.checksum,
        storage_uri=document.storage_uri,
        status=document.status,
    )


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    object_storage: ObjectStorage = Depends(storage),
    document_parser: Parser = Depends(parser),
    document_chunker: Chunker = Depends(chunker),
    document_embedder: Embedder = Depends(embedder),
    store: VectorStore = Depends(vector_store),
) -> UploadResponse:
    """Upload a file: store it, dedup by checksum, parse, chunk, embed, index.

    Returns the canonical ``ParsedDocument`` regardless of source format, plus
    the number of chunks indexed for raw similarity search.
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file upload")

    ingestion = IngestionService(
        embedder=document_embedder, vector_store=store, chunker=document_chunker
    )
    service = DocumentService(object_storage, document_parser, ingestion, db)
    try:
        result = await service.upload(
            data=data,
            filename=file.filename or "upload.bin",
            content_type=file.content_type,
            org_id=settings.DEFAULT_ORG_ID,
            owner_id=settings.DEFAULT_ORG_ID,
        )
    except ParserError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    return UploadResponse(
        document=_to_out(result.document),
        deduped=result.deduped,
        chunk_count=result.chunk_count,
        parsed=result.parsed,
    )


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    q: str,
    top_k: int = 5,
    document_embedder: Embedder = Depends(embedder),
    store: VectorStore = Depends(vector_store),
) -> SearchResponse:
    """Raw dense similarity search over indexed chunks (Phase 3).

    Retrieval independent of generation; hybrid retrieval and reranking arrive
    in Phases 5-6.
    """
    ingestion = IngestionService(embedder=document_embedder, vector_store=store)
    hits = await ingestion.search(q, namespace=settings.DEFAULT_ORG_ID, top_k=top_k)
    return SearchResponse(
        query=q,
        hits=[
            SearchHit(
                chunk_id=h.chunk.id,
                document_id=h.chunk.metadata.document_id,
                text=h.chunk.text,
                score=h.score,
                page=h.chunk.metadata.page,
                heading_path=h.chunk.metadata.heading_path,
            )
            for h in hits
        ],
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: Session = Depends(get_db)) -> list[DocumentOut]:
    stmt = select(Document).where(Document.org_id == settings.DEFAULT_ORG_ID)
    return [_to_out(d) for d in db.execute(stmt).scalars().all()]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentOut:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_out(document)
