"""The autonomous build loop.

Given a project (goal), the agent drives the whole thing itself:

    plan  ->  generate files  ->  set up env  ->  run tests  ->  fix  ->  repeat

Every step streams progress as events (persisted + broadcast) so the UI can
show live output and, after a restart, replay exactly what happened.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from ..config import get_settings
from ..database import session_scope
from ..llm import LLMProvider, build_provider
from ..memory import get_memory
from ..models import Artifact, Message, Project, ProjectStatus
from ..sandbox import SandboxManager, run_command
from ..services.event_bus import bus
from ..services.events import emit
from . import prompts
from .parsing import extract_json

logger = logging.getLogger(__name__)

_PYTHONISH = {"python", "py", "python3"}


class AutoDevAgent:
    def __init__(
        self,
        project_id: str,
        stop_event: Optional[asyncio.Event] = None,
        provider: Optional[LLMProvider] = None,
        revision_feedback: Optional[str] = None,
    ):
        self.project_id = project_id
        self.settings = get_settings()
        self.stop_event = stop_event or asyncio.Event()
        self.provider = provider or build_provider(self.settings)
        self.memory = get_memory()
        self.sandbox: Optional[SandboxManager] = None
        self.files: dict[str, str] = {}
        self.goal = ""
        self.plan: dict = {}
        self.require_approval = False
        self.revision_feedback = revision_feedback

    # ------------------------------------------------------------------
    # persistence helpers
    # ------------------------------------------------------------------

    def _update_project(self, **fields) -> None:
        with session_scope() as session:
            project = session.get(Project, self.project_id)
            if project is None:
                return
            for key, value in fields.items():
                setattr(project, key, value)

    def _load_project(self) -> Project:
        with session_scope() as session:
            project = session.get(Project, self.project_id)
            if project is None:
                raise RuntimeError(f"Project {self.project_id} not found")
            session.expunge(project)
            return project

    def _index_artifact(self, rel_path: str, content: str, language: str) -> None:
        with session_scope() as session:
            existing = (
                session.query(Artifact)
                .filter_by(project_id=self.project_id, path=rel_path)
                .one_or_none()
            )
            if existing:
                existing.size = len(content.encode("utf-8"))
                existing.language = language
            else:
                session.add(
                    Artifact(
                        project_id=self.project_id,
                        path=rel_path,
                        language=language,
                        size=len(content.encode("utf-8")),
                    )
                )

    def _add_message(self, role: str, content: str) -> None:
        with session_scope() as session:
            session.add(
                Message(project_id=self.project_id, role=role, content=content)
            )

    # ------------------------------------------------------------------
    # streaming helper — ephemeral token stream (not persisted)
    # ------------------------------------------------------------------

    def _token_streamer(self, phase: str):
        async def on_token(text: str) -> None:
            await bus.publish(
                self.project_id,
                {"type": "token", "phase": phase, "data": {"text": text}},
            )

        return on_token

    def _check_stop(self) -> bool:
        if self.stop_event.is_set():
            return True
        # Also honor an out-of-band DB status change to "stopped".
        with session_scope() as session:
            project = session.get(Project, self.project_id)
            if project and project.status == ProjectStatus.stopped:
                self.stop_event.set()
                return True
        return False

    # ------------------------------------------------------------------
    # main entry
    # ------------------------------------------------------------------

    async def run(self, resume: bool = False) -> None:
        try:
            project = self._load_project()
            self.goal = project.goal
            self.require_approval = bool(getattr(project, "require_approval", False))

            if resume:
                # Plan was already produced and approved; rebuild context and
                # continue straight to code generation.
                self.plan = project.plan or {}
                self.sandbox = SandboxManager(self.project_id, project.name or "project")
                self.sandbox.create()
                await emit(self.project_id, "status",
                           "Plan approved — resuming build", phase="generating")
            else:
                await emit(self.project_id, "status", "Run started", phase="start")
                if self._check_stop():
                    return await self._finish_stopped()

                await self._phase_plan()
                if self._check_stop():
                    return await self._finish_stopped()

                if self.require_approval:
                    return await self._gate_for_approval()

            await self._phase_generate()
            if self._check_stop():
                return await self._finish_stopped()

            await self._phase_setup()
            if self._check_stop():
                return await self._finish_stopped()

            await self._phase_test_and_fix()

        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent run failed")
            self._update_project(status=ProjectStatus.failed, error=str(exc))
            await emit(
                self.project_id,
                "error",
                f"Run failed: {exc}",
                level="error",
                phase="error",
            )
            await emit(self.project_id, "done", "Run ended (failed)",
                       phase="done", data={"success": False})

    async def _finish_stopped(self) -> None:
        self._update_project(status=ProjectStatus.stopped, phase="stopped")
        await emit(self.project_id, "status", "Run stopped by user",
                   phase="stopped")
        await emit(self.project_id, "done", "Run ended (stopped)",
                   phase="done", data={"success": False, "stopped": True})

    async def _gate_for_approval(self) -> None:
        """Pause after planning until the user approves or revises the plan.

        The run task ends here (no 'done' event). The plan is persisted, so the
        gate survives an app restart — the user can approve later.
        """
        self._update_project(
            status=ProjectStatus.awaiting_approval, phase="awaiting_approval"
        )
        await emit(
            self.project_id,
            "approval",
            "Plan ready — review and approve to start building.",
            phase="awaiting_approval",
            data={"plan": self.plan},
        )

    # ------------------------------------------------------------------
    # phase: PLAN
    # ------------------------------------------------------------------

    async def _phase_plan(self) -> None:
        self._update_project(status=ProjectStatus.planning, phase="planning")
        await emit(self.project_id, "phase", "Planning the project", phase="planning")

        memory_hits = self.memory.query(self.goal) if self.memory.enabled else []
        messages = prompts.plan_messages(
            self.goal, memory_hits, revision_feedback=self.revision_feedback
        )
        raw = await self.provider.chat(
            messages,
            temperature=self.settings.temperature,
            on_token=self._token_streamer("planning"),
        )
        plan = extract_json(raw)
        self.plan = plan

        name = str(plan.get("project_name") or "").strip() or "project"
        language = str(plan.get("language") or "").strip().lower()
        description = str(plan.get("description") or "").strip()

        self._update_project(
            name=name, language=language, description=description, plan=plan
        )
        self._add_message("assistant", f"Plan: {description}")

        # Now that we know the name, create the sandbox directory.
        self.sandbox = SandboxManager(self.project_id, name)
        workspace = self.sandbox.create()
        self._update_project(workspace_path=str(workspace))

        await emit(
            self.project_id,
            "result",
            f"Plan ready: {description}",
            phase="planning",
            data={
                "plan": plan,
                "language": language,
                "workspace": str(workspace),
                "files": [f.get("path") for f in plan.get("files", [])],
            },
        )

    # ------------------------------------------------------------------
    # phase: GENERATE
    # ------------------------------------------------------------------

    def _use_incremental(self) -> bool:
        mode = (self.settings.incremental_generation or "auto").lower()
        planned = self.plan.get("files", []) or []
        if mode == "always":
            return True
        if mode == "never":
            return False
        return len(planned) > self.settings.incremental_file_threshold

    async def _write_generated(self, path: str, content: str, phase: str) -> None:
        assert self.sandbox is not None
        language = self.plan.get("language", "")
        self.sandbox.write_file(path, content)
        self.files[path] = content
        self._index_artifact(path, content, self._lang_for(path, language))
        await emit(
            self.project_id, "file", f"Wrote {path}", phase=phase,
            data={"path": path, "size": len(content)},
        )

    async def _phase_generate(self) -> None:
        assert self.sandbox is not None
        self._update_project(status=ProjectStatus.generating, phase="generating")

        if self._use_incremental():
            await self._generate_incremental()
        else:
            await self._generate_single_shot()

        if not self.files:
            raise RuntimeError("Generator produced no files")

        await emit(
            self.project_id,
            "result",
            f"Generated {len(self.files)} files",
            phase="generating",
            data={"files": list(self.files.keys())},
        )

    async def _generate_single_shot(self) -> None:
        await emit(self.project_id, "phase", "Generating source files",
                   phase="generating")
        messages = prompts.generate_messages(self.goal, self.plan)
        raw = await self.provider.chat(
            messages,
            temperature=self.settings.temperature,
            on_token=self._token_streamer("generating"),
        )
        data = extract_json(raw)
        for entry in data.get("files", []) or []:
            path = str(entry.get("path", "")).strip()
            content = entry.get("content", "")
            if not path or content is None:
                continue
            await self._write_generated(path, content, "generating")

    async def _generate_incremental(self) -> None:
        planned = [
            f for f in (self.plan.get("files", []) or [])
            if str(f.get("path", "")).strip()
        ]
        await emit(
            self.project_id, "phase",
            f"Generating {len(planned)} files incrementally",
            phase="generating",
        )
        for entry in planned:
            if self._check_stop():
                return
            path = str(entry.get("path", "")).strip()
            purpose = str(entry.get("purpose", ""))
            await emit(self.project_id, "log", f"Generating {path}",
                       phase="generating")
            messages = prompts.generate_one_file_messages(
                self.goal, self.plan, path, purpose, self.files
            )
            raw = await self.provider.chat(
                messages,
                temperature=self.settings.temperature,
                on_token=self._token_streamer("generating"),
            )
            content = self._extract_file_content(raw, path)
            if content is None:
                await emit(self.project_id, "log",
                           f"No content produced for {path}", level="warn",
                           phase="generating")
                continue
            await self._write_generated(path, content, "generating")

    @staticmethod
    def _extract_file_content(raw: str, path: str) -> Optional[str]:
        """Pull one file's content from an incremental response.

        Accepts either {"content": "..."} or {"files": [{"path","content"}]}.
        """
        data = extract_json(raw)
        if isinstance(data.get("content"), str):
            return data["content"]
        for entry in data.get("files", []) or []:
            if str(entry.get("path", "")).strip() == path:
                return entry.get("content")
        files = data.get("files", []) or []
        if files:  # fall back to the first file if paths don't line up
            return files[0].get("content")
        return None

    @staticmethod
    def _lang_for(path: str, default: str) -> str:
        ext = Path(path).suffix.lower()
        mapping = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby",
            ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".php": "php",
            ".html": "html", ".css": "css", ".json": "json", ".md": "markdown",
            ".sh": "bash", ".yml": "yaml", ".yaml": "yaml", ".toml": "toml",
        }
        return mapping.get(ext, default or "")

    # ------------------------------------------------------------------
    # phase: SETUP
    # ------------------------------------------------------------------

    def _is_python(self) -> bool:
        lang = (self.plan.get("language") or "").lower()
        return any(p in lang for p in _PYTHONISH)

    async def _run_shell(self, command: str, phase: str):
        assert self.sandbox is not None
        env = self.sandbox.venv_env() if self._is_python() else None
        await emit(self.project_id, "command", f"$ {command}", phase=phase,
                   data={"command": command})

        async def on_line(line: str) -> None:
            await bus.publish(
                self.project_id,
                {"type": "output", "phase": phase, "data": {"line": line}},
            )

        result = await run_command(
            command,
            cwd=self.sandbox.root,
            timeout=self.settings.command_timeout,
            env=env,
            on_line=on_line,
        )
        await emit(
            self.project_id,
            "result",
            f"exit={result.returncode} ({result.duration}s)"
            + (" [timeout]" if result.timed_out else ""),
            phase=phase,
            level="info" if result.ok else "warn",
            data={
                "command": command,
                "returncode": result.returncode,
                "timed_out": result.timed_out,
                "tail": result.stdout[-4000:],
            },
        )
        return result

    async def _phase_setup(self) -> None:
        assert self.sandbox is not None
        self._update_project(status=ProjectStatus.setup, phase="setup")
        await emit(self.project_id, "phase", "Setting up environment",
                   phase="setup")

        if self._is_python() and self.settings.auto_venv:
            await emit(self.project_id, "log", "Creating Python virtualenv",
                       phase="setup")
            venv_res = await self.sandbox.ensure_python_venv()
            if not venv_res.ok and venv_res.command != "venv (cached)":
                await emit(self.project_id, "log",
                           "venv creation reported an issue; continuing",
                           level="warn", phase="setup")
            # Ensure pip is fresh, and install requirements if present.
            if (self.sandbox.root / "requirements.txt").exists():
                await self._run_shell(
                    "python -m pip install -q -r requirements.txt", "setup"
                )

        for cmd in self.plan.get("setup_commands", []) or []:
            cmd = str(cmd).strip()
            if not cmd:
                continue
            if self._check_stop():
                return
            await self._run_shell(cmd, "setup")

    # ------------------------------------------------------------------
    # phase: TEST + FIX
    # ------------------------------------------------------------------

    async def _phase_test_and_fix(self) -> None:
        test_command = str(self.plan.get("test_command") or "").strip()
        if not test_command:
            await emit(self.project_id, "log",
                       "No test command in plan; skipping tests",
                       level="warn", phase="testing")
            return await self._finish_success(tests_passed=None)

        max_iters = self.settings.max_fix_iterations
        for attempt in range(max_iters + 1):
            if self._check_stop():
                return await self._finish_stopped()

            self._update_project(status=ProjectStatus.testing, phase="testing")
            await emit(
                self.project_id, "phase",
                f"Running tests (attempt {attempt + 1}/{max_iters + 1})",
                phase="testing",
            )
            result = await self._run_shell(test_command, "testing")

            if result.ok:
                return await self._finish_success(tests_passed=True)

            # Missing runtime/tool: fixing code won't help.
            if result.returncode == 127 or "command not found" in result.stdout.lower():
                await emit(
                    self.project_id, "log",
                    "Test runtime not available on this machine; "
                    "delivering project without running tests.",
                    level="warn", phase="testing",
                )
                return await self._finish_success(tests_passed=None,
                                                  note="test runtime unavailable")

            if attempt >= max_iters:
                break

            # FIX phase
            if self._check_stop():
                return await self._finish_stopped()
            self._update_project(status=ProjectStatus.fixing, phase="fixing")
            await emit(self.project_id, "phase",
                       "Tests failed — attempting a fix", phase="fixing")
            await self._apply_fix(test_command, result.stdout)

        # Exhausted attempts.
        self._update_project(
            status=ProjectStatus.completed,
            phase="done",
            error="Tests still failing after max fix attempts",
        )
        await emit(self.project_id, "result",
                   "Tests still failing after max attempts; project delivered "
                   "as-is for review.", level="warn", phase="done")
        await emit(self.project_id, "done", "Run ended (tests failing)",
                   phase="done", data={"success": False, "tests_passed": False})

    async def _apply_fix(self, test_command: str, failing_output: str) -> None:
        assert self.sandbox is not None
        messages = prompts.fix_messages(
            self.goal, self.plan, self.files, failing_output
        )
        raw = await self.provider.chat(
            messages,
            temperature=self.settings.temperature,
            on_token=self._token_streamer("fixing"),
        )
        data = extract_json(raw)
        explanation = str(data.get("explanation", "")).strip()
        if explanation:
            await emit(self.project_id, "log", f"Fix: {explanation}",
                       phase="fixing")

        changed = 0
        language = self.plan.get("language", "")
        for entry in data.get("files", []) or []:
            path = str(entry.get("path", "")).strip()
            content = entry.get("content")
            if not path or content is None:
                continue
            self.sandbox.write_file(path, content)
            self.files[path] = content
            self._index_artifact(path, content, self._lang_for(path, language))
            changed += 1
            await emit(self.project_id, "file", f"Updated {path}",
                       phase="fixing", data={"path": path})

        if changed == 0:
            await emit(self.project_id, "log",
                       "Fixer produced no file changes", level="warn",
                       phase="fixing")

    # ------------------------------------------------------------------
    # completion
    # ------------------------------------------------------------------

    async def _finish_success(self, tests_passed, note: str = "") -> None:
        self._update_project(status=ProjectStatus.completed, phase="done",
                             error="")
        summary = self._build_summary(tests_passed, note)
        self._add_message("assistant", summary)

        if self.memory.enabled:
            self.memory.add(
                self.project_id, "summary",
                f"Goal: {self.goal}\n{summary}",
                metadata={"language": self.plan.get("language", "")},
            )

        await emit(self.project_id, "result", summary, phase="done")
        await emit(
            self.project_id, "done", "Run completed",
            phase="done",
            data={
                "success": True,
                "tests_passed": tests_passed,
                "note": note,
                "files": list(self.files.keys()),
                "run_command": self.plan.get("run_command", ""),
            },
        )

    def _build_summary(self, tests_passed, note: str) -> str:
        lines = [
            f"Built '{self.plan.get('project_name', 'project')}' "
            f"({self.plan.get('language', 'n/a')}).",
            self.plan.get("description", ""),
            f"{len(self.files)} files generated.",
        ]
        if tests_passed is True:
            lines.append("All automated tests passed.")
        elif tests_passed is None:
            lines.append(f"Tests not run ({note})." if note else "Tests skipped.")
        run_cmd = self.plan.get("run_command")
        if run_cmd:
            lines.append(f"Run it with: {run_cmd}")
        return "\n".join(x for x in lines if x)
