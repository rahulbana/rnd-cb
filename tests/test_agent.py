"""Unit tests that exercise the agent without hitting the OpenAI API."""

from __future__ import annotations

import json
import os

import pytest

from code_review_agent.collector import (
    CollectorError,
    collect,
    extensions_for,
    normalize_language,
)
from code_review_agent.config import DEFAULT_CATEGORIES, Settings
from code_review_agent.formatter import render, to_review_json
from code_review_agent.models import CategoryFinding, FileReview, ReviewReport
from code_review_agent.prompts import build_response_schema, build_user_prompt
from code_review_agent.reviewer import ReviewEngine


# --------------------------------------------------------------------------
# A fake OpenAI client so tests are hermetic and free.
# --------------------------------------------------------------------------
class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _FakeCompletions:
    def __init__(self, payload):
        self._payload = payload

    def create(self, **kwargs):  # noqa: D401 - mimic OpenAI SDK signature
        return _Resp(self._payload)


class _FakeChat:
    def __init__(self, payload):
        self.completions = _FakeCompletions(payload)


class _FakeClient:
    def __init__(self, payload):
        self.chat = _FakeChat(payload)


def _payload_all_categories(status=0):
    return json.dumps(
        {
            c.key: {
                "status": status,
                "severity": "high" if status else "none",
                "explanation": "test",
                "suggestion": "fix" if status else "",
                "issues": (
                    [
                        {
                            "line": 3,
                            "end_line": 3,
                            "severity": "high",
                            "explanation": "problem here",
                            "current_code": "os.system(cmd)",
                            "suggested_code": "subprocess.run(shlex.split(cmd), check=True)",
                        }
                    ]
                    if status
                    else []
                ),
            }
            for c in DEFAULT_CATEGORIES
        }
    )


def _settings():
    return Settings(api_key="test-key", model="gpt-4o-mini", concurrency=2)


# --------------------------------------------------------------------------
# Collector
# --------------------------------------------------------------------------
def test_normalize_language_aliases():
    assert normalize_language("Py") == "python"
    assert normalize_language("JS") == "javascript"
    assert normalize_language("golang") == "go"
    assert normalize_language("c++") == "cpp"


def test_extensions_for_known_language():
    assert ".py" in extensions_for("python")
    assert extensions_for("unknown-lang") == set()


