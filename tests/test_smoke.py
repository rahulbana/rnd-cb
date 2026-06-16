"""Lightweight smoke tests that do not require network or an API key.

They exercise the pure-Python parts: model construction, request formatting,
filename slugging, and the dry-run downloader.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qpaper_agent.agents.downloader import DownloaderAgent, _slugify  # noqa: E402
from qpaper_agent.config import Settings  # noqa: E402
from qpaper_agent.models import (  # noqa: E402
    PaperCandidate,
    PaperRequest,
    ValidatedPaper,
)


def _settings(tmp: str) -> Settings:
    return Settings(
        openai_api_key="test-key",
        model="gpt-4o",
        search_model="gpt-4o",
        output_dir=tmp,
        request_timeout=10,
        max_candidates=25,
    )


def test_request_describe():
    req = PaperRequest(board="CBSE", subject="English", klass="10", years=[2023])
    text = req.describe()
    assert "CBSE" in text and "English" in text and "10" in text and "2023" in text


def test_slugify_is_filesystem_safe():
    assert _slugify("CBSE Class 10 / English 2023!") == "CBSE_Class_10_English_2023"
    assert _slugify("") == "paper"


def test_dry_run_downloader_writes_nothing(tmp_path):
    agent = DownloaderAgent(_settings(str(tmp_path)), dry_run=True)
    cand = PaperCandidate(
        title="Sample", url="https://example.com/p.pdf", source="example.com"
    )
    vp = ValidatedPaper(candidate=cand, is_valid=True, confidence=0.9, reason="ok")
    results = agent.run([vp], subdir="cbse")

    assert len(results) == 1
    assert results[0].success is True
    assert "dry-run" in (results[0].error or "")
    # Nothing should actually be written in dry-run mode.
    assert not os.listdir(tmp_path)


def test_settings_requires_api_key():
    s = Settings(
        openai_api_key="",
        model="m",
        search_model="m",
        output_dir="d",
        request_timeout=1,
        max_candidates=1,
    )
    try:
        s.require_api_key()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
