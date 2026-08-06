"""LLM-powered tools: translate, summarize, and verify claim (fact-check)."""
from __future__ import annotations

import json

from ..agent.client import LLMUnavailable, complete
from .base import Tool, err, ok
from .textextract import UnsupportedFile, read_text_from_file
from .web_search import deep_web_search


def translate_text(text: str, target_language: str, source_language: str = "auto") -> dict:
    """Translate text from one language to another."""
    try:
        src = "auto-detect the source language" if source_language == "auto" \
            else f"from {source_language}"
        result = complete(
            system="You are a professional translator. Translate the user's text "
                   f"{src} into {target_language}. Return ONLY the translated text, "
                   "with no explanations or quotes.",
            user=text,
            temperature=0.0,
        )
    except LLMUnavailable as exc:
        return err(str(exc))
    return ok({
        "source_language": source_language,
        "target_language": target_language,
        "original": text,
        "translated": result,
    })


def summarize_text(text: str | None = None, style: str = "concise",
                   file_path: str | None = None) -> dict:
    """Summarize a block of text or the contents of a file (txt, md, csv, json,
    xml, docx, pdf, …). Style can be 'concise', 'bullets', or 'detailed'."""
    source = None
    if file_path:
        try:
            text = read_text_from_file(file_path)
            source = file_path
        except FileNotFoundError:
            return err(f"File not found: {file_path}")
        except UnsupportedFile as exc:
            return err(str(exc))
        except Exception as exc:  # noqa: BLE001
            return err(f"Could not read file: {exc}")

    if not text or not text.strip():
        return err("Nothing to summarize: provide 'text' or a readable 'file_path'.")

    style_map = {
        "concise": "Write a concise summary of 2-4 sentences.",
        "bullets": "Summarize as 3-7 short bullet points.",
        "detailed": "Write a thorough, well-structured summary with key points.",
    }
    instruction = style_map.get(style, style_map["concise"])
    try:
        result = complete(
            system=f"You are an expert summarizer. {instruction}",
            user=text,
            temperature=0.2,
        )
    except LLMUnavailable as exc:
        return err(str(exc))
    out = {"style": style, "summary": result}
    if source:
        out["source_file"] = source
    return ok(out)


def verify_claim(claim: str) -> dict:
    """Fact-check a claim by researching the web and returning a verdict."""
    # Gather evidence via deep web search (works even without an LLM for sources).
    research = deep_web_search(claim, max_results=5)
    sources = research.get("data", {}).get("sources", []) if research.get("ok") else []
    evidence = research.get("data", {}).get("summary") if research.get("ok") else None

    try:
        raw = complete(
            system="You are a rigorous fact-checker. Given a claim and researched "
                   "evidence, decide a verdict. Respond in strict JSON with keys: "
                   "verdict (one of 'True','False','Partly True','Unverified'), "
                   "confidence (0-1), explanation (string). No other text.",
            user=f"Claim: {claim}\n\nEvidence:\n{evidence or 'No evidence gathered.'}",
            temperature=0.0,
            max_tokens=600,
        )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"verdict": "Unverified", "confidence": 0.0, "explanation": raw}
    except LLMUnavailable as exc:
        return err(str(exc))

    parsed["claim"] = claim
    parsed["sources"] = sources
    return ok(parsed)


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="translate_text",
            description="Translate text from one language to another.",
            category="Language",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to translate."},
                    "target_language": {"type": "string", "description": "Target language, e.g. 'French'."},
                    "source_language": {"type": "string", "description": "Source language or 'auto'."},
                },
                "required": ["text", "target_language"],
            },
            func=translate_text,
        ),
        Tool(
            name="summarize_text",
            description="Summarize a block of text, OR the contents of a file "
                        "(txt, md, csv, json, xml, docx, pdf) via file_path. "
                        "Provide either 'text' or 'file_path'.",
            category="Language",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to summarize."},
                    "file_path": {"type": "string",
                                  "description": "Path to a text/document file to summarize."},
                    "style": {
                        "type": "string",
                        "enum": ["concise", "bullets", "detailed"],
                        "description": "Summary style. Default 'concise'.",
                    },
                },
                "required": [],
            },
            func=summarize_text,
        ),
        Tool(
            name="verify_claim",
            description="Fact-check a claim by researching the web and returning a "
                        "verdict (True/False/Partly True/Unverified) with sources.",
            category="Research",
            parameters={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The claim to verify."},
                },
                "required": ["claim"],
            },
            func=verify_claim,
        ),
    ]
