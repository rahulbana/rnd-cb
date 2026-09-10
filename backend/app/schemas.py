"""Pydantic request/response models for the API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .languages import DEFAULT_STYLE


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to translate.")
    source_lang: str = Field("auto", description="Source language code or 'auto'.")
    target_lang: str = Field(..., description="Target language code.")
    style: str = Field(DEFAULT_STYLE, description="Translation style: formal, casual, technical.")


class TranslateResponse(BaseModel):
    translated_text: str
    detected_source_lang: str
    source_lang: str
    target_lang: str
    style: str


class BatchTranslateRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="List of texts to translate.")
    source_lang: str = Field("auto", description="Source language code or 'auto'.")
    target_lang: str = Field(..., description="Target language code.")
    style: str = Field(DEFAULT_STYLE, description="Translation style.")


class BatchItem(BaseModel):
    original: str
    translated_text: str


class BatchTranslateResponse(BaseModel):
    items: list[BatchItem]
    detected_source_lang: str
    source_lang: str
    target_lang: str
    style: str


class HistoryEntry(BaseModel):
    id: str
    created_at: datetime
    source_lang: str
    detected_source_lang: str
    target_lang: str
    style: str
    original: str
    translated_text: str


class LanguageInfo(BaseModel):
    code: str
    name: str


class MetadataResponse(BaseModel):
    languages: list[LanguageInfo]
    styles: list[str]
    default_style: str
