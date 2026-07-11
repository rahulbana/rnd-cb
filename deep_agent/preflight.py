"""Preflight validation.

Fast, offline-friendly checks that catch misconfiguration *before* a run
starts — a missing API key or an unreachable broker — so the pipeline fails
fast with an actionable message instead of part-way through.
"""
from __future__ import annotations

from dataclasses import dataclass

from deep_agent.config import (
    CheckpointBackend,
    LLMProvider,
    SearchProvider,
    Settings,
    get_settings,
)
from deep_agent.utils.logging import get_logger

logger = get_logger("preflight")

# Obvious placeholder values copied from .env.example that mean "unset".
_PLACEHOLDERS = {"", "sk-...", "sk-ant-...", "tvly-...", "...", "changeme"}


@dataclass
class CheckResult:
    """Outcome of a single preflight check."""

    name: str
    ok: bool
    detail: str
    critical: bool = True


def _key_present(value: str | None) -> bool:
    return bool(value) and value.strip() not in _PLACEHOLDERS


def _check_llm(settings: Settings) -> CheckResult:
    provider = settings.llm_provider
    key = (
        settings.openai_api_key
        if provider is LLMProvider.OPENAI
        else settings.anthropic_api_key
    )
    env_name = "OPENAI_API_KEY" if provider is LLMProvider.OPENAI else "ANTHROPIC_API_KEY"
    if _key_present(key):
        return CheckResult(f"LLM ({provider.value})", True, f"{env_name} is set")
    return CheckResult(
        f"LLM ({provider.value})",
        False,
        f"{env_name} is missing — set it in your environment or .env",
    )


def _check_search(settings: Settings) -> CheckResult:
    provider = settings.search_provider
    key = (
        settings.tavily_api_key
        if provider is SearchProvider.TAVILY
        else settings.serper_api_key
    )
    env_name = "TAVILY_API_KEY" if provider is SearchProvider.TAVILY else "SERPER_API_KEY"
    if _key_present(key):
        return CheckResult(f"Search ({provider.value})", True, f"{env_name} is set")
    return CheckResult(
        f"Search ({provider.value})",
        False,
        f"{env_name} is missing — set it in your environment or .env",
    )


def _check_broker(settings: Settings) -> CheckResult:
    """Ping the Celery broker; skipped (non-critical) in eager mode."""

    if settings.celery_task_always_eager:
        return CheckResult(
            "Celery broker",
            True,
            "eager mode — scraping/search run inline (broker not needed)",
            critical=False,
        )
    url = settings.celery_broker_url
    try:
        if url.startswith("redis://") or url.startswith("rediss://"):
            import redis

            client = redis.from_url(url, socket_connect_timeout=3)
            client.ping()
            return CheckResult("Celery broker", True, f"reachable at {url}")
        return CheckResult(
            "Celery broker", True, f"{url} (reachability not verified)", critical=False
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Celery broker", False, f"unreachable at {url}: {exc}")


def _check_checkpoint(settings: Settings) -> CheckResult:
    if settings.checkpoint_backend is not CheckpointBackend.SQLITE:
        return CheckResult(
            "Checkpointer",
            True,
            f"{settings.checkpoint_backend.value}",
            critical=False,
        )
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: F401

        return CheckResult(
            "Checkpointer",
            True,
            f"sqlite → {settings.checkpoint_db}",
            critical=False,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "Checkpointer",
            False,
            f"sqlite backend selected but unavailable: {exc}",
            critical=False,
        )


def _check_langfuse(settings: Settings) -> CheckResult:
    if not settings.langfuse_enabled:
        return CheckResult("Langfuse tracing", True, "disabled", critical=False)
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return CheckResult(
            "Langfuse tracing",
            False,
            "enabled but LANGFUSE_PUBLIC_KEY/SECRET_KEY missing",
            critical=False,
        )
    try:
        import langfuse  # noqa: F401

        return CheckResult(
            "Langfuse tracing", True, f"enabled → {settings.langfuse_host}", critical=False
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "Langfuse tracing",
            False,
            f"enabled but package unavailable: {exc}",
            critical=False,
        )


def run_preflight(settings: Settings | None = None) -> list[CheckResult]:
    """Run all preflight checks and return their results."""

    settings = settings or get_settings()
    checks = [
        _check_llm(settings),
        _check_search(settings),
        _check_broker(settings),
        _check_checkpoint(settings),
        _check_langfuse(settings),
    ]
    for check in checks:
        level = logger.info if check.ok else logger.error
        level("preflight %-22s %s — %s", check.name, "OK" if check.ok else "FAIL", check.detail)
    return checks


def preflight_ok(results: list[CheckResult]) -> bool:
    """True when no *critical* check failed."""

    return all(r.ok for r in results if r.critical)
