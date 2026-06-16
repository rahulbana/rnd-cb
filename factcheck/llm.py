"""OpenAI-backed reasoning steps: query drafting and the grounded verdict.

Two strict rules govern the LLM usage here:

1. The model may help *phrase search queries* (a language task), but it never
   decides whether the claim is true at that stage.
2. The verdict step is shown ONLY the text gathered from the web. The system
   prompt forbids the use of prior/parametric knowledge and forces an
   ``UNVERIFIED`` result when the sources are insufficient.
"""

from __future__ import annotations

import json
from typing import List

from openai import OpenAI

from .models import FactCheckResult, Source

QUERY_SYSTEM_PROMPT = """\
You are a research assistant that turns a claim into effective web search queries.
Your ONLY job is to produce search strings — you must NOT judge whether the claim
is true or false.

Generate diverse queries that would help an investigator gather evidence:
- at least one neutral query about the core facts,
- at least one query phrased to CONFIRM the claim,
- at least one query phrased to REFUTE or debunk the claim,
- include named entities, dates, and numbers from the claim where useful.

Respond ONLY with JSON of the form: {"queries": ["...", "..."]}.
"""

VERDICT_SYSTEM_PROMPT = """\
You are a strict, evidence-bound fact-checking engine.

ABSOLUTE RULES:
1. Base your judgment EXCLUSIVELY on the numbered SOURCES provided by the user.
2. You are FORBIDDEN from using prior knowledge, training data, memorized facts,
   intuition, or assumptions. If you "know" something but it is not in the
   sources, you must ignore it.
3. Every key finding must be supported by at least one specific source index.
4. If the sources do not contain enough relevant information to evaluate the
   claim, you MUST return verdict "UNVERIFIED" — do not guess.
5. If sources conflict, weigh them, state the conflict, and reflect the
   uncertainty in your confidence score.

VERDICT VALUES:
- "TRUE": sources clearly support the claim.
- "FALSE": sources clearly contradict the claim.
- "PARTIALLY_TRUE": some parts supported, others contradicted or unsupported.
- "UNVERIFIED": insufficient or irrelevant evidence in the sources.

Respond ONLY with JSON matching this schema:
{
  "verdict": "TRUE" | "FALSE" | "PARTIALLY_TRUE" | "UNVERIFIED",
  "confidence": <float 0.0-1.0>,
  "summary": "<2-4 sentence conclusion grounded in the sources>",
  "key_findings": ["<finding with source refs like [2]>", ...],
  "source_assessments": [
    {"index": <int>, "stance": "SUPPORTS"|"REFUTES"|"NEUTRAL", "note": "<one line>"}
  ]
}
"""


class Reasoner:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def generate_queries(self, claim: str, max_queries: int = 4) -> List[str]:
        user = (
            f"Claim to investigate:\n{claim}\n\n"
            f"Produce up to {max_queries} search queries."
        )
        raw = self._json_completion(QUERY_SYSTEM_PROMPT, user)
        queries = raw.get("queries", []) if isinstance(raw, dict) else []
        cleaned = [q.strip() for q in queries if isinstance(q, str) and q.strip()]
        # Always keep the raw claim as a fallback query.
        if claim not in cleaned:
            cleaned.append(claim)
        return cleaned[:max_queries] if len(cleaned) > max_queries else cleaned

    def verdict(self, claim: str, sources: List[Source]) -> FactCheckResult:
        if not sources:
            return FactCheckResult(
                verdict="UNVERIFIED",  # type: ignore[arg-type]
                confidence=0.0,
                summary="No web sources could be gathered for this claim.",
                key_findings=[],
                source_assessments=[],
            )

        evidence = "\n\n".join(self._format_source(s) for s in sources)
        user = (
            f"CLAIM TO EVALUATE:\n{claim}\n\n"
            f"SOURCES (this is the ONLY information you may use):\n\n{evidence}"
        )
        raw = self._json_completion(VERDICT_SYSTEM_PROMPT, user)
        return FactCheckResult.model_validate(raw)

    @staticmethod
    def _format_source(source: Source, max_chars: int = 4000) -> str:
        body = source.content[:max_chars]
        return (
            f"[{source.index}] {source.title}\n"
            f"URL: {source.url}\n"
            f"CONTENT: {body}"
        )

    def _json_completion(self, system: str, user: str) -> dict:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
