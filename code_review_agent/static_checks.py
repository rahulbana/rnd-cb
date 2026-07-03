"""Deterministic, non-LLM checks that act as guaranteed backstops.

Some issues are fully objective and should never depend on model judgement.
This module uses Python's :mod:`ast` to detect them directly and returns
:class:`~code_review_agent.models.Issue` objects that the engine merges into
the LLM findings. Today it covers:

* ``syntax``        -> a real syntax error (with line and message).
* ``documentation`` -> a missing module/class/function/method docstring.

Only Python is supported; for any other language this returns ``{}`` and the
review relies solely on the model.
"""

from __future__ import annotations

import ast
from typing import Dict, List

from .collector import normalize_language
from .models import Issue, Severity


def run_static_checks(
    file_path: str, language: str, content: str
) -> Dict[str, List[Issue]]:
    """Return deterministic issues keyed by review-category (Python only)."""

    if normalize_language(language) != "python":
        return {}

    lines = content.splitlines()

    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        line = exc.lineno if exc.lineno and exc.lineno > 0 else 1
        current = lines[line - 1] if 0 <= line - 1 < len(lines) else ""
        return {
            "syntax": [
                Issue(
                    explanation=f"Syntax error: {exc.msg}.",
                    line=line,
                    end_line=line,
                    current_code=current,
                    suggested_code="",
                    severity=Severity.HIGH.value,
                )
            ]
        }
    except (ValueError, RecursionError):
        # Malformed source (e.g. null bytes) — leave it to the model.
        return {}

    results: Dict[str, List[Issue]] = {}
    doc_issues = _docstring_issues(tree, lines)
    if doc_issues:
        results["documentation"] = doc_issues
    return results


def _indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _docstring_issues(tree: ast.Module, lines: List[str]) -> List[Issue]:
    """Flag every module/class/function/method that lacks a docstring."""

    issues: List[Issue] = []

    # Module-level docstring (only meaningful for a non-empty module).
    if tree.body and not ast.get_docstring(tree):
        issues.append(
            Issue(
                explanation="Module is missing a docstring.",
                line=1,
                end_line=1,
                current_code="",
                suggested_code='"""TODO: describe this module."""',
                severity=Severity.LOW.value,
            )
        )

    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        if ast.get_docstring(node):
            continue
        kind = "Class" if isinstance(node, ast.ClassDef) else "Function"
        issues.append(_missing_docstring_issue(node, kind, lines))

    issues.sort(key=lambda i: (i.line or 0))
    return issues


def _missing_docstring_issue(node, kind: str, lines: List[str]) -> Issue:
    """Build an Issue with the exact docstring insertion for ``node``."""

    def_idx = node.lineno - 1  # 0-based line of `def`/`class`
    first_body = node.body[0]

    if first_body.lineno > node.lineno:
        # Normal multi-line block: anchor on the line ending the signature
        # (the one with the colon) and match the body's indentation.
        anchor_idx = first_body.lineno - 2
        anchor_idx = max(def_idx, min(anchor_idx, len(lines) - 1))
        body_line = (
            lines[first_body.lineno - 1]
            if 0 <= first_body.lineno - 1 < len(lines)
            else ""
        )
        indent = _indent_of(body_line) or (_indent_of(lines[def_idx]) + "    ")
    else:
        # One-liner (`def f(): return x`) — anchor on the def line itself.
        anchor_idx = def_idx
        indent = _indent_of(lines[def_idx]) + "    "

    anchor = lines[anchor_idx] if 0 <= anchor_idx < len(lines) else ""
    doc_line = f'{indent}"""TODO: describe {node.name}."""'
    suggested = f"{anchor}\n{doc_line}" if anchor else doc_line

    return Issue(
        explanation=f"{kind} `{node.name}` is missing a docstring.",
        line=node.lineno,
        end_line=node.lineno,
        current_code=anchor,
        suggested_code=suggested,
        severity=Severity.LOW.value,
    )
