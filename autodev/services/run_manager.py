"""Owns background agent runs.

A run is an asyncio task launched by the FastAPI server process. Because the
server is the always-on engine (the browser UI is just a view), a run keeps
going after the user closes the UI — and its progress is fully persisted, so
reopening the UI replays everything and shows the live tail.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from ..database import session_scope
from ..models import Project, ProjectStatus

logger = logging.getLogger(__name__)

_ACTIVE = {
    ProjectStatus.planning,
    ProjectStatus.generating,
    ProjectStatus.setup,
    ProjectStatus.testing,
    ProjectStatus.fixing,
}


@dataclass
class RunHandle:
    task: asyncio.Task
    stop_event: asyncio.Event


class RunManager:
    def __init__(self) -> None:
        self._runs: dict[str, RunHandle] = {}

    def is_running(self, project_id: str) -> bool:
        handle = self._runs.get(project_id)
        return handle is not None and not handle.task.done()

    def start(
        self,
        project_id: str,
        resume: bool = False,
        revision_feedback: str | None = None,
        chat_feedback: str | None = None,
    ) -> bool:
        """Launch a background run. Returns False if one is already active."""
        if self.is_running(project_id):
            return False

        # Imported lazily to avoid a circular import at module load time
        # (agent -> services -> run_manager -> agent).
        from ..agent import AutoDevAgent

        stop_event = asyncio.Event()
        agent = AutoDevAgent(
            project_id,
            stop_event=stop_event,
            revision_feedback=revision_feedback,
            chat_feedback=chat_feedback,
        )
        task = asyncio.create_task(agent.run(resume=resume), name=f"run-{project_id}")
        self._runs[project_id] = RunHandle(task=task, stop_event=stop_event)

        def _cleanup(_: asyncio.Task) -> None:
            self._runs.pop(project_id, None)

        task.add_done_callback(_cleanup)
        return True

    def approve(self, project_id: str) -> bool:
        """Approve a plan that's waiting, and resume the build."""
        if self.is_running(project_id):
            return False
        with session_scope() as session:
            project = session.get(Project, project_id)
            if not project or project.status != ProjectStatus.awaiting_approval:
                return False
        return self.start(project_id, resume=True)

    def revise(self, project_id: str, feedback: str) -> bool:
        """Reject the current plan and re-plan with the user's feedback."""
        if self.is_running(project_id):
            return False
        with session_scope() as session:
            project = session.get(Project, project_id)
            if not project or project.status != ProjectStatus.awaiting_approval:
                return False
        return self.start(project_id, resume=False, revision_feedback=feedback)

    def chat(self, project_id: str, feedback: str) -> bool:
        """Iterate on an existing project from a user's chat feedback."""
        if self.is_running(project_id):
            return False
        with session_scope() as session:
            project = session.get(Project, project_id)
            if not project:
                return False
            # Chatting only makes sense once there's something built to iterate on.
            if project.status == ProjectStatus.awaiting_approval:
                return False
        return self.start(project_id, chat_feedback=feedback)

    async def stop(self, project_id: str) -> bool:
        handle = self._runs.get(project_id)
        if handle is None:
            # Not actively running; just mark it stopped if mid-flight.
            with session_scope() as session:
                project = session.get(Project, project_id)
                if project and project.status in _ACTIVE:
                    project.status = ProjectStatus.stopped
                    project.phase = "stopped"
                    return True
            return False
        handle.stop_event.set()
        return True

    def recover_orphans(self) -> int:
        """Mark runs interrupted by a previous process exit as 'stopped'.

        We can't resume a run mid-LLM-call, but the persisted history is intact
        and the user can re-run. This keeps the UI honest after a crash/restart.
        """
        count = 0
        with session_scope() as session:
            orphans = (
                session.query(Project)
                .filter(Project.status.in_(list(_ACTIVE)))
                .all()
            )
            for project in orphans:
                project.status = ProjectStatus.stopped
                project.phase = "interrupted"
                project.error = "Interrupted by app restart. Re-run to continue."
                count += 1
        if count:
            logger.info("Recovered %d interrupted run(s) as stopped", count)
        return count


# App-wide singleton.
run_manager = RunManager()
