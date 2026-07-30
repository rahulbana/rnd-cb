"""Generate banner images for articles via the OpenAI image API."""
from __future__ import annotations

import base64
import logging
import os
import uuid

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def _banners_dir() -> str:
    path = os.path.join(settings.MEDIA_DIR, "banners")
    os.makedirs(path, exist_ok=True)
    return path


def _build_prompt(title: str, summary: str, tags: list[str]) -> str:
    topic = title or summary or "an article"
    tag_str = ", ".join(tags[:6]) if tags else ""
    return (
        "A clean, modern, professional editorial banner illustration for a blog "
        f"article titled: \"{topic}\". "
        + (f"Themes: {tag_str}. " if tag_str else "")
        + "Wide landscape hero image, tasteful and abstract, strong focal "
        "concept, balanced composition with soft lighting and a cohesive color "
        "palette. No text, no words, no letters, no watermark, no logos."
    )


def _decode_image(data0) -> bytes:
    """Handle both b64_json (gpt-image-1) and url (dall-e) responses."""
    b64 = getattr(data0, "b64_json", None)
    if b64:
        return base64.b64decode(b64)
    url = getattr(data0, "url", None)
    if url:
        import httpx

        resp = httpx.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content
    raise RuntimeError("Image response contained neither b64_json nor url")


def generate_banner(
    *, title: str, summary: str = "", tags: list[str] | None = None
) -> str:
    """Generate a banner image and return its relative media URL."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured; cannot generate images.",
        )

    from app.services.observability import get_openai_client

    client = get_openai_client(
        api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
    )
    prompt = _build_prompt(title, summary, tags or [])

    try:
        result = client.images.generate(
            model=settings.IMAGE_MODEL,
            prompt=prompt,
            size=settings.IMAGE_SIZE,
            n=1,
        )
        image_bytes = _decode_image(result.data[0])
    except Exception as exc:
        logger.exception("Banner generation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Banner generation failed: {exc}",
        ) from exc

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(_banners_dir(), filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    return f"{settings.MEDIA_URL_PREFIX}/banners/{filename}"


def resolve_media_path(media_url: str | None) -> str | None:
    """Map a stored /media/... URL back to a local file path, if it exists."""
    if not media_url or not media_url.startswith(settings.MEDIA_URL_PREFIX):
        return None
    rel = media_url[len(settings.MEDIA_URL_PREFIX):].lstrip("/")
    path = os.path.join(settings.MEDIA_DIR, rel)
    return path if os.path.exists(path) else None