def test_collect_single_file(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    targets = collect(str(f), "python")
    assert len(targets) == 1
    assert targets[0].language == "python"
    assert "x = 1" in targets[0].content


def test_collect_directory_filters_by_language(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.js").write_text("var y = 2;\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "c.py").write_text("ignored = True\n")

    targets = collect(str(tmp_path), "python")
    paths = {os.path.basename(t.path) for t in targets}
    assert paths == {"a.py"}  # b.js excluded, node_modules pruned


def test_collect_missing_path():
    with pytest.raises(CollectorError):
        collect("/does/not/exist", "python")


def test_collect_empty_directory(tmp_path):
    with pytest.raises(CollectorError):
        collect(str(tmp_path), "python")


# --------------------------------------------------------------------------
# Prompts / schema
# --------------------------------------------------------------------------
def test_schema_has_all_categories():
    schema = build_response_schema(DEFAULT_CATEGORIES)
    assert set(schema["required"]) == {c.key for c in DEFAULT_CATEGORIES}


def test_user_prompt_contains_code_and_keys():
    prompt = build_user_prompt(
        file_path="x.py",
        language="python",
        code="print('hi')",
        categories=DEFAULT_CATEGORIES,
    )
    assert "print('hi')" in prompt
    assert "security" in prompt


# --------------------------------------------------------------------------
# Review engine (with fake client)
# --------------------------------------------------------------------------
def test_review_file_clean():
    engine = ReviewEngine(_settings(), client=_FakeClient(_payload_all_categories(0)))
    from code_review_agent.collector import TargetFile

    review = engine.review_file(TargetFile("x.py", "python", "x = 1"))
    assert review.ok
    assert review.issue_count == 0
    assert set(review.findings) == {c.key for c in DEFAULT_CATEGORIES}


def test_review_file_with_issue():
    engine = ReviewEngine(_settings(), client=_FakeClient(_payload_all_categories(1)))
    from code_review_agent.collector import TargetFile

    review = engine.review_file(TargetFile("x.py", "python", "eval(x)"))
    assert not review.ok
    assert review.issue_count == len(DEFAULT_CATEGORIES)
    assert review.findings["security"].severity == "high"


def test_review_file_includes_exact_code_fix():
    engine = ReviewEngine(_settings(), client=_FakeClient(_payload_all_categories(1)))
    from code_review_agent.collector import TargetFile

    review = engine.review_file(TargetFile("x.py", "python", "os.system(cmd)"))
    issue = review.findings["security"].issues[0]
    assert issue.line == 3
    assert issue.current_code == "os.system(cmd)"
    assert "subprocess.run" in issue.suggested_code


def test_status_inferred_from_issues_when_missing():
    from code_review_agent.reviewer import _coerce_finding

    finding = _coerce_finding(
        {
            "status": 0,  # model contradicts itself
            "issues": [
                {"line": 1, "severity": "critical", "explanation": "x",
                 "current_code": "a", "suggested_code": "b"}
            ],
        }
    )
    assert finding.status == 1
    assert finding.severity == "critical"


def test_large_file_is_chunked_and_merged():
    from code_review_agent.collector import TargetFile

    settings = _settings()
    settings.chunk_lines = 50
    engine = ReviewEngine(settings, client=_FakeClient(_payload_all_categories(1)))
    big = "\n".join(f"line{i}" for i in range(130))  # 3 chunks of 50
    review = engine.review_file(TargetFile("big.py", "python", big))
    # Each chunk contributes one issue per category -> 3 issues merged.
    assert len(review.findings["security"].issues) == 3


def test_review_handles_bad_json():
    engine = ReviewEngine(_settings(), client=_FakeClient("not json at all"))
    from code_review_agent.collector import TargetFile

    review = engine.review_file(TargetFile("x.py", "python", "x = 1"))
    assert review.error  # error captured, not raised


def test_review_lenient_json_extraction():
    wrapped = "Here you go:\n```json\n" + _payload_all_categories(0) + "\n```"
    engine = ReviewEngine(_settings(), client=_FakeClient(wrapped))
    from code_review_agent.collector import TargetFile

    review = engine.review_file(TargetFile("x.py", "python", "x = 1"))
    assert review.ok


def test_review_files_preserves_order():
    from code_review_agent.collector import TargetFile

    engine = ReviewEngine(_settings(), client=_FakeClient(_payload_all_categories(0)))
    targets = [TargetFile(f"f{i}.py", "python", "x = 1") for i in range(5)]
    report = engine.review_files(targets, target_label="dir")
    assert [r.file for r in report.reviews] == [t.path for t in targets]


# --------------------------------------------------------------------------
# Formatter
# --------------------------------------------------------------------------
def test_review_json_single_file_is_object():
    review = FileReview(
        file="x.py",
        language="python",
        findings={"security": CategoryFinding(status=1, explanation="e", suggestion="s", severity="high")},
    )
    report = ReviewReport(target="x.py", model="m", reviews=[review])
    out = json.loads(to_review_json(report))
    assert out["security"]["status"] == 1


def test_review_json_multi_file_is_list():
    reviews = [
        FileReview(file=f"f{i}.py", language="python", findings={
            "security": CategoryFinding(status=0)
        })
        for i in range(2)
    ]
    report = ReviewReport(target="dir", model="m", reviews=reviews)
    out = json.loads(to_review_json(report))
    assert isinstance(out, list)
    assert out[0]["file"] == "f0.py"


def test_render_full_json_has_summary():
    review = FileReview(file="x.py", language="python", findings={
        "security": CategoryFinding(status=1)
    })
    report = ReviewReport(target="x.py", model="m", reviews=[review])
    out = json.loads(render(report, "json"))
    assert out["summary"]["total_issues"] == 1


# --------------------------------------------------------------------------
# Dependency resolution
# --------------------------------------------------------------------------
def test_extract_definitions_python():
    from code_review_agent.dependencies import extract_definitions

    code = "def helper(a, b):\n    return a + b\n\nclass Foo:\n    def m(self):\n        pass\n"
    defs = {d.name for d in extract_definitions("u.py", "python", code)}
    assert {"helper", "Foo", "m"} <= defs


def test_find_call_names():
    from code_review_agent.dependencies import find_call_names

    names = find_call_names("result = helper(1, 2)\nobj.method(x)\n", "python")
    assert "helper" in names and "method" in names
    assert "len" not in names  # stopword


def test_resolve_dependencies_cross_file():
    from code_review_agent.dependencies import (
        build_symbol_index,
        resolve_dependencies,
    )

    helper_src = "def charge(amount):\n    return amount * 100\n"
    caller_src = "from billing import charge\nx = charge(10, 20)\n"
    index = build_symbol_index([("billing.py", "python", helper_src)])

    deps = resolve_dependencies(
        file_path="caller.py",
        language="python",
        content=caller_src,
        index=index,
    )
    assert len(deps) == 1
    assert deps[0].name == "charge"
    assert "def charge(amount)" in deps[0].snippet


def test_resolve_skips_same_file_definitions():
    from code_review_agent.dependencies import (
        build_symbol_index,
        resolve_dependencies,
    )

    src = "def helper():\n    return 1\n\nx = helper()\n"
    index = build_symbol_index([("same.py", "python", src)])
    deps = resolve_dependencies(
        file_path="same.py", language="python", content=src, index=index
    )
    assert deps == []  # helper is already visible in the reviewed file


def test_dependency_block_rendered_in_prompt():
    from code_review_agent.dependencies import Definition
    from code_review_agent.prompts import build_user_prompt

    dep = Definition(
        name="charge", kind="function", file="billing.py",
        start_line=1, end_line=2, snippet="def charge(amount):\n    return amount",
    )
    prompt = build_user_prompt(
        file_path="caller.py", language="python", code="charge(1, 2)",
        categories=DEFAULT_CATEGORIES, dependencies=[dep],
    )
    assert "DEPENDENCY DEFINITIONS" in prompt
    assert "def charge(amount)" in prompt


def test_engine_resolves_dependencies_end_to_end(tmp_path):
    from code_review_agent.collector import TargetFile

    (tmp_path / "billing.py").write_text("def charge(amount):\n    return amount * 100\n")
    caller = tmp_path / "caller.py"
    caller.write_text("from billing import charge\nx = charge(10, 20)\n")

    settings = _settings()
    engine = ReviewEngine(settings, client=_FakeClient(_payload_all_categories(0)))
    target = TargetFile(str(caller), "python", caller.read_text())
    engine.review_files([target], target_label=str(caller), context_dir=str(tmp_path))
    deps = engine._dependencies_for(target)
    assert any(d.name == "charge" for d in deps)


def test_render_pretty_runs():
    review = FileReview(file="x.py", language="python", findings={
        "security": CategoryFinding(status=1, explanation="bad", suggestion="fix", severity="high")
    })
    report = ReviewReport(target="x.py", model="m", reviews=[review])
    text = render(report, "pretty", color=False)
    assert "x.py" in text and "security" in text
