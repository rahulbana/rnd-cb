"""LLM content generation using OpenAI structured outputs."""
from __future__ import annotations

import json
import logging
import re

from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.generation import GeneratedContent, GenerationRequest

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert content strategist and long-form SEO
writer. You produce comprehensive, polished, publication-ready articles and
rich metadata.

Write in depth and at length. A strong article includes:
- an engaging introduction that frames the topic;
- multiple substantial sections with `##` headings (and `###` subheadings
  where helpful);
- concrete details, examples, data points, step-by-step explanations and
  practical takeaways — not vague generalities;
- lists, tables or code blocks where they aid clarity;
- a conclusion, and a short FAQ section when it fits the topic.

Never pad with filler or repeat yourself, but do fully develop every section
— do not stop short or write a thin summary. Hit the requested length.
Always return well-structured Markdown for the body. Keep the SEO meta
description around 155 characters. Extract named entities accurately.

For 'sources', list the key references, studies, standards or well-known
works the article draws on. Be honest: only include a URL when you are
confident it is real and correct — otherwise omit the url and give just
the title. Never fabricate links. If the piece is original and does not
rely on external sources, return an empty list."""


def _length_hint(length: str | None) -> str:
    return {
        "short": "at least 500 words",
        "medium": "at least 1000 words",
        "long": "at least 2000 words",
        "xl": "at least 3000 words, a thorough deep-dive",
    }.get((length or "medium").lower(), "at least 1000 words")


def _build_user_prompt(
    req: GenerationRequest,
    rag_context: list[str],
    web_findings: str | None = None,
) -> str:
    parts = [f"Write content about: {req.prompt}"]
    if req.tone:
        parts.append(f"Tone: {req.tone}.")
    if req.audience:
        parts.append(f"Target audience: {req.audience}.")
    parts.append(
        f"Target length: {_length_hint(req.length)}. Write the full article and "
        "develop every section thoroughly — do not truncate or under-write."
    )
    if req.keywords:
        parts.append(f"Weave in these SEO keywords naturally: {', '.join(req.keywords)}.")
    if web_findings:
        parts.append(
            "Ground your factual claims in the researched findings below. "
            "Prefer these facts over your own recollection, and stay accurate "
            "to them. The underlying sources are recorded separately, so you "
            "do not need to repeat URLs:\n"
            f"{web_findings}"
        )
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


def _loads(raw: str) -> dict:
    """Parse the model's JSON, tolerating stray prose or code fences."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def _finalize(data: dict) -> GeneratedContent:
    """Validate and backfill any fields the model may have omitted."""
    content = GeneratedContent.model_validate(data)
    if not content.title.strip():
        content.title = "Untitled"
    if not content.summary.strip() and content.body.strip():
        plain = re.sub(r"\s+", " ", re.sub(r"[#>*`_\[\]()]", "", content.body)).strip()
        content.summary = (
            plain[:200].rsplit(" ", 1)[0] + "…" if len(plain) > 200 else plain
        )
    if not content.seo_description.strip():
        content.seo_description = content.summary[:155]
    return content


def generate_content(
    req: GenerationRequest,
    rag_context: list[str] | None = None,
    web_findings: str | None = None,
) -> GeneratedContent:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "OPENAI_API_KEY is not configured on the server. "
                "Set it to enable AI content generation."
            ),
        )

    from app.services.observability import get_openai_client

    client = get_openai_client(
        api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
    )
    user_prompt = _build_user_prompt(req, rag_context or [], web_findings)

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
        return _finalize(_loads(raw))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("LLM generation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Content generation failed: {exc}",
        ) from exc


_EXPAND_MODES = {
    "longer": (
        "Substantially expand this article. Add depth, detail, examples and "
        "explanation throughout, and add new relevant sections where useful. "
        "Aim to roughly double the length."
    ),
    "examples": (
        "Enrich this article with concrete examples, case studies, code "
        "snippets or scenarios that illustrate the points."
    ),
    "faq": (
        "Keep the article intact and append a thorough '## FAQ' section that "
        "answers the most common related questions."
    ),
    "depth": (
        "Deepen the existing sections with more technical detail, nuance, "
        "trade-offs and actionable guidance, without padding."
    ),
}


def expand_content(
    *, title: str, body: str, mode: str = "longer", instruction: str | None = None
) -> str:
    """Expand/lengthen an existing Markdown body and return the new body."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured on the server.",
        )

    directive = (
        instruction
        if mode == "custom" and instruction
        else _EXPAND_MODES.get(mode, _EXPAND_MODES["longer"])
    )

    from app.services.observability import get_openai_client

    client = get_openai_client(
        api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
    )
    try:
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert long-form editor. You expand articles "
                        "while preserving their voice, facts and intent. Preserve "
                        "the existing content and Markdown structure, improving and "
                        "extending it. Return ONLY the full updated article body in "
                        "Markdown — no preamble, no commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Title: {title}\n\nInstruction: {directive}\n\n"
                        f"Current article:\n\n{body}"
                    ),
                },
            ],
        )
        return (completion.choices[0].message.content or body).strip()
    except Exception as exc:
        logger.exception("Content expansion failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Content expansion failed: {exc}",
        ) from exc
