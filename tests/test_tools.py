"""Tests for the individual tool factories."""

from __future__ import annotations

import pytest

from memory_agent.config import Settings
from memory_agent.tools import build_tools
from memory_agent.tools.base import extract_host
from memory_agent.tools.converters import make_converter_tools
from memory_agent.tools.datetime_tools import make_time_tools
from memory_agent.tools.memory import make_memory_tools
from memory_agent.tools.network import make_network_tools
from memory_agent.tools.text import make_text_tools
from memory_agent.tools.web import make_web_tools


def _by_name(tools):
    return {t.name: t for t in tools}


# --- registry -------------------------------------------------------------

def test_build_tools_registers_all(settings, memory):
    class FakeLLM:
        def invoke(self, m):
            return type("R", (), {"content": "x"})()

    names = [t.name for t in build_tools(settings, FakeLLM(), memory)]
    assert names == [
        "save_memory", "search_long_term_memory", "web_search",
        "convert_currency", "convert_units", "current_time", "ip_lookup",
        "draft_email", "summarize_text", "translate_text",
    ]


# --- helpers --------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("https://github.com/x/y", "github.com"),
    ("github.com", "github.com"),
    ("http://sub.example.org:8080/path", "sub.example.org"),
])
def test_extract_host(value, expected):
    assert extract_host(value) == expected


# --- unit converter (real, offline) --------------------------------------

def test_convert_units_length():
    convert_units = _by_name(make_converter_tools())["convert_units"]
    out = convert_units.invoke({"value": 10, "from_unit": "km", "to_unit": "mi"})
    assert "6.21" in out


def test_convert_units_temperature():
    convert_units = _by_name(make_converter_tools())["convert_units"]
    out = convert_units.invoke({"value": 72, "from_unit": "degF", "to_unit": "degC"})
    assert "22.2" in out


def test_convert_units_bad_unit_is_graceful():
    convert_units = _by_name(make_converter_tools())["convert_units"]
    out = convert_units.invoke({"value": 1, "from_unit": "km", "to_unit": "kilograms"})
    assert "Could not convert" in out


# --- currency converter (mocked HTTP) ------------------------------------

class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_convert_currency_success(monkeypatch):
    from memory_agent.tools import converters

    monkeypatch.setattr(
        converters.requests, "get",
        lambda url, timeout: _Resp({"result": "success", "rates": {"INR": 80.0}}),
    )
    convert_currency = _by_name(make_converter_tools())["convert_currency"]
    out = convert_currency.invoke({"amount": 100, "from_currency": "usd", "to_currency": "inr"})
    assert "8,000.00 INR" in out


def test_convert_currency_unknown_target(monkeypatch):
    from memory_agent.tools import converters

    monkeypatch.setattr(
        converters.requests, "get",
        lambda url, timeout: _Resp({"result": "success", "rates": {"INR": 80.0}}),
    )
    convert_currency = _by_name(make_converter_tools())["convert_currency"]
    out = convert_currency.invoke({"amount": 1, "from_currency": "USD", "to_currency": "XYZ"})
    assert "Unknown target currency" in out


def test_convert_currency_network_error_is_graceful(monkeypatch):
    from memory_agent.tools import converters

    def boom(url, timeout):
        raise ConnectionError("no network")

    monkeypatch.setattr(converters.requests, "get", boom)
    convert_currency = _by_name(make_converter_tools())["convert_currency"]
    out = convert_currency.invoke({"amount": 1, "from_currency": "USD", "to_currency": "EUR"})
    assert "Currency lookup failed" in out


# --- current time (real, offline) ----------------------------------------

@pytest.mark.parametrize("place,expected", [
    ("UTC", "Current time in UTC"),
    ("Japan", "Asia/Tokyo"),
    ("Tokyo", "Asia/Tokyo"),
    ("Asia/Kolkata", "Asia/Kolkata"),
])
def test_current_time_resolves(place, expected):
    current_time = _by_name(make_time_tools())["current_time"]
    assert expected in current_time.invoke({"timezone_or_place": place})


def test_current_time_unknown():
    current_time = _by_name(make_time_tools())["current_time"]
    assert "Couldn't resolve" in current_time.invoke({"timezone_or_place": "Nowhereland"})


# --- ip lookup (mocked DNS + geo) ----------------------------------------

def test_ip_lookup_success(monkeypatch):
    from memory_agent.tools import network

    monkeypatch.setattr(
        network.socket, "gethostbyname_ex",
        lambda host: (host, [], ["140.82.113.4"]),
    )
    monkeypatch.setattr(
        network.requests, "get",
        lambda url, timeout: _Resp({
            "status": "success", "city": "San Francisco",
            "regionName": "California", "country": "USA", "isp": "GitHub",
        }),
    )
    ip_lookup = _by_name(make_network_tools())["ip_lookup"]
    out = ip_lookup.invoke({"domain_or_url": "https://github.com"})
    assert "140.82.113.4" in out
    assert "San Francisco" in out


def test_ip_lookup_dns_failure(monkeypatch):
    from memory_agent.tools import network

    def boom(host):
        raise OSError("name resolution failed")

    monkeypatch.setattr(network.socket, "gethostbyname_ex", boom)
    ip_lookup = _by_name(make_network_tools())["ip_lookup"]
    assert "DNS lookup failed" in ip_lookup.invoke({"domain_or_url": "nope.invalid"})


# --- text tools (fake LLM) -----------------------------------------------

def test_text_tools_use_llm():
    class FakeLLM:
        def __init__(self):
            self.seen = []

        def invoke(self, messages):
            self.seen.append(messages)
            return type("R", (), {"content": "LLM-OUTPUT"})()

    llm = FakeLLM()
    tools = _by_name(make_text_tools(llm))
    assert tools["summarize_text"].invoke({"text": "long text"}) == "LLM-OUTPUT"
    assert tools["translate_text"].invoke(
        {"text": "hi", "target_language": "French"}
    ) == "LLM-OUTPUT"
    assert tools["draft_email"].invoke(
        {"recipient": "a@b.c", "subject": "s", "key_points": "k"}
    ) == "LLM-OUTPUT"
    assert len(llm.seen) == 3


# --- web search (no key) --------------------------------------------------

def test_web_search_without_key():
    web_search = _by_name(make_web_tools(Settings(tavily_api_key="")))["web_search"]
    assert "TAVILY_API_KEY is not set" in web_search.invoke({"query": "x"})


# --- memory tools (config-injected user_id) ------------------------------

def test_memory_tools_scope_by_config(memory):
    tools = _by_name(make_memory_tools(memory))
    cfg = {"configurable": {"user_id": "alice"}}
    tools["save_memory"].invoke({"fact": "User likes tea"}, config=cfg)
    assert memory.list_all("alice") == ["User likes tea"]
    out = tools["search_long_term_memory"].invoke({"query": "tea"}, config=cfg)
    assert "User likes tea" in out
