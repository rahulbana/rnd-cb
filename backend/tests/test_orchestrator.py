"""Tests for the orchestration layer.

These tests inject fake agents so the pipeline can be verified without any
network access or OpenAI API key.
"""
from __future__ import annotations

import os
import sys

import pytest

# Ensure the backend package is importable when tests run from any directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas import Language  # noqa: E402
from app.services.orchestrator import CodeGenerationOrchestrator  # noqa: E402


class _FakePlanner:
    def plan(self, language, problem_statement):
        return ["Validate input", "Compute result", "Return value"]


class _FakeCoder:
    def write(self, language, problem_statement, plan):
        assert plan, "coder should receive a plan"
        return "def solve():\n    return 42", "Returns the answer."


class _FakeReviewer:
    def review(self, language, problem_statement, code):
        return code + "  # reviewed", ["Added a clarifying comment."]


def test_run_pipeline_wires_agents_together():
    orchestrator = CodeGenerationOrchestrator(
        planner=_FakePlanner(),
        coder=_FakeCoder(),
        reviewer=_FakeReviewer(),
    )
    result = orchestrator.run(Language.PYTHON, "Return the answer to everything")

    assert result.language == "Python"
    assert result.plan == ["Validate input", "Compute result", "Return value"]
    assert result.code.endswith("# reviewed")
    assert result.review_notes == ["Added a clarifying comment."]
    assert result.explanation == "Returns the answer."


def test_generate_request_rejects_blank_problem():
    from pydantic import ValidationError

    from app.schemas import GenerateRequest

    with pytest.raises(ValidationError):
        GenerateRequest(language=Language.PYTHON, problem_statement="   ")
