from code_reviewer.agents import build_agents
from code_reviewer.collector import collect_files
from code_reviewer.config import Settings
from code_reviewer.models import Severity
from code_reviewer.orchestrator import run_review


class FakeClient:
    """Duck-typed stand-in for LLMClient that returns canned findings."""

    def review(self, system_prompt, user_prompt):
        if "Security" in system_prompt:
            return {
                "summary": "Found a secret.",
                "findings": [
                    {
                        "title": "Hardcoded secret",
                        "severity": "critical",
                        "line": 1,
                        "description": "API key in source.",
                        "recommendation": "Move to env var.",
                    }
                ],
            }
        return {"summary": "Looks fine.", "findings": []}


def test_run_review_aggregates(tmp_path):
    (tmp_path / "app.py").write_text("API_KEY = 'sk-123'\n")
    settings = Settings(path=str(tmp_path), language="python", max_workers=2)
    files = collect_files(settings)
    agents = build_agents()

    report = run_review(settings, files, agents, client=FakeClient())

    assert len(report.files) == 1
    counts = report.severity_counts()
    assert counts[Severity.CRITICAL] == 1
    assert len(report.all_findings) == 1
    # Every agent produced a result for the file.
    assert len(report.files[0].results) == len(agents)
