"""Startup preflight checks.

Catches environment/dependency mismatches at boot with a clear, actionable
message instead of letting them surface as a confusing failure on the first
upload or chat request. The classic case: a ``transformers`` newer than the
installed PyTorch supports, which makes transformers silently disable PyTorch
so SentenceTransformers/CrossEncoder can't run.
"""
from __future__ import annotations

from ..config import get_settings
from .logging import get_logger

log = get_logger(__name__)


def check_ml_backend() -> list[str]:
    """Return a list of human-readable problems (empty means healthy)."""
    problems: list[str] = []
    settings = get_settings()

    # The embedding + reranker stack rides on PyTorch via transformers.
    if settings.embedding_provider != "sentence_transformer":
        return problems

    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        problems.append(
            f"PyTorch is not importable ({exc}). Install it: pip install torch"
        )
        return problems

    torch_version = getattr(torch, "__version__", "unknown")

    try:
        from transformers.utils import is_torch_available

        if not is_torch_available():
            problems.append(
                "transformers has DISABLED PyTorch (installed torch "
                f"{torch_version} is older than your transformers requires). "
                "Embeddings and the cross-encoder reranker will NOT work.\n"
                "        Fix (Intel macOS, torch capped at 2.2.2): "
                "pip install 'transformers<4.46' 'sentence-transformers<3.3'\n"
                "        Fix (Apple Silicon / Linux): pip install -U 'torch>=2.5'"
            )
    except Exception:  # transformers not installed yet — surfaced elsewhere
        pass

    return problems


def run_preflight() -> None:
    problems = check_ml_backend()
    if not problems:
        log.info("Preflight OK — ML backend (PyTorch/transformers) is healthy.")
        return
    bar = "!" * 72
    log.error(bar)
    log.error("PREFLIGHT FAILED — the RAG pipeline will not function correctly:")
    for problem in problems:
        log.error("  • %s", problem)
    log.error(bar)
