"""Tests for the tools that don't need network access."""

import math

import pytest

from yeai.tools.calculator import safe_eval
from yeai.tools.units import LENGTH_TOOL


def test_calculator_basic_arithmetic():
    assert safe_eval("2 + 3 * 4") == 14
    assert safe_eval("(2 + 3) * 4") == 20
    assert safe_eval("10 / 4") == 2.5
    assert safe_eval("10 % 3") == 1


def test_calculator_named_functions():
    assert safe_eval("sqrt(144)") == 12
    assert safe_eval("square(9)") == 81
    assert safe_eval("cube(3)") == 27
    assert safe_eval("percent(15, 200)") == 30
    assert math.isclose(safe_eval("pi"), math.pi)


def test_calculator_rejects_unsafe_input():
    with pytest.raises(Exception):
        safe_eval("__import__('os').system('echo hi')")
    with pytest.raises(Exception):
        safe_eval("open('x')")


def test_length_conversion_cm_to_m():
    assert LENGTH_TOOL.run(value=250, from_unit="cm", to_unit="m") == "250 cm = 2.5 m"


def test_length_conversion_m_to_cm():
    assert LENGTH_TOOL.run(value=3, from_unit="m", to_unit="cm") == "3 m = 300 cm"


def test_length_conversion_unknown_unit():
    out = LENGTH_TOOL.run(value=1, from_unit="parsec", to_unit="m")
    assert out.startswith("ERROR")


def test_registry_has_expected_tools():
    from yeai.tools.base import build_registry

    names = set(build_registry())
    assert {
        "web_search",
        "convert_currency",
        "calculator",
        "convert_length",
        "country_summary",
        "time_and_weather",
    } <= names
