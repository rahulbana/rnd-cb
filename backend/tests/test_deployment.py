"""Phase 10: secrets abstraction + deep readiness probe.

Proves the production-hardening seams work on fakes/defaults: the secret
provider swaps by one env var (env -> GCP Secret Manager) without importing a
cloud SDK, and the readiness probe reports datastore health (200 ready / 503
not-ready).
"""

from __future__ import annotations

import pytest

from app.adapters.secrets import EnvSecretProvider, GCPSecretManagerProvider
from app.core.config import settings
from app.core.registry import clear_registry_caches, get_secret_provider
from app.domain.interfaces import SecretProvider


def test_default_secret_provider_is_env() -> None:
    provider = get_secret_provider()
    assert isinstance(provider, EnvSecretProvider)
    assert isinstance(provider, SecretProvider)
    assert provider.name == "env"


def test_env_secret_provider_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("MY_SECRET", "s3cr3t")
    provider = EnvSecretProvider()
    assert provider.get("MY_SECRET") == "s3cr3t"
    assert provider.get("MISSING", default="fallback") == "fallback"
    assert provider.get("MISSING") is None


def test_env_secret_provider_honours_prefix(monkeypatch) -> None:
    monkeypatch.setenv("APP_TOKEN", "abc")
    provider = EnvSecretProvider(prefix="APP_")
    assert provider.get("TOKEN") == "abc"


def test_secret_provider_swap_to_gcp(monkeypatch) -> None:
    """Flipping SECRET_PROVIDER resolves the GCP adapter -- no SDK import."""
    monkeypatch.setattr(settings, "SECRET_PROVIDER", "gcp_secret_manager")
    monkeypatch.setattr(settings, "GCP_PROJECT_ID", "demo-project")
    clear_registry_caches()
    provider = get_secret_provider()
    assert isinstance(provider, GCPSecretManagerProvider)
    assert provider.name == "gcp_secret_manager"


def test_gcp_provider_requires_project_id() -> None:
    with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
        GCPSecretManagerProvider("")


def test_gcp_provider_construction_does_not_import_sdk(monkeypatch) -> None:
    """Constructing the adapter must not require google-cloud-secret-manager."""
    import sys

    monkeypatch.setitem(sys.modules, "google.cloud.secretmanager", None)
    # Construction + from_settings never touch the client, so this is safe even
    # with the SDK absent.
    monkeypatch.setattr(settings, "GCP_PROJECT_ID", "demo-project")
    provider = GCPSecretManagerProvider.from_settings(settings)
    assert provider._client is None


def test_readiness_ready_on_healthy_stack(upload_client) -> None:
    resp = upload_client.get("/api/v1/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
    # Task queue is inline in tests, so the Redis check is skipped.
    assert body["checks"]["redis"] == "skipped"


def test_readiness_503_when_database_unreachable(async_env, monkeypatch) -> None:
    client = async_env("inline")
    from app.db import base as dbbase

    monkeypatch.setattr(
        settings, "DATABASE_URL", "postgresql+psycopg://x:y@127.0.0.1:1/z"
    )
    dbbase.get_engine.cache_clear()
    dbbase._get_sessionmaker.cache_clear()

    resp = client.get("/api/v1/ready")
    assert resp.status_code == 503
    assert resp.json()["status"] == "not_ready"
    assert resp.json()["checks"]["database"].startswith("error")


def test_providers_endpoint_lists_phase10_wiring(upload_client) -> None:
    resp = upload_client.get("/api/v1/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["secret_provider"] == "env"
    assert "tracer" in body
