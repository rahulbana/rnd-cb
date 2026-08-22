"""Use an LLM to pull entities and relationships out of a text chunk.

This is the heart of graph construction: we ask the model to return a small
JSON object describing the nodes (entities) and edges (relationships) it finds.
We use OpenAI's JSON mode so parsing is reliable.
"""

import json

from . import config
from .ingest import Chunk

_SYSTEM_PROMPT = """\
You are an information-extraction engine that builds a knowledge graph.
Given a passage of text, identify the key entities and the relationships
between them.

Rules:
- Entities are specific people, organizations, places, products, concepts, or
  events. Normalize names (e.g. "the company" -> its actual name if known).
- Each relationship connects two entities you listed, with a short verb phrase
  describing how they relate (e.g. "founded", "located in", "works for").
- Only extract facts actually stated in the passage. Do not invent anything.
- Keep entity names concise and consistent so the same entity in different
  passages produces the same name.

Return ONLY JSON matching this schema:
{
  "entities": [
    {"name": "string", "type": "string", "description": "string"}
  ],
  "relationships": [
    {"source": "string", "target": "string", "relation": "string"}
  ]
}
"""


def extract_from_chunk(chunk: Chunk, client=None) -> dict:
    """Return {"entities": [...], "relationships": [...]} for one chunk."""
    client = client or config.get_client()

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Passage:\n\n{chunk.text}"},
        ],
    )

    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # If the model ever returns malformed JSON, skip this chunk gracefully
        # rather than crashing the whole build.
        return {"entities": [], "relationships": []}

    return {
        "entities": data.get("entities", []) or [],
        "relationships": data.get("relationships", []) or [],
    }
