"""Document upload + retrieval routes (Phase 2, synchronous path)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.parsers import ParserError
from app.api.v1.deps import parser, storage
from app.api.v1.schemas import DocumentOut, UploadResponse
from app.core.config import settings
from app.db.base import get_db
from app.db.models import Document
from app.domain.interfaces import ObjectStorage, Parser
from app.services.document_service import DocumentService

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
) -> UploadResponse:
    """Upload a file: store it, dedup by checksum, and parse it synchronously.

    Returns the canonical ``ParsedDocument`` regardless of source format.
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file upload")

    service = DocumentService(object_storage, document_parser, db)
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
        parsed=result.parsed,
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
