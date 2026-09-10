"""OpenAI client and structured question generation.

We ask the model for a flat JSON structure (one shape covering all question
types via optional fields) using JSON-schema constrained output, then validate
each item into the strongly-typed pydantic union in ``schemas``. Keeping the
wire schema flat avoids brittle ``anyOf`` strict-mode issues across models
while still giving us validated, typed data to work with.
"""
import json

from openai import OpenAI

from .config import get_settings
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import (
    GenerateRequest,
    MCQOption,
    MCQQuestion,
    Question,
    ShortAnswerQuestion,
    TrueFalseQuestion,
)

# Flat JSON schema handed to the model. Every question is one object; fields
# not relevant to a given type are simply left empty.
_GENERATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["questions"],
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "type",
                    "question",
                    "difficulty",
                    "explanation",
                    "options",
                    "mcq_answer",
                    "tf_answer",
                    "short_answer",
                    "keywords",
                ],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["mcq", "true_false", "short_answer"],
                    },
                    "question": {"type": "string"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                    },
                    "explanation": {"type": "string"},
                    "options": {
                        "type": "array",
                        "description": "MCQ only: exactly 4 options.",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["label", "text"],
                            "properties": {
                                "label": {
                                    "type": "string",
                                    "enum": ["A", "B", "C", "D"],
                                },
                                "text": {"type": "string"},
                            },
                        },
                    },
                    "mcq_answer": {
                        "type": "string",
                        "description": "MCQ only: correct option label.",
                    },
                    "tf_answer": {
                        "type": "boolean",
                        "description": "True/False only: the correct boolean.",
                    },
                    "short_answer": {
                        "type": "string",
                        "description": "Short-answer only: concise model answer.",
                    },
                    "keywords": {
                        "type": "array",
                        "description": "Short-answer only: key terms.",
                        "items": {"type": "string"},
                    },
                },
            },
        }
    },
}


class LLMError(RuntimeError):
    """Raised when generation fails or the model returns unusable data."""


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError(
            "OPENAI_API_KEY is not set. Add it to backend/.env before generating."
        )
    kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def _to_typed(raw: dict) -> Question | None:
    """Validate one raw item into the appropriate typed model, or drop it."""
    qtype = raw.get("type")
    try:
        if qtype == "mcq":
            return MCQQuestion(
                question=raw["question"],
                options=[MCQOption(**o) for o in raw.get("options", [])],
                answer=raw["mcq_answer"],
                explanation=raw["explanation"],
                difficulty=raw["difficulty"],
            )
        if qtype == "true_false":
            return TrueFalseQuestion(
                question=raw["question"],
                answer=bool(raw["tf_answer"]),
                explanation=raw["explanation"],
                difficulty=raw["difficulty"],
            )
        if qtype == "short_answer":
            return ShortAnswerQuestion(
                question=raw["question"],
                answer=raw["short_answer"],
                keywords=raw.get("keywords", []),
                explanation=raw["explanation"],
                difficulty=raw["difficulty"],
            )
    except Exception:
        return None
    return None


def generate_questions(req: GenerateRequest) -> list[Question]:
    settings = get_settings()
    client = _client()

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.4,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(req)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "question_set",
                    "strict": True,
                    "schema": _GENERATION_SCHEMA,
                },
            },
        )
    except Exception as exc:  # network / auth / API errors
        raise LLMError(f"OpenAI request failed: {exc}") from exc

    content = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError("Model returned invalid JSON.") from exc

    typed = [q for raw in data.get("questions", []) if (q := _to_typed(raw))]
    if not typed:
        raise LLMError("Model returned no valid questions. Try again.")
    return typed
