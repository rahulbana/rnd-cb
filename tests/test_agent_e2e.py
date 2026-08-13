"""End-to-end: the agent plans, generates, sets up a venv, writes + runs tests.

Uses an offline stub LLM so no network/API key is needed, but exercises the
real orchestrator, sandbox, venv creation and subprocess test execution.
"""
import asyncio
from pathlib import Path

from stub_provider import StubProvider

from autodev.agent import AutoDevAgent
from autodev.models import ProjectStatus
from autodev.services import project_service as svc


def _run(project_id, provider):
    agent = AutoDevAgent(project_id, provider=provider)
    asyncio.run(agent.run())


def test_full_build_passes_tests():
    project = svc.create_project("Build a tiny adder library in Python")
    pid = project["id"]

    _run(pid, StubProvider())

    p = svc.get_project(pid)
    assert p["status"] == ProjectStatus.completed.value, p

    # Files landed on disk in the isolated sandbox.
    workspace = Path(p["workspace_path"])
    assert (workspace / "adder.py").exists()
    assert (workspace / "test_adder.py").exists()
    assert (workspace / ".venv").exists()

    # A "done" event recorded success + passing tests.
    events = svc.get_events(pid)
    done = [e for e in events if e["type"] == "done"]
    assert done, "expected a done event"
    assert done[-1]["data"]["success"] is True
    assert done[-1]["data"]["tests_passed"] is True

    artifacts = {a["path"] for a in svc.get_artifacts(pid)}
    assert {"adder.py", "test_adder.py"} <= artifacts


def test_plan_approval_gate_and_resume():
    project = svc.create_project(
        "Build a tiny adder library in Python", require_approval=True
    )
    pid = project["id"]

    # First run should stop at the approval gate after planning.
    _run(pid, StubProvider())
    p = svc.get_project(pid)
    assert p["status"] == ProjectStatus.awaiting_approval.value, p
    assert p["plan"], "plan should be persisted for review"
    assert svc.get_artifacts(pid) == [], "no code generated before approval"

    events = svc.get_events(pid)
    assert any(e["type"] == "approval" for e in events)

    # Approve by resuming — build should now complete.
    agent = AutoDevAgent(pid, provider=StubProvider())
    asyncio.run(agent.run(resume=True))
    p = svc.get_project(pid)
    assert p["status"] == ProjectStatus.completed.value, p
    artifacts = {a["path"] for a in svc.get_artifacts(pid)}
    assert {"adder.py", "test_adder.py"} <= artifacts


def test_incremental_generation_writes_each_file():
    project = svc.create_project("Adder built incrementally")
    pid = project["id"]

    agent = AutoDevAgent(pid, provider=StubProvider())
    original = agent.settings.incremental_generation
    agent.settings.incremental_generation = "always"
    try:
        asyncio.run(agent.run())
    finally:
        agent.settings.incremental_generation = original

    p = svc.get_project(pid)
    assert p["status"] == ProjectStatus.completed.value, p

    events = svc.get_events(pid)
    msgs = [e["message"] for e in events]
    assert any("incrementally" in m for m in msgs), msgs
    assert any(m == "Generating adder.py" for m in msgs), msgs

    artifacts = {a["path"] for a in svc.get_artifacts(pid)}
    assert {"adder.py", "test_adder.py"} <= artifacts


def test_fix_loop_recovers_from_failure():
    project = svc.create_project("Adder that first fails then gets fixed")
    pid = project["id"]

    # broken_first makes the initial generation wrong, forcing a fix cycle.
    _run(pid, StubProvider(broken_first=True))

    p = svc.get_project(pid)
    assert p["status"] == ProjectStatus.completed.value, p

    events = svc.get_events(pid)
    phases = {e["phase"] for e in events}
    assert "fixing" in phases, "expected the fix phase to run"

    done = [e for e in events if e["type"] == "done"]
    assert done[-1]["data"]["tests_passed"] is True
