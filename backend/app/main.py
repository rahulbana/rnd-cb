"""FastAPI application exposing the AI Translator API."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .history import HistoryStore
from .languages import LANGUAGES, STYLES, DEFAULT_STYLE, is_supported
from .schemas import (
    BatchItem,
    BatchTranslateRequest,
    BatchTranslateResponse,
    HistoryEntry,
    LanguageInfo,
    MetadataResponse,
    TranslateRequest,
    TranslateResponse,
)
from .translator import TranslationError, translate_batch, translate_one

settings = get_settings()
history = HistoryStore(limit=settings.history_limit)

app = FastAPI(
    title="AI Translator",
    description="Multilingual translation API powered by an LLM.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_langs(source_lang: str, target_lang: str, style: str) -> None:
    if not is_supported(source_lang):
        raise HTTPException(400, f"Unsupported source language: {source_lang}")
    if target_lang == "auto" or not is_supported(target_lang):
        raise HTTPException(400, f"Unsupported target language: {target_lang}")
    if style not in STYLES:
        raise HTTPException(400, f"Unsupported style: {style}")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": settings.openai_model, "key_configured": bool(settings.openai_api_key)}


@app.get("/api/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    return MetadataResponse(
        languages=[LanguageInfo(code=c, name=n) for c, n in LANGUAGES.items()],
        styles=list(STYLES.keys()),
        default_style=DEFAULT_STYLE,
    )


@app.post("/api/translate", response_model=TranslateResponse)
def translate(req: TranslateRequest) -> TranslateResponse:
    _validate_langs(req.source_lang, req.target_lang, req.style)
    try:
        translated, detected = translate_one(
            req.text, req.source_lang, req.target_lang, req.style
        )
    except TranslationError as exc:
        raise HTTPException(502, str(exc)) from exc

    history.add(
        original=req.text,
        translated_text=translated,
        source_lang=req.source_lang,
        detected_source_lang=detected,
        target_lang=req.target_lang,
        style=req.style,
    )
    return TranslateResponse(
        translated_text=translated,
        detected_source_lang=detected,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        style=req.style,
    )


@app.post("/api/translate/batch", response_model=BatchTranslateResponse)
def translate_batch_endpoint(req: BatchTranslateRequest) -> BatchTranslateResponse:
    _validate_langs(req.source_lang, req.target_lang, req.style)
    texts = [t for t in req.texts if t.strip()]
    if not texts:
        raise HTTPException(400, "No non-empty texts provided.")
    try:
        translations, detected = translate_batch(
            texts, req.source_lang, req.target_lang, req.style
        )
    except TranslationError as exc:
        raise HTTPException(502, str(exc)) from exc

    items = []
    for original, translated in zip(texts, translations):
        items.append(BatchItem(original=original, translated_text=translated))
        history.add(
            original=original,
            translated_text=translated,
            source_lang=req.source_lang,
            detected_source_lang=detected,
            target_lang=req.target_lang,
            style=req.style,
        )
    return BatchTranslateResponse(
        items=items,
        detected_source_lang=detected,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        style=req.style,
    )


@app.get("/api/history", response_model=list[HistoryEntry])
def get_history() -> list[HistoryEntry]:
    return history.list()


@app.delete("/api/history")
def clear_history() -> dict:
    history.clear()
    return {"status": "cleared"}
