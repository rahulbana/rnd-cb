"""Summarization orchestration: single-pass vs. map-reduce, streaming, structured output."""

from __future__ import annotations

from typing import AsyncIterator

from .chunking import chunk_text
from .config import config
from .llm import MODEL, count_tokens, get_client
from .models import StructuredSummary, SummarizeRequest
from . import prompts

STREAM_MAX_TOKENS = 4_096  # generous ceiling for a streamed summary
MAP_MAX_TOKENS = 1_500  # per-chunk condensations stay compact
SUMMARY_TEMPERATURE = 0.3  # focused, low-variance summaries

# An event is a JSON-serializable dict matching the frontend's StreamEvent union.
Event = dict


async def summarize_streaming(opts: SummarizeRequest) -> AsyncIterator[Event]:
    """Summarize ``opts.text``, yielding stream events. Chooses a single-pass
    request when the input fits comfortably, and a chunked map-reduce pass when
    it does not."""
    system = prompts.build_system_prompt(opts)
    user = prompts.build_user_prompt(opts.text)

    yield {"type": "status", "message": "Counting tokens…"}
    input_tokens = count_tokens(system, user)

    if input_tokens <= config.chunk_threshold_tokens:
        yield {"type": "meta", "inputTokens": input_tokens, "strategy": "single-pass"}
        async for ev in _single_pass(system, user, input_tokens):
            yield ev
    else:
        async for ev in _map_reduce(opts, input_tokens):
            yield ev


async def _stream_summary(
    messages: list[dict], input_tokens: int
) -> AsyncIterator[Event]:
    """Stream one chat completion, yielding text deltas then a 'done' event."""
    stream = await get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=SUMMARY_TEMPERATURE,
        max_tokens=STREAM_MAX_TOKENS,
        stream=True,
        stream_options={"include_usage": True},
    )

    output_tokens = 0
    async for chunk in stream:
        if chunk.choices:
            text = chunk.choices[0].delta.content
            if text:
                yield {"type": "delta", "text": text}
        # The final chunk carries usage (choices is empty there).
        if chunk.usage:
            output_tokens = chunk.usage.completion_tokens

    yield {"type": "done", "outputTokens": output_tokens, "inputTokens": input_tokens}


async def _single_pass(
    system: str, user: str, input_tokens: int
) -> AsyncIterator[Event]:
    yield {"type": "status", "message": "Generating summary…"}
    async for ev in _stream_summary(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        input_tokens,
    ):
        yield ev


async def _map_reduce(opts: SummarizeRequest, input_tokens: int) -> AsyncIterator[Event]:
    chunks = chunk_text(opts.text, config.chars_per_chunk)
    yield {
        "type": "meta",
        "inputTokens": input_tokens,
        "strategy": "map-reduce",
        "chunks": len(chunks),
    }
    yield {
        "type": "status",
        "message": (
            f"Document is large (~{input_tokens:,} tokens). "
            f"Splitting into {len(chunks)} sections."
        ),
    }

    # MAP: condense each chunk. These are throwaway intermediate summaries, so
    # favor speed with a low temperature and a tight output cap.
    map_system = prompts.build_map_system_prompt()
    section_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        yield {
            "type": "status",
            "message": f"Summarizing section {i + 1} of {len(chunks)}…",
        }
        res = await get_client().chat.completions.create(
            model=MODEL,
            temperature=0.2,
            max_tokens=MAP_MAX_TOKENS,
            messages=[
                {"role": "system", "content": map_system},
                {
                    "role": "user",
                    "content": prompts.build_map_user_prompt(chunk, i + 1, len(chunks)),
                },
            ],
        )
        section_summaries.append(res.choices[0].message.content or "")

    # REDUCE: synthesize the final, formatted summary from the section summaries,
    # streaming the result to the client.
    yield {"type": "status", "message": "Synthesizing final summary…"}
    async for ev in _stream_summary(
        [
            {"role": "system", "content": prompts.build_reduce_system_prompt(opts)},
            {"role": "user", "content": prompts.build_reduce_user_prompt(section_summaries)},
        ],
        input_tokens,
    ):
        yield ev


# ---------------------------------------------------------------------------
# Structured extraction: a non-streaming request that returns machine-readable
# JSON. Uses OpenAI Structured Outputs (response_format json_schema, strict),
# which guarantees the model's output conforms to the schema.
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM = (
    "You extract structured information from a document. Base every field strictly "
    "on the document; never invent content. Use empty arrays where nothing applies."
)

# JSON Schema for Structured Outputs. strict mode requires every property to be
# listed in `required` and additionalProperties to be false.
_EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string", "description": "A concise title for the document."},
        "summary": {"type": "string", "description": "A 2-4 sentence overview."},
        "keyPoints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Most important takeaways, ordered by importance.",
        },
        "decisions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Decisions made or proposed (empty if none).",
        },
        "actionItems": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete next steps, each starting with a verb (empty if none).",
        },
        "entities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Notable people, orgs, products, or places mentioned.",
        },
    },
    "required": ["title", "summary", "keyPoints", "decisions", "actionItems", "entities"],
}


async def extract_structured(text: str) -> StructuredSummary:
    """Extract a structured summary object from text (non-streaming)."""
    res = await get_client().chat.completions.create(
        model=MODEL,
        temperature=0.2,
        max_tokens=2_000,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "structured_summary",
                "strict": True,
                "schema": _EXTRACT_SCHEMA,
            },
        },
        messages=[
            {"role": "system", "content": _EXTRACT_SYSTEM},
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "Extract structured information from the document below.",
                        "",
                        "<document>",
                        text,
                        "</document>",
                    ]
                ),
            },
        ],
    )

    raw = res.choices[0].message.content or ""
    try:
        return StructuredSummary.model_validate_json(raw)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            "Model did not return valid JSON for structured extraction."
        ) from exc
