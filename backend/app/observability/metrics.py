"""Prometheus metrics for application and agent observability.

Metric naming follows Prometheus conventions (``_total`` for counters,
``_seconds`` for durations). Labels are kept low-cardinality on purpose — never
label by raw user query.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# ---- HTTP (application) ----
HTTP_REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)
HTTP_IN_PROGRESS = Gauge(
    "http_requests_in_progress", "In-progress HTTP requests", ["method", "path"]
)

# ---- Agent (runs) ----
AGENT_RUNS = Counter("agent_runs_total", "Agent runs by outcome", ["status"])
AGENT_RUNS_IN_PROGRESS = Gauge("agent_runs_in_progress", "Agent runs currently active")
AGENT_RUN_DURATION = Histogram(
    "agent_run_duration_seconds",
    "End-to-end agent run duration",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120),
)
AGENT_SOURCES = Histogram(
    "agent_sources_found",
    "Unique sources gathered per run",
    buckets=(0, 1, 2, 5, 10, 15, 20, 30, 50),
)

# ---- Agent (nodes) ----
NODE_DURATION = Histogram(
    "agent_node_duration_seconds", "Per-node execution time", ["node"]
)

# ---- Providers ----
SEARCH_CALLS = Counter(
    "search_calls_total", "Search provider calls", ["provider", "status"]
)
SEARCH_RESULTS = Counter(
    "search_results_total", "Results returned by search providers", ["provider"]
)
LLM_CALLS = Counter("llm_calls_total", "LLM invocations", ["model", "kind"])
LLM_TOKENS = Counter("llm_tokens_streamed_total", "Streamed LLM chunks", ["model"])


@asynccontextmanager
async def observe_node(node: str):
    """Time an agent node and record it under the ``node`` label."""
    start = time.perf_counter()
    try:
        yield
    finally:
        NODE_DURATION.labels(node=node).observe(time.perf_counter() - start)


def render_latest() -> tuple[bytes, str]:
    """Return (payload, content_type) for the /metrics endpoint."""
    return generate_latest(), CONTENT_TYPE_LATEST
