import pytest

from code_reviewer.config import extensions_for, normalize_language


def test_normalize_aliases():
    assert normalize_language("PY") == "python"
    assert normalize_language("golang") == "go"
    assert normalize_language("C++") == "cpp"


def test_extensions_for_known():
    assert ".py" in extensions_for("python")
    assert ".ts" in extensions_for("typescript")


def test_extensions_for_unknown():
    with pytest.raises(ValueError):
        extensions_for("cobol")
