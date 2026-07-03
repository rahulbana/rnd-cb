"""The review engine: orchestrates OpenAI calls with retries and concurrency."""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

from openai import (
    APIConnectionError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
    InternalServerError,
)

from .collector import TargetFile
from .config import Settings
from .models import CategoryFinding, FileReview, ReviewCategory, ReviewReport, Severity
from .prompts import (
    SYSTEM_PROMPT,
    build_response_schema,
    build_user_prompt,
)

logger = logging.getLogger("code_review_agent")

_RETRYABLE = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)
_VALID_SEVERITIES = {s.value for s in Severity}


class ReviewEngine:
    """Reviews files by delegating to an OpenAI chat model."""

    def __init__(self, settings: Settings, client: Optional[OpenAI] = None) -> None:
        self.settings = settings
        self.categories: List[ReviewCategory] = settings.resolved_categories()
        self.client = client or OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.request_timeout,
            max_retries=0,  # we implement our own backoff below
        )
        self._schema = build_response_schema(self.categories)

    # -- public API ---------------------------------------------------------
    def review_files(
        self,
        targets: List[TargetFile],
        *,
        target_label: str,
        progress: Optional[Callable[[FileReview], None]] = None,
    ) -> ReviewReport:
        """Review every target, optionally in parallel, and build a report."""

        report = ReviewReport(target=target_label, model=self.settings.model)
        results: Dict[str, FileReview] = {}

        workers = max(1, min(self.settings.concurrency, len(targets)))
        if workers == 1:
            for target in targets:
                review = self.review_file(target)
                results[target.path] = review
                if progress:
                    progress(review)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self.review_file, t): t.path for t in targets
                }
                for future in as_completed(futures):
                    review = future.result()
                    results[futures[future]] = review
                    if progress:
                        progress(review)

        # Preserve the deterministic input order in the final report.
        report.reviews = [results[t.path] for t in targets]
        return report

    def review_file(self, target: TargetFile) -> FileReview:
        """Review a single file and normalise the model response."""

        try:
            raw = self._call_model(target)
            findings = self._parse(raw)
            return FileReview(
                file=target.path, language=target.language, findings=findings
            )
        except Exception as exc:  # noqa: BLE001 - surfaced per-file, never fatal
            logger.warning("Failed to review %s: %s", target.path, exc)
            return FileReview(
                file=target.path,
                language=target.language,
                findings={},
                error=str(exc),
            )

    # -- internals ----------------------------------------------------------
    def _call_model(self, target: TargetFile) -> str:
        user_prompt = build_user_prompt(
            file_path=target.path,
            language=target.language,
            code=target.content,
            categories=self.categories,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Optional[Exception] = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.model,
                    messages=messages,
                    temperature=self.settings.temperature,
                    max_tokens=self.settings.max_tokens,
                    response_format=self._response_format(),
                )
                content = response.choices[0].message.content or ""
                if not content.strip():
                    raise ValueError("Model returned an empty response.")
                return content
            except _RETRYABLE as exc:
                last_error = exc
                if attempt < self.settings.max_retries:
                    delay = 2 ** attempt
                    logger.info(
                        "Retryable error on %s (attempt %d/%d): %s; sleeping %ds",
                        target.path,
                        attempt + 1,
                        self.settings.max_retries,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise
        # Should be unreachable, but keep the type checker and runtime honest.
        raise last_error or RuntimeError("Model call failed for an unknown reason.")

    def _response_format(self) -> dict:
        """Prefer strict json_schema; the SDK falls back cleanly if unsupported."""

        return {
            "type": "json_schema",
            "json_schema": {
                "name": "code_review",
                "strict": True,
                "schema": self._schema,
            },
        }

    def _parse(self, raw: str) -> Dict[str, CategoryFinding]:
        data = _loads_lenient(raw)
        findings: Dict[str, CategoryFinding] = {}
        for category in self.categories:
            entry = data.get(category.key) or {}
            findings[category.key] = _coerce_finding(entry)
        return findings


def _loads_lenient(raw: str) -> dict:
    """Parse JSON, tolerating models that wrap output in prose or code fences."""

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = raw[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            pass
    raise ValueError("Model response was not valid JSON.")


def _coerce_finding(entry: dict) -> CategoryFinding:
    """Coerce an arbitrary dict into a well-formed :class:`CategoryFinding`."""

    if not isinstance(entry, dict):
        return CategoryFinding(status=0, explanation="No data returned.", suggestion="")

    status = 1 if entry.get("status") in (1, "1", True) else 0
    explanation = str(entry.get("explanation", "")).strip()
    suggestion = str(entry.get("suggestion", "")).strip()

    severity = str(entry.get("severity", "")).strip().lower()
    if severity not in _VALID_SEVERITIES:
        severity = Severity.MEDIUM.value if status == 1 else Severity.NONE.value
    if status == 0:
        severity = Severity.NONE.value

    return CategoryFinding(
        status=status,
        explanation=explanation,
        suggestion=suggestion,
        severity=severity,
    )
