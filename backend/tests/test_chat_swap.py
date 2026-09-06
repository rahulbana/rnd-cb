"""Phase 7 EXIT TEST.

The same query streams a cited answer, and the LLM backend is swapped through
Ollama / OpenAI / Anthropic / Gemini by changing one env var -- no code touched.
The real providers need network + keys, so the swap is proven by the registry
resolving each implementation at the same call site (construction is lazy),
and the end-to-end streamed-cited-answer path is proven with the fake provider.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.registry import clear_registry_caches, get_llm_provider
from tests import fixtures


def test_one_env_var_swaps_all_four_backends(monkeypatch):
    names = ["ollama", "openai", "anthropic", "gemini"]
    resolved = []
    for provider in names:
        monkeypatch.setattr(settings, "LLM_PROVIDER", provider)
        clear_registry_caches()
        llm = get_llm_provider()  # identical call site for every provider
        resolved.append(llm.name)
    assert resolved == names  # each env value selects its backend


def test_same_query_streams_cited_answer(upload_client):
    upload_client.post(
        "/api/v1/documents",
        files={
            "file": (
                "bio.md",
                fixtures.make_markdown(body="the mitochondria is the powerhouse"),
                "text/markdown",
            )
        },
    )
    resp = upload_client.post(
        "/api/v1/chat/stream", json={"question": "what is the powerhouse"}
    )
    assert resp.status_code == 200
    # The streamed metadata carries citations for the grounded answer.
    assert "event: meta" in resp.text
    assert "document_id" in resp.text
    assert "data:" in resp.text
