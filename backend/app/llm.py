"""LLM-backed text transformation service.

This module owns the prompt design and the call into OpenAI. It asks the
model for a *structured* JSON response (via response_format=json_object) so
the API can return a reliable before/after comparison instead of free text.
"""
import json

from openai import OpenAI

from .config import Settings
from .schemas import Action, Change, TransformResponse


# Human-readable instruction for each action. Keeping these terse and
# specific is the core of the "prompt design" for this app.
ACTION_INSTRUCTIONS: dict[Action, str] = {
    Action.GRAMMAR: (
        "Fix only grammar mistakes (subject-verb agreement, tense, articles, "
        "prepositions, punctuation). Do not change the meaning, tone, or word "
        "choice beyond what grammar requires."
    ),
    Action.SPELLING: (
        "Fix only spelling and obvious typos. Do not change grammar, wording, "
        "tone, or meaning."
    ),
    Action.IMPROVE: (
        "Improve the clarity, flow, and word choice of the text while keeping "
        "the original meaning and roughly the same length. Fix any grammar or "
        "spelling issues along the way."
    ),
    Action.PROFESSIONAL: (
        "Rewrite the text in a polished, professional business tone suitable "
        "for workplace communication. Keep the meaning; remove slang and "
        "filler."
    ),
    Action.SIMPLIFY: (
        "Rewrite the text so it is simpler and easier to read, using plain "
        "everyday words and shorter sentences. Preserve the meaning."
    ),
    Action.FORMAL: (
        "Convert the text to a formal register: no contractions, no slang, "
        "measured and respectful phrasing. Keep the meaning."
    ),
    Action.INFORMAL: (
        "Convert the text to a relaxed, friendly, conversational tone as if "
        "writing to a colleague you know well. Keep the meaning."
    ),
}

SYSTEM_PROMPT = (
    "You are a precise writing assistant, similar to Grammarly. You transform "
    "the user's text according to a specific instruction and return a strict "
    "JSON object. Never add commentary, greetings, or content that was not "
    "implied by the input. Preserve the user's intent and any technical terms, "
    "names, or numbers exactly."
)

# The shape we ask the model to fill. Documented inline so the model returns
# exactly what our Pydantic schema expects.
JSON_CONTRACT = (
    'Return ONLY a JSON object with this exact shape:\n'
    '{\n'
    '  "result": "<the fully transformed text>",\n'
    '  "summary": "<one short sentence describing what you changed>",\n'
    '  "changes": [\n'
    '    {"original": "<original fragment>", "replacement": "<new fragment>", '
    '"reason": "<short reason>"}\n'
    '  ]\n'
    '}\n'
    'The "changes" array should list the notable edits (up to 12). If nothing '
    'needed changing, return the text unchanged, an empty "changes" array, and '
    'say so in "summary".'
)


class TransformError(RuntimeError):
    """Raised when the transformation cannot be completed."""


class WritingAssistant:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = settings.openai_model
        if settings.openai_api_key:
            self._client: OpenAI | None = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
            )
        else:
            self._client = None

    @property
    def configured(self) -> bool:
        return self._client is not None

    def _build_user_prompt(self, text: str, action: Action) -> str:
        return (
            f"Task: {ACTION_INSTRUCTIONS[action]}\n\n"
            f"{JSON_CONTRACT}\n\n"
            f"Text to transform:\n\"\"\"\n{text}\n\"\"\""
        )

    def transform(self, text: str, action: Action) -> TransformResponse:
        if self._client is None:
            raise TransformError(
                "OPENAI_API_KEY is not configured on the server. "
                "Add it to backend/.env and restart."
            )

        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                # Low temperature keeps corrections deterministic and faithful
                # — this is "controlled generation".
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",
                     "content": self._build_user_prompt(text, action)},
                ],
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean API error
            raise TransformError(f"OpenAI request failed: {exc}") from exc

        raw = completion.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TransformError(
                "The model returned malformed JSON."
            ) from exc

        result = str(data.get("result", "")).strip()
        if not result:
            raise TransformError("The model returned an empty result.")

        changes = []
        for item in data.get("changes", []) or []:
            if not isinstance(item, dict):
                continue
            changes.append(
                Change(
                    original=str(item.get("original", "")),
                    replacement=str(item.get("replacement", "")),
                    reason=str(item.get("reason", "")),
                )
            )

        return TransformResponse(
            action=action,
            original=text,
            result=result,
            changes=changes,
            summary=str(data.get("summary", "")).strip(),
        )
