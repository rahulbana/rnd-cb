"""Offline tests for prompt construction and the two-agent pipeline.

These use a fake OpenAI client, so no API key or network access is needed.
"""

import types
import unittest

from history_agent import agent
from history_agent.dateparse import parse_date_input


class _FakeResponse:
    def __init__(self, text):
        self.output_text = text


class _FakeResponses:
    def __init__(self, recorder):
        self._recorder = recorder

    def create(self, **kwargs):
        self._recorder.append(kwargs)
        # Echo which agent ran, based on its instructions, so tests can assert order.
        role = "verifier" if "fact-checking editor" in kwargs["instructions"] else "researcher"
        return _FakeResponse(f"{role} output")


class _FakeClient:
    def __init__(self):
        self.calls = []
        self.responses = _FakeResponses(self.calls)


class PromptTests(unittest.TestCase):
    def test_exact_date_prompt_mentions_exact_day(self):
        p = agent.build_prompt(parse_date_input("7 July 1984"))
        self.assertIn("7th July 1984", p)
        self.assertIn("exact date", p)

    def test_day_month_prompt_mentions_all_years(self):
        p = agent.build_prompt(parse_date_input("21 July"))
        self.assertIn("21st July", p)
        self.assertIn("all", p.lower())

    def test_country_focus_included(self):
        p = agent.build_prompt(parse_date_input("21 July"), country="India")
        self.assertIn("India", p)

    def test_verification_prompt_wraps_draft(self):
        parsed = parse_date_input("21 July")
        p = agent.build_verification_prompt(parsed, "DRAFT BODY HERE")
        self.assertIn("DRAFT BODY HERE", p)
        self.assertIn("DRAFT REPORT START", p)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.fake = _FakeClient()
        self._orig = agent._build_client
        agent._build_client = lambda api_key: self.fake

    def tearDown(self):
        agent._build_client = self._orig

    def test_investigate_runs_researcher_then_verifier(self):
        parsed = parse_date_input("21 July")
        stages = []
        result = agent.investigate(parsed, on_stage=stages.append)

        self.assertEqual(stages, ["research", "verify"])
        self.assertEqual(len(self.fake.calls), 2)
        # First call is the researcher, second is the verifier.
        self.assertIn("historical researcher", self.fake.calls[0]["instructions"])
        self.assertIn("fact-checking editor", self.fake.calls[1]["instructions"])
        # The verifier receives the researcher's draft in its input.
        self.assertIn("researcher output", self.fake.calls[1]["input"])
        self.assertEqual(result.markdown, "verifier output")

    def test_investigate_no_verify_skips_second_agent(self):
        parsed = parse_date_input("21 July")
        stages = []
        result = agent.investigate(parsed, verify=False, on_stage=stages.append)

        self.assertEqual(stages, ["research"])
        self.assertEqual(len(self.fake.calls), 1)
        self.assertEqual(result.markdown, "researcher output")

    def test_web_search_tool_is_requested(self):
        parsed = parse_date_input("7 July 1984")
        agent.investigate(parsed, verify=False)
        self.assertEqual(
            self.fake.calls[0]["tools"], [{"type": "web_search"}]
        )


if __name__ == "__main__":
    unittest.main()
