"""Writing-style reference routes: upload files/links used for LLM style."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.style_reference import StyleReference
from app.models.user import User
from app.schemas.style import StyleLinkCreate, StyleReferenceOut
from app.services.ingest import extract_from_file, extract_from_url
from app.services.vectorstore import get_vector_store

router = APIRouter(prefix="/style-references", tags=["style"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


async def _index(ref: StyleReference) -> None:
    await asyncio.to_thread(
        get_vector_store().upsert_style_reference,
        ref_id=ref.id,
        user_id=ref.user_id,
        name=ref.name,
        content=ref.content,
    )


@router.get("", response_model=list[StyleReferenceOut])
async def list_style_references(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StyleReference)
        .where(StyleReference.user_id == user.id)
        .order_by(StyleReference.created_at.desc())
    )
    return result.scalars().all()


@router.post("/link", response_model=StyleReferenceOut, status_code=status.HTTP_201_CREATED)
async def add_link(
    payload: StyleLinkCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    title, text = await asyncio.to_thread(extract_from_url, payload.url)
    ref = StyleReference(
        user_id=user.id,
        name=title[:512],
        source_type="link",
        origin=payload.url[:1024],
        content=text,
        char_count=len(text),
    )
    db.add(ref)
    await db.commit()
    await db.refresh(ref)
    await _index(ref)
    return ref


@router.post("/upload", response_model=StyleReferenceOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10 MB).",
        )
    text = extract_from_file(file.filename or "", data)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable text found in the file.",
        )
    ref = StyleReference(
        user_id=user.id,
        name=(file.filename or "Uploaded file")[:512],
        source_type="file",
        origin=(file.filename or "")[:1024],
        content=text,
        char_count=len(text),
    )
    db.add(ref)
    await db.commit()
    await db.refresh(ref)
    await _index(ref)
    return ref


@router.delete("/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style_reference(
    ref_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ref = await db.get(StyleReference, ref_id)
    if ref is None or ref.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await db.delete(ref)
    await db.commit()
    await asyncio.to_thread(get_vector_store().delete_style_reference, ref_id)
