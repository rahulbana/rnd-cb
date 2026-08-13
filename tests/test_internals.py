"""Unit tests for testgen's provider-independent logic.

These run without any network or LLM by injecting a fake provider.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from testgen import languages
from testgen.collector import collect
from testgen.generator import _strip_code_fences, generate_for_file
from testgen.llm.base import LLMProvider


class FakeProvider(LLMProvider):
    """Returns a fixed test body so we can exercise the write path offline."""

    def __init__(self, body: str = "def test_placeholder():\n    assert True\n"):
        super().__init__(model="fake")
        self._body = body

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self._body


def test_detect_python():
    spec = languages.detect(Path("foo.py"))
    assert spec is not None
    assert spec.framework == "pytest"
    assert spec.test_filename(Path("foo.py")) == "test_foo.py"


def test_detect_unsupported():
    assert languages.detect(Path("foo.md")) is None


@pytest.mark.parametrize(
    "raw,expected_first",
    [
        ("```python\ndef test_x():\n    pass\n```", "def test_x():"),
        ("def test_x():\n    pass", "def test_x():"),
        ("```\nplain\n```", "plain"),
    ],
)
def test_strip_code_fences(raw, expected_first):
    assert _strip_code_fences(raw).splitlines()[0] == expected_first


def test_collect_single_file(tmp_path: Path):
    src = tmp_path / "mod.py"
    src.write_text("x = 1\n")
    assert collect(src) == [src.resolve()]


def test_collect_skips_tests_and_ignores(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "test_a.py").write_text("x = 1\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "b.py").write_text("x = 1\n")
    (tmp_path / "readme.md").write_text("# hi\n")
    found = {p.name for p in collect(tmp_path)}
    assert found == {"a.py"}


def test_generate_writes_alongside(tmp_path: Path):
    src = tmp_path / "mod.py"
    src.write_text("def f():\n    return 1\n")
    result = generate_for_file(src, FakeProvider(), root=tmp_path)
    assert result.written
    assert result.test_path.name == "test_mod.py"
    assert result.test_path.read_text().startswith("def test_placeholder")


def test_generate_respects_existing(tmp_path: Path):
    src = tmp_path / "mod.py"
    src.write_text("x = 1\n")
    (tmp_path / "test_mod.py").write_text("# already here\n")
    result = generate_for_file(src, FakeProvider(), root=tmp_path)
    assert not result.written
    assert result.skipped_reason and "exists" in result.skipped_reason


def test_generate_output_dir_mirrors_tree(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    src = pkg / "mod.py"
    src.write_text("x = 1\n")
    out = tmp_path / "gen_tests"
    result = generate_for_file(src, FakeProvider(), root=tmp_path, output_dir=out)
    assert result.written
    assert result.test_path == (out / "pkg" / "test_mod.py").resolve()
