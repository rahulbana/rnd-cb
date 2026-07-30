"""LLM content generation using OpenAI structured outputs."""
from __future__ import annotations

import json
import logging

from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.generation import GeneratedContent, GenerationRequest

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert content strategist and SEO writer.
You produce polished, publication-ready articles and rich metadata.
Always return well-structured Markdown for the body (headings, lists,
emphasis where useful). Keep the SEO meta description around 155
characters. Extract named entities accurately."""


def _length_hint(length: str | None) -> str:
    return {
        "short": "roughly 250-400 words",
        "medium": "roughly 600-900 words",
        "long": "roughly 1200-1800 words",
    }.get((length or "medium").lower(), "roughly 600-900 words")


def _build_user_prompt(req: GenerationRequest, rag_context: list[str]) -> str:
    parts = [f"Write content about: {req.prompt}"]
    if req.tone:
        parts.append(f"Tone: {req.tone}.")
    if req.audience:
        parts.append(f"Target audience: {req.audience}.")
    parts.append(f"Length: {_length_hint(req.length)}.")
    if req.keywords:
        parts.append(f"Weave in these SEO keywords naturally: {', '.join(req.keywords)}.")
    if rag_context:
        joined = "\n\n---\n\n".join(rag_context)
        parts.append(
            "For voice and style consistency, here are excerpts from the "
            f"author's previous articles. Match their style, do not copy:\n{joined}"
        )
    return "\n".join(parts)


def _json_schema() -> dict:
    schema = GeneratedContent.model_json_schema()
    schema["additionalProperties"] = False
    return schema


def generate_content(
    req: GenerationRequest, rag_context: list[str] | None = None
) -> GeneratedContent:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "OPENAI_API_KEY is not configured on the server. "
                "Set it to enable AI content generation."
            ),
        )

    from openai import OpenAI  # lazy import

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
    )
    user_prompt = _build_user_prompt(req, rag_context or [])

    try:
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "generated_content",
                    "schema": _json_schema(),
                    "strict": False,
                },
            },
        )
        raw = completion.choices[0].message.content or "{}"
        return GeneratedContent.model_validate(json.loads(raw))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("LLM generation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Content generation failed: {exc}",
        ) from exc
