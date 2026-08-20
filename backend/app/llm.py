"""OpenAI-backed generation of notes and questions from document text."""
from __future__ import annotations

import json
import os
from typing import Dict, List

from openai import OpenAI

from .schemas import (
    QUESTION_TYPE_LABELS,
    QUESTION_TYPES,
    StudyMaterial,
)

# Model is configurable via env; default to a widely-available, capable model.
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Cap the amount of source text sent to the model to keep requests bounded.
MAX_CHARS = int(os.getenv("MAX_SOURCE_CHARS", "48000"))


class LLMConfigError(Exception):
    """Raised when the OpenAI client cannot be configured."""


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMConfigError(
            "OPENAI_API_KEY is not set. Add it to the backend environment "
            "before generating study material."
        )
    return OpenAI(api_key=api_key)


# How many questions to request per type unless the caller overrides it.
DEFAULT_COUNTS: Dict[str, int] = {
    "true_false": 6,
    "mcq": 6,
    "fill_blanks": 6,
    "very_short": 5,
    "short": 4,
    "long": 3,
    "case_based": 2,
}


def _build_prompt(
    text: str,
    selected_types: List[str],
    counts: Dict[str, int],
    grade_level: str,
    research_context: str = "",
) -> str:
    text = text[:MAX_CHARS]

    wanted = []
    for t in selected_types:
        n = counts.get(t, DEFAULT_COUNTS.get(t, 4))
        wanted.append(f"- {QUESTION_TYPE_LABELS[t]} (key \"{t}\"): {n} questions")
    wanted_block = "\n".join(wanted)

    audience = (
        f"The audience is students at the {grade_level} level and their parents."
        if grade_level
        else "The audience is students and their parents."
    )

    schema = """
Return ONLY valid JSON (no markdown fences) with this exact shape:
{
  "notes": {
    "title": "short descriptive title of the material",
    "summary": "2-4 sentence plain-language overview",
    "key_points": ["concise revision bullet", ...],
    "sections": [{"heading": "topic", "points": ["...", "..."]}],
    "glossary": ["Term: short definition", ...]
  },
  "questions": {
    "true_false":  [{"statement": "...", "answer": true, "explanation": "..."}],
    "mcq":         [{"question": "...", "options": ["A","B","C","D"], "answer": "the exact correct option text", "explanation": "..."}],
    "fill_blanks": [{"question": "sentence with ______ blank", "answer": "..."}],
    "very_short":  [{"question": "...", "answer": "one line answer"}],
    "short":       [{"question": "...", "answer": "2-3 sentence answer"}],
    "long":        [{"question": "...", "answer": "detailed paragraph answer"}],
    "case_based":  [{"case": "a short scenario grounded in the material", "questions": [{"question": "...", "answer": "..."}]}]
  }
}
Only include the question-type keys that were requested; leave others as empty arrays.
"""

    reference_block = ""
    if research_context.strip():
        reference_block = f"""

You may also use the ADDITIONAL REFERENCE MATERIAL below — gathered from
reputable educational sources online (school boards, coaching centres,
educational sites) — to enrich the notes and questions with commonly-tested
points and standard exam-style question patterns. The uploaded document is the
primary source: prefer it, do not contradict it, and only use the references to
add depth and exam-relevant coverage. Do not copy references verbatim.

=== ADDITIONAL REFERENCE MATERIAL START ===
{research_context.strip()}
=== ADDITIONAL REFERENCE MATERIAL END ==="""

    return f"""You are an expert teacher creating study material from a document.
{audience}

Create clear, accurate revision NOTES and practice QUESTIONS based primarily on
the document content below. Do not invent facts that are unsupported by the
document (or the reference material, when provided). Keep language
age-appropriate and easy to understand. Every question must include its correct
answer so parents can check their child's work.

Question types requested (generate the given number for each):
{wanted_block}

{schema}

=== DOCUMENT START ===
{text}
=== DOCUMENT END ==={reference_block}"""


def generate_study_material(
    text: str,
    selected_types: List[str],
    counts: Dict[str, int] | None = None,
    grade_level: str = "",
    research_context: str = "",
) -> StudyMaterial:
    """Call OpenAI and parse the response into a StudyMaterial model."""
    selected_types = [t for t in selected_types if t in QUESTION_TYPES]
    if not selected_types:
        selected_types = list(QUESTION_TYPES)
    counts = counts or {}

    client = _client()
    prompt = _build_prompt(text, selected_types, counts, grade_level, research_context)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a meticulous educational content generator. You "
                    "always respond with a single valid JSON object and nothing "
                    "else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    data = _safe_json(raw)

    # Drop any question types that were not requested so the UI stays clean.
    questions = data.get("questions", {}) or {}
    for t in QUESTION_TYPES:
        if t not in selected_types:
            questions[t] = []
    data["questions"] = questions

    return StudyMaterial.model_validate(data)


def _safe_json(raw: str) -> dict:
    raw = raw.strip()
    # Strip accidental markdown fences if the model added them.
    if raw.startswith("```"):
        raw = raw.strip("`")
        newline = raw.find("\n")
        if newline != -1:
            raw = raw[newline + 1 :]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to recover the outermost JSON object.
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise ValueError("The model did not return valid JSON.")
