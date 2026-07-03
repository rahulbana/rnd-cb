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
    BadRequestError,
    OpenAI,
    RateLimitError,
    InternalServerError,
)

from .collector import TargetFile
from .config import Settings
from .dependencies import (
    Definition,
    SymbolIndex,
    build_symbol_index,
    collect_manifests,
    iter_source_files,
    resolve_dependencies,
)
from .models import (
    CategoryFinding,
    FileReview,
    Issue,
    ReviewReport,
    Severity,
    SEVERITY_ORDER,
)
from .prompts import (
    SYSTEM_PROMPT,
    build_response_schema,
    build_user_prompt,
)
from .reviewers.base import Reviewer
from .static_checks import run_static_checks

logger = logging.getLogger("code_review_agent")

_RETRYABLE = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)
_VALID_SEVERITIES = {s.value for s in Severity}
_ISSUE_SEVERITIES = _VALID_SEVERITIES - {Severity.NONE.value}


class ReviewEngine:
    """Reviews files by delegating to an OpenAI chat model."""

    def __init__(self, settings: Settings, client: Optional[OpenAI] = None) -> None:
        self.settings = settings
        self.reviewers: List[Reviewer] = settings.resolved_reviewers()
        self.client = client or OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.request_timeout,
            max_retries=0,  # we implement our own backoff below
        )
        # Group reviewers by the LLM model they run on. Reviewers that share a
        # model are batched into a single call; a reviewer with its own model
        # (from config) forms its own group. This keeps the common case at one
        # call per file while allowing a distinct model per reviewer.
        self._groups: Dict[str, List[Reviewer]] = {}
        for reviewer in self.reviewers:
            model_name = reviewer.model or settings.model
            self._groups.setdefault(model_name, []).append(reviewer)
        self._schemas: Dict[str, dict] = {
            model_name: build_response_schema(revs)
            for model_name, revs in self._groups.items()
        }
        self._index: SymbolIndex = {}
        self._manifests: List[tuple] = []
        # Some models/gateways do not support strict json_schema output. When
        # that is detected we fall back to json_object mode for the rest of the
        # run (the prompt already fully specifies the required JSON shape).
        self._use_json_object = False

    # -- public API ---------------------------------------------------------
    def review_files(
        self,
        targets: List[TargetFile],
        *,
        target_label: str,
        context_dir: Optional[str] = None,
        progress: Optional[Callable[[FileReview], None]] = None,
    ) -> ReviewReport:
        """Review every target, optionally in parallel, and build a report.

        ``context_dir`` is scanned (in addition to the target files) to build
        the symbol index used for dependency resolution, so cross-file callee
        definitions can be supplied to the reviewer.
        """

        if self.settings.resolve_dependencies:
            self._index = self._build_index(targets, context_dir)
        if self.settings.include_manifests:
            self._manifests = collect_manifests(
                context_dir, max_chars=self.settings.max_manifest_chars
            )

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
        """Review a single file (chunking large files) and merge findings."""

        try:
            dependencies = self._dependencies_for(target)
            chunks = self._split(target.content)
            merged: Dict[str, CategoryFinding] = {}
            for offset, chunk in chunks:
                chunk_findings: Dict[str, CategoryFinding] = {}
                for model_name, reviewers in self._groups.items():
                    raw = self._call_model(
                        target, chunk, offset, dependencies, reviewers, model_name
                    )
                    chunk_findings.update(self._parse(raw, reviewers))
                merged = _merge(merged, chunk_findings)
            if not merged:  # empty file edge-case
                merged = {r.key: CategoryFinding(status=0) for r in self.reviewers}
            if self.settings.static_checks:
                self._apply_static_checks(target, merged)
            return FileReview(
                file=target.path, language=target.language, findings=merged
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
    def _build_index(
        self, targets: List[TargetFile], context_dir: Optional[str]
    ) -> SymbolIndex:
        """Index definitions from the targets plus any surrounding project dir."""

        language = targets[0].language if targets else ""
        sources: Dict[str, tuple] = {
            t.path: (t.language, t.content) for t in targets
        }
        if context_dir:
            for path, content in iter_source_files(
                context_dir,
                language,
                max_files=self.settings.max_index_files,
                max_bytes=self.settings.max_file_bytes,
            ):
                sources.setdefault(path, (language, content))
        return build_symbol_index(
            (path, lang, content) for path, (lang, content) in sources.items()
        )

    def _dependencies_for(self, target: TargetFile) -> List[Definition]:
        if not self.settings.resolve_dependencies or not self._index:
            return []
        return resolve_dependencies(
            file_path=target.path,
            language=target.language,
            content=target.content,
            index=self._index,
            max_defs=self.settings.max_dependency_defs,
            max_chars=self.settings.max_dependency_chars,
        )

    def _apply_static_checks(
        self, target: TargetFile, merged: Dict[str, CategoryFinding]
    ) -> None:
        """Merge guaranteed deterministic findings into the LLM results."""

        try:
            static = run_static_checks(
                target.path, target.language, target.content
            )
        except Exception as exc:  # noqa: BLE001 - never let a backstop break review
            logger.warning("Static checks failed for %s: %s", target.path, exc)
            return

        enabled = {r.key for r in self.reviewers}
        for key, issues in static.items():
            if key not in enabled:
                continue  # reviewer disabled in config -> skip its backstop too
            finding = merged.get(key)
            if finding is None:
                finding = CategoryFinding(status=0)
                merged[key] = finding
            # De-dupe only against lines the model already reported (so the
            # same finding is not listed twice). We must NOT dedupe deterministic
            # issues against each other: distinct symbols can share a line
            # (e.g. a module docstring and a function both anchored at line 1).
            was_clean = finding.status != 1  # model reported nothing here
            llm_lines = {i.line for i in finding.issues if i.line is not None}
            added = False
            for issue in issues:
                if issue.line is not None and issue.line in llm_lines:
                    continue
                finding.issues.append(issue)
                added = True
            if not finding.issues:
                continue
            finding.status = 1
            finding.severity = _worst_severity(finding.issues) or finding.severity
            if added:
                # Re-sort by line so deterministic and model issues interleave.
                finding.issues.sort(key=lambda i: (i.line or 0))
                # If the model had said this category was clean, its "ok"-style
                # summary is now stale — replace it so the report is coherent.
                if was_clean or not finding.explanation:
                    finding.explanation = (
                        "Issues detected by deterministic checks."
                    )
                if was_clean or not finding.suggestion:
                    finding.suggestion = "Apply the fixes shown for each issue."

    def _split(self, code: str):
        """Yield ``(line_offset, chunk_text)`` pairs, splitting large files."""

        lines = code.splitlines()
        limit = max(50, self.settings.chunk_lines)
        if len(lines) <= limit:
            return [(0, code)]
        chunks = []
        for start in range(0, len(lines), limit):
            chunk_lines = lines[start : start + limit]
            chunks.append((start, "\n".join(chunk_lines)))
        return chunks

    def _call_model(
        self,
        target: TargetFile,
        chunk: str,
        offset: int,
        dependencies: List[Definition],
        reviewers: List[Reviewer],
        model_name: str,
    ) -> str:
        user_prompt = build_user_prompt(
            file_path=target.path,
            language=target.language,
            code=chunk,
            categories=reviewers,
            line_offset=offset,
            dependencies=dependencies,
            manifests=self._manifests,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        schema = self._schemas[model_name]

        # ``attempts`` counts only retryable-error retries against the budget;
        # the one-time json_schema -> json_object fallback is independent so it
        # never gets starved even when ``max_retries`` is 0.
        attempts = 0
        fallback_tried = False
        while True:
            try:
                return self._once(messages, model_name, schema)
            except BadRequestError as exc:
                if (
                    not self._use_json_object
                    and not fallback_tried
                    and _is_response_format_error(exc)
                ):
                    logger.info(
                        "json_schema unsupported for model '%s'; falling back "
                        "to json_object mode.",
                        model_name,
                    )
                    self._use_json_object = True
                    fallback_tried = True
                    continue
                raise
            except _RETRYABLE as exc:
                if attempts < self.settings.max_retries:
                    delay = 2 ** attempts
                    attempts += 1
                    logger.info(
                        "Retryable error on %s (attempt %d/%d): %s; sleeping %ds",
                        target.path,
                        attempts,
                        self.settings.max_retries,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise
        # Unreachable: every path above returns or raises.

    def _once(self, messages: List[dict], model_name: str, schema: dict) -> str:
        """Make a single model call and return its non-empty text content."""

        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            response_format=self._response_format(schema),
        )
        content = response.choices[0].message.content or ""
        if not content.strip():
            raise ValueError("Model returned an empty response.")
        return content

    def _response_format(self, schema: dict) -> dict:
        """Return the response_format, preferring strict json_schema.

        Falls back to ``json_object`` for the rest of the run once a model or
        gateway is found not to support ``json_schema`` (see ``_call_model``).
        """

        if self._use_json_object:
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "code_review",
                "strict": True,
                "schema": schema,
            },
        }

    def _parse(
        self, raw: str, reviewers: List[Reviewer]
    ) -> Dict[str, CategoryFinding]:
        data = _loads_lenient(raw)
        findings: Dict[str, CategoryFinding] = {}
        for reviewer in reviewers:
            entry = data.get(reviewer.key) or {}
            findings[reviewer.key] = _coerce_finding(entry)
        return findings


