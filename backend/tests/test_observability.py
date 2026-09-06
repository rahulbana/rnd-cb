"""Tracer + eval-harness registry swaps and the noop tracer."""

from __future__ import annotations

from app.adapters.eval_harnesses import HeuristicEvalHarness, RagasEvalHarness
from app.adapters.tracers import NoopTracer, OTelTracer
from app.core.config import settings
from app.core.registry import (
    clear_registry_caches,
    get_eval_harness,
    get_tracer,
)


def test_tracer_swap(monkeypatch):
    for provider, cls in [("noop", NoopTracer), ("otel", OTelTracer)]:
        monkeypatch.setattr(settings, "TRACER_PROVIDER", provider)
        clear_registry_caches()
        assert isinstance(get_tracer(), cls)


def test_eval_harness_swap(monkeypatch):
    for provider, cls in [
        ("heuristic", HeuristicEvalHarness),
        ("ragas", RagasEvalHarness),
    ]:
        monkeypatch.setattr(settings, "EVAL_HARNESS", provider)
        clear_registry_caches()
        assert isinstance(get_eval_harness(), cls)


def test_noop_span_is_a_context_manager():
    tracer = NoopTracer()
    with tracer.span("x", a=1, b="two"):
        pass  # no-op, must not raise


def test_otel_tracer_constructs_without_sdk():
    # Construction must not import OpenTelemetry.
    assert OTelTracer.from_settings(settings).name == "otel"
