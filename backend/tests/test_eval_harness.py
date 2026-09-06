"""Heuristic eval harness scoring and pass/fail thresholds."""

from __future__ import annotations

import pytest

from app.adapters.eval_harnesses import HeuristicEvalHarness
from app.domain.models import EvalCase

pytestmark = pytest.mark.eval


@pytest.mark.asyncio
async def test_grounded_answer_passes():
    cases = [
        EvalCase(
            question="what is the capital of france",
            answer="the capital is paris located in france",
            contexts=["paris is the capital of france"],
            ground_truth="paris capital france",
        )
    ]
    card = await HeuristicEvalHarness().evaluate(cases, threshold=0.6)
    assert card.harness == "heuristic"
    assert card.cases == 1
    assert card.passed is True
    assert card.metric("faithfulness") >= 0.6
    assert {m.name for m in card.metrics} == {
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    }


@pytest.mark.asyncio
async def test_ungrounded_answer_fails():
    cases = [
        EvalCase(
            question="what is the capital of france",
            answer="bananas are yellow and grow on trees",
            contexts=["paris is the capital of france"],
            ground_truth="paris capital france",
        )
    ]
    card = await HeuristicEvalHarness().evaluate(cases, threshold=0.6)
    assert card.passed is False
    assert card.metric("faithfulness") < 0.6