def _is_response_format_error(exc: BadRequestError) -> bool:
    """Heuristic: does this 400 indicate json_schema/response_format is unsupported?"""

    text = str(getattr(exc, "message", "") or exc).lower()
    return "response_format" in text or "json_schema" in text or "json schema" in text


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


def _to_int_or_none(value) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_issue(entry: dict) -> Optional[Issue]:
    if not isinstance(entry, dict):
        return None
    severity = str(entry.get("severity", "")).strip().lower()
    if severity not in _ISSUE_SEVERITIES:
        severity = Severity.MEDIUM.value
    return Issue(
        explanation=str(entry.get("explanation", "")).strip(),
        line=_to_int_or_none(entry.get("line")),
        end_line=_to_int_or_none(entry.get("end_line")),
        current_code=str(entry.get("current_code", "")),
        suggested_code=str(entry.get("suggested_code", "")),
        severity=severity,
    )


def _coerce_finding(entry: dict) -> CategoryFinding:
    """Coerce an arbitrary dict into a well-formed :class:`CategoryFinding`."""

    if not isinstance(entry, dict):
        return CategoryFinding(status=0, explanation="No data returned.", suggestion="")

    raw_issues = entry.get("issues")
    issues: List[Issue] = []
    if isinstance(raw_issues, list):
        for item in raw_issues:
            coerced = _coerce_issue(item)
            if coerced is not None:
                issues.append(coerced)

    status = 1 if entry.get("status") in (1, "1", True) else 0
    # If the model flagged status but gave no issues, keep status; if it gave
    # issues but forgot status, treat it as an issue. This makes the two
    # signals self-consistent and robust to sloppy responses.
    if issues:
        status = 1

    explanation = str(entry.get("explanation", "")).strip()
    suggestion = str(entry.get("suggestion", "")).strip()

    severity = str(entry.get("severity", "")).strip().lower()
    if status == 0:
        severity = Severity.NONE.value
    else:
        worst = _worst_severity(issues)
        if severity not in _ISSUE_SEVERITIES:
            severity = worst or Severity.MEDIUM.value
        elif worst and SEVERITY_ORDER[worst] > SEVERITY_ORDER[severity]:
            severity = worst

    return CategoryFinding(
        status=status,
        explanation=explanation,
        suggestion=suggestion,
        severity=severity,
        issues=issues,
    )


def _worst_severity(issues: List[Issue]) -> Optional[str]:
    if not issues:
        return None
    return max((i.severity for i in issues), key=lambda s: SEVERITY_ORDER.get(s, 0))


def _merge(
    base: Dict[str, CategoryFinding], new: Dict[str, CategoryFinding]
) -> Dict[str, CategoryFinding]:
    """Merge per-chunk findings: OR statuses, concat issues, keep worst severity."""

    if not base:
        return new
    for key, finding in new.items():
        if key not in base:
            base[key] = finding
            continue
        existing = base[key]
        existing.issues.extend(finding.issues)
        if finding.status == 1:
            existing.status = 1
        # Merge summaries without losing information.
        if finding.explanation and finding.explanation not in existing.explanation:
            existing.explanation = (
                f"{existing.explanation} {finding.explanation}".strip()
            )
        if finding.suggestion and finding.suggestion not in existing.suggestion:
            existing.suggestion = (
                f"{existing.suggestion} {finding.suggestion}".strip()
            )
        worst = _worst_severity(existing.issues)
        existing.severity = (
            worst or Severity.NONE.value if existing.status == 1 else Severity.NONE.value
        )
    return base
