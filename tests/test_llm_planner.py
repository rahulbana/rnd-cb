"""Tests for the optional LLM planner.

The network call is monkeypatched, so these run offline without the ``openai``
SDK or an API key. They verify (a) a well-formed OpenAI JSON response becomes a
valid ``DatasetSpec`` and (b) any failure falls back to the heuristic planner.
"""

import json

from app.agents.llm_planner import LLMPlanner
from app.models.spec import TaskType


def test_openai_json_response_parsed(monkeypatch):
    payload = {
        "name": "fraud_llm",
        "description": "fraud dataset",
        "domain": "banking",
        "task_type": "binary_classification",
        "n_rows": 4321,
        "features": [
            {"name": "amount", "dtype": "float", "distribution": "lognormal",
             "params": {"mean": 3.0, "sigma": 1.0}, "description": "amount"},
            {"name": "channel", "dtype": "category",
             "categories": ["online", "pos"], "description": "channel"},
        ],
        "target": {"name": "is_fraud", "positive_rate": 0.03, "n_classes": 2,
                   "signal_strength": 0.7, "nonlinear": False},
        "quality": {"missing_rate": 0.0, "duplicate_rate": 0.0,
                    "outlier_rate": 0.0, "noise": 0.0},
    }

    planner = LLMPlanner()
    monkeypatch.setattr(planner, "_call_llm", lambda prompt: json.dumps(payload))

    spec = planner.plan("make me a fraud dataset")
    assert spec.task_type == TaskType.BINARY_CLASSIFICATION
    assert spec.n_rows == 4321
    assert spec.target.name == "is_fraud"
    assert abs(spec.target.positive_rate - 0.03) < 1e-9
    assert spec.metadata["prompt"] == "make me a fraud dataset"


def test_openai_response_with_prose_wrapper(monkeypatch):
    """Model sometimes wraps JSON in prose/fences; we extract the object."""

    payload = {"name": "d", "task_type": "regression", "n_rows": 100,
               "features": [{"name": "x", "dtype": "float"}],
               "target": {"name": "y"}}
    wrapped = "Here is your spec:\n```json\n" + json.dumps(payload) + "\n```"
    planner = LLMPlanner()
    monkeypatch.setattr(planner, "_call_llm", lambda prompt: wrapped)
    spec = planner.plan("a regression dataset")
    assert spec.task_type == TaskType.REGRESSION
    assert spec.n_rows == 100


def test_llm_failure_falls_back_to_heuristic(monkeypatch):
    def boom(prompt):
        raise RuntimeError("no api key")

    planner = LLMPlanner()
    monkeypatch.setattr(planner, "_call_llm", boom)
    spec = planner.plan("telecom churn dataset with 5000 customers and 10% churn")
    # Heuristic fallback still produces a sensible spec.
    assert spec.task_type == TaskType.BINARY_CLASSIFICATION
    assert spec.n_rows == 5000
    assert abs(spec.target.positive_rate - 0.10) < 1e-9
