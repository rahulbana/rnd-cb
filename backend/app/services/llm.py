"""OpenAI-backed text-to-SQL generation and explanation.

Uses structured (JSON) output so the API always returns a predictable shape.
"""
from __future__ import annotations

import json
import re

from openai import OpenAI

from ..config import Settings

# JSON schema the model is asked to conform to for generation.
_GENERATION_SCHEMA = {
    "name": "sql_generation",
    "schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "A single read-only SELECT query."},
            "explanation": {
                "type": "string",
                "description": "Plain-language explanation of what the query does.",
            },
            "tables_used": {
                "type": "array",
                "items": {"type": "string"},
            },
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Assumptions made when the schema was ambiguous.",
            },
        },
        "required": ["sql", "explanation", "tables_used", "assumptions"],
        "additionalProperties": False,
    },
    "strict": True,
}

_GENERATION_SYSTEM_PROMPT = """\
You are an expert data analyst that translates natural-language questions into \
SQL for the {dialect} dialect.

Hard rules:
- Produce exactly ONE statement, and it MUST be read-only: a SELECT (optionally \
  with a leading WITH ... clause). Never emit INSERT, UPDATE, DELETE, DROP, \
  ALTER, CREATE, TRUNCATE, GRANT or any statement that changes data or schema.
- Use only tables and columns that appear in the provided schema. If the schema \
  is empty or a needed field is missing, make a reasonable assumption and record \
  it in "assumptions".
- Prefer explicit column lists over SELECT *. Add a sensible LIMIT when the user \
  asks for "top", "first", or a specific count.
- Write clean, readable SQL.

Return your answer as JSON matching the requested schema."""


class LLMNotConfiguredError(RuntimeError):
    """Raised when generation is attempted without an API key."""


def _client(settings: Settings) -> OpenAI:
    if not settings.llm_configured:
        raise LLMNotConfiguredError(
            "OPENAI_API_KEY is not set. Add it to backend/.env to enable generation."
        )
    kwargs: dict = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:sql|json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    return fence.group(1).strip() if fence else text


def generate_sql(
    question: str,
    schema_text: str,
    dialect: str,
    settings: Settings,
) -> dict:
    """Return {sql, explanation, tables_used, assumptions}."""
    client = _client(settings)

    schema_block = schema_text.strip() or "(No schema provided — infer reasonable table/column names.)"
    user_content = (
        f"Database schema:\n{schema_block}\n\n"
        f"Question:\n{question.strip()}"
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {"role": "system", "content": _GENERATION_SYSTEM_PROMPT.format(dialect=dialect)},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_schema", "json_schema": _GENERATION_SCHEMA},
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    data["sql"] = _strip_code_fence(data.get("sql", ""))
    data.setdefault("explanation", "")
    data.setdefault("tables_used", [])
    data.setdefault("assumptions", [])
    return data


def explain_sql(
    sql: str,
    schema_text: str,
    dialect: str,
    settings: Settings,
) -> str:
    """Return a plain-language explanation of an existing SQL query."""
    client = _client(settings)

    schema_block = schema_text.strip()
    schema_part = f"\n\nSchema for context:\n{schema_block}" if schema_block else ""
    prompt = (
        f"Explain the following {dialect} SQL query in clear, concise language for "
        f"someone who is not a SQL expert. Describe what it returns, how it filters "
        f"and aggregates, and any noteworthy behaviour. Use short paragraphs or "
        f"bullet points.{schema_part}\n\nSQL:\n{sql.strip()}"
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a helpful SQL tutor."},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()
