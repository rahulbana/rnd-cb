from autodev.agent.parsing import extract_json
import pytest


def test_direct_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_fenced_json():
    text = 'sure!\n```json\n{"a": 1, "b": [1, 2]}\n```\ndone'
    assert extract_json(text) == {"a": 1, "b": [1, 2]}


def test_embedded_with_braces_in_string():
    text = 'prefix {"nested": {"x": "a}b"}} suffix'
    assert extract_json(text) == {"nested": {"x": "a}b"}}


def test_no_json_raises():
    with pytest.raises(ValueError):
        extract_json("no json here")
