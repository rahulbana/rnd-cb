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
distributions for the described domain. Use ONLY the exact enum values listed
above — do not invent others. For a two-valued/binary feature use
dtype "boolean" (not a "bernoulli" distribution). For a categorical feature use
dtype "category" and provide "categories"."""


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
            payload = self._sanitize_payload(payload)
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

    # LLMs reliably use vocabulary just outside our enums (e.g. "bernoulli",
    # "gaussian", "int"). Rather than reject the whole spec, coerce each field
    # to the nearest supported value at the boundary so the pipeline stays
    # robust to reasonable model variation.
    _DIST_ALIASES = {
        "gaussian": "normal", "norm": "normal",
        "binomial": "poisson", "geometric": "poisson", "discrete": "poisson",
        "categorical": "uniform", "uniform_int": "uniform", "randint": "uniform",
        "pareto": "powerlaw", "zipf": "powerlaw", "power": "powerlaw",
        "weibull": "gamma", "chi2": "gamma", "chisquare": "gamma",
        "log-normal": "lognormal", "log_normal": "lognormal",
        "expon": "exponential", "exp": "exponential",
    }
    _DTYPE_ALIASES = {
        "int": "integer", "int64": "integer", "long": "integer",
        "numeric": "float", "double": "float", "number": "float",
        "continuous": "float", "real": "float", "decimal": "float",
        "bool": "boolean", "binary": "boolean",
        "categorical": "category", "string": "category", "str": "category",
        "object": "category", "enum": "category", "nominal": "category",
        "date": "datetime", "timestamp": "datetime", "time": "datetime",
    }
    _VALID_DIST = {
        "normal", "uniform", "poisson", "gamma", "exponential",
        "lognormal", "beta", "powerlaw",
    }
    _VALID_DTYPE = {
        "integer", "float", "boolean", "category", "ordinal", "datetime",
        "uuid", "email", "phone", "url", "name", "text",
    }

    def _sanitize_payload(self, payload: dict) -> dict:
        for feature in payload.get("features", []) or []:
            if not isinstance(feature, dict):
                continue
            self._sanitize_dtype(feature)
            self._sanitize_distribution(feature)
            self._sanitize_params(feature)
        return payload

    def _sanitize_dtype(self, feature: dict) -> None:
        dtype = str(feature.get("dtype", "float")).strip().lower()
        dtype = self._DTYPE_ALIASES.get(dtype, dtype)
        if dtype not in self._VALID_DTYPE:
            dtype = "float"
        feature["dtype"] = dtype

    def _sanitize_distribution(self, feature: dict) -> None:
        dist = feature.get("distribution")
        if dist is None:
            return
        dist = str(dist).strip().lower()
        # "bernoulli"/binary distributions describe a two-valued column: model it
        # as a boolean rather than forcing a continuous distribution onto it.
        if dist in {"bernoulli", "binary", "boolean"}:
            feature["dtype"] = "boolean"
            feature["distribution"] = "normal"  # ignored for boolean columns
            return
        dist = self._DIST_ALIASES.get(dist, dist)
        if dist not in self._VALID_DIST:
            dist = "normal"
        feature["distribution"] = dist

    def _sanitize_params(self, feature: dict) -> None:
        params = feature.get("params")
        if not isinstance(params, dict):
            feature.pop("params", None)
            return
        clean: dict[str, float] = {}
        for key, value in params.items():
            try:
                clean[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
        feature["params"] = clean

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
