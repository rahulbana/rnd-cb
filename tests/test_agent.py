"""Offline tests — no real API key or network needed.

We inject a fake OpenAI client so we can exercise the agent's parsing and the
CLI rendering without hitting OpenAI.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from festival_agent.agent import FestivalAgent, FestivalResult  # noqa: E402
from festival_agent import cli  # noqa: E402


class _FakeCompletions:
    def __init__(self, payload: dict):
        self._payload = payload
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        message = SimpleNamespace(content=json.dumps(self._payload))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeClient:
    def __init__(self, payload: dict):
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload))


def _sample_payload():
    return {
        "festival": "Diwali",
        "year": 1984,
        "found": True,
        "date": "1984-11-13",
        "date_range": "11 Nov - 15 Nov 1984",
        "day_of_week": "Tuesday",
        "notes": "Diwali spans five days; the main day (Lakshmi Puja) is listed.",
        "confidence": "high",
    }


def test_lookup_parses_structured_response():
    agent = FestivalAgent(client=_FakeClient(_sample_payload()))
    result = agent.lookup("Diwali", 1984)
    assert isinstance(result, FestivalResult)
    assert result.festival == "Diwali"
    assert result.year == 1984
    assert result.found is True
    assert result.date == "1984-11-13"
    assert result.confidence == "high"


def test_lookup_sends_year_in_prompt():
    fake = _FakeClient(_sample_payload())
    FestivalAgent(client=fake).lookup("Diwali", 1984)
    sent = fake.chat.completions.last_kwargs["messages"][-1]["content"]
    assert "1984" in sent
    assert "Diwali" in sent


def test_not_found_payload():
    payload = _sample_payload()
    payload.update({"found": False, "date": "", "confidence": "low"})
    agent = FestivalAgent(client=_FakeClient(payload))
    result = agent.ask("When was Brigadoon festival in 1700?")
    assert result.found is False
    assert result.date == ""


def test_cli_renders_without_crashing(capsys, monkeypatch):
    monkeypatch.setattr(
        cli, "FestivalAgent", lambda **_: FestivalAgent(client=_FakeClient(_sample_payload()))
    )
    rc = cli.main(["Diwali", "1984", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "1984-11-13" in out


if __name__ == "__main__":
    test_lookup_parses_structured_response()
    test_lookup_sends_year_in_prompt()
    test_not_found_payload()
    print("All non-pytest assertions passed.")
