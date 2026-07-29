"""Langfuse tracing for the agent (OpenTelemetry-based).

Langfuse v4 instruments the OpenAI Agents SDK via OpenInference, so every agent
run, LLM call, and tool call (MCP client-directory calls, web search, currency)
is captured as a span and sent to Langfuse — no per-call wiring needed.

Design:
- Fully **optional and gated**: tracing turns on only when both Langfuse keys are
  present. With no keys, `configure_langfuse()` is a no-op and the app runs
  normally.
- **Soft dependency**: if the observability extra isn't installed, we print a
  hint and continue instead of crashing.

Enable by setting LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY (and optionally
LANGFUSE_HOST) in your .env, and installing: `pip install -e ".[observability]"`.
"""

from __future__ import annotations

import os

from rich.console import Console

from agentic_app.config import get_settings

console = Console()

_client = None  # cached Langfuse client
_instrumented = False


def configure_langfuse() -> bool:
    """Enable Langfuse tracing if configured. Returns True when active."""
    global _client, _instrumented

    settings = get_settings()
    if not settings.langfuse_enabled:
        return False

    # Langfuse (and its OTEL exporter) read credentials from the environment.
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key  # type: ignore[assignment]
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key  # type: ignore[assignment]
    os.environ["LANGFUSE_HOST"] = settings.langfuse_host

    try:
        from langfuse import get_client
        from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
    except ImportError:
        console.print(
            "[yellow]Langfuse keys are set but the observability packages are missing.[/]\n"
            "[yellow]Install them with:[/] pip install -e \".[observability]\""
        )
        return False

    _client = get_client()
    if not _instrumented:
        OpenAIAgentsInstrumentor().instrument()
        _instrumented = True

    # auth_check is best-effort: a failure (e.g. offline) shouldn't break the app.
    try:
        if _client.auth_check():
            console.print(f"[dim]Langfuse tracing enabled → {settings.langfuse_host}[/]")
        else:
            console.print("[yellow]Langfuse auth check failed — verify your keys/host.[/]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]Langfuse auth check skipped: {exc}[/]")

    return True


def flush_langfuse() -> None:
    """Flush any buffered spans. Call before the process exits so nothing is lost."""
    if _client is not None:
        try:
            _client.flush()
        except Exception:  # noqa: BLE001 - never fail shutdown on telemetry
            pass
