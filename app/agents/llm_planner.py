"""Optional LLM-backed planner.

This is intentionally thin and dependency-light. It asks an LLM to translate the
user's prompt into a :class:`DatasetSpec` JSON payload, validates it with
Pydantic, and falls back to the heuristic planner on any error. It is only
loaded when ``PLANNER_BACKEND=llm``.

The default provider is OpenAI (``LLM_PROVIDER=openai``, key from
``OPENAI_API_KEY``); ``anthropic`` and ``litellm`` are also supported. The prompt
asks for a strict JSON object matching the ``DatasetSpec`` schema, so the same
downstream pipeline consumes the result unchanged regardless of provider.
"""

from __future__ import annotations

import json
import os

from app.agents.base import Agent
from app.agents.planner import HeuristicPlanner
from app.config import settings
from app.models.spec import DatasetSpec

SYSTEM_PROMPT = """You are a data engineering planner. Given a user request for
a machine learning dataset, output a single JSON object matching this schema:

{
  "name": str, "description": str, "domain": str,
  "task_type": one of ["binary_classification","multiclass_classification",
     "multilabel_classification","regression","clustering","time_series"],
  "n_rows": int,
  "features": [{"name": str, "dtype": one of ["integer","float","boolean",
     "category","ordinal","datetime"], "distribution": one of ["normal",
     "uniform","poisson","gamma","exponential","lognormal","beta","powerlaw"],
     "params": {..}, "categories": [str]|null, "description": str}],
  "target": {"name": str, "positive_rate": float, "n_classes": int,
     "signal_strength": float, "nonlinear": bool} | null,
  "quality": {"missing_rate": float, "duplicate_rate": float,
     "outlier_rate": float, "noise": float}
}

Return ONLY the JSON object, no prose. Choose realistic feature names and
distributions for the described domain."""


class LLMPlanner(Agent):
    name = "planner"

    def __init__(self) -> None:
        self._fallback = HeuristicPlanner()

    def run(self, prompt: str) -> DatasetSpec:
        return self.plan(prompt)

    def plan(self, prompt: str) -> DatasetSpec:
        try:
            raw = self._call_llm(prompt)
            payload = json.loads(self._extract_json(raw))
            payload.setdefault("metadata", {})["prompt"] = prompt
            spec = DatasetSpec.model_validate(payload)
            self.log(f"LLM planned {len(spec.features)} features")
            return spec
        except Exception as exc:
            self.log(f"LLM planning failed ({exc}); using heuristic fallback")
            return self._fallback.plan(prompt)

    def _extract_json(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("no JSON object in LLM response")
        return text[start : end + 1]

    def _call_llm(self, prompt: str) -> str:
        """Call the configured provider (``LLM_PROVIDER``)."""

        provider = settings.llm_provider
        if provider == "openai":
            return self._call_openai(prompt)
        if provider == "anthropic":
            return self._call_anthropic(prompt)

        # Generic multi-provider fallback via litellm if installed.
        import litellm  # type: ignore

        resp = litellm.completion(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return resp["choices"][0]["message"]["content"]

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI Chat Completions with JSON-object response format.

        Reads the API key from ``OPENAI_API_KEY`` and honours ``OPENAI_BASE_URL``
        for Azure/OpenAI-compatible gateways when set.
        """

        from openai import OpenAI  # type: ignore

        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic  # type: ignore

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model=settings.llm_model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")
