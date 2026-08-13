"""CRUD + read helpers for projects, events, artifacts and files."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from ..database import session_scope
from ..models import Artifact, Event, Message, Project, ProjectStatus
from ..sandbox import SandboxManager


def create_project(
    goal: str,
    name: Optional[str] = None,
    require_approval: bool = False,
) -> dict[str, Any]:
    with session_scope() as session:
        project = Project(
            goal=goal.strip(),
            name=(name or "New project").strip(),
            status=ProjectStatus.pending,
            require_approval=require_approval,
        )
        session.add(project)
        session.flush()
        session.add(Message(project_id=project.id, role="user", content=goal.strip()))
        return project.to_dict()


def list_projects() -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = (
            session.query(Project).order_by(Project.created_at.desc()).all()
        )
        return [p.to_dict() for p in rows]


def get_project(project_id: str) -> Optional[dict[str, Any]]:
    with session_scope() as session:
        project = session.get(Project, project_id)
        return project.to_dict() if project else None


def get_events(project_id: str, after_seq: int = 0, limit: int = 2000) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(Event)
            .filter(Event.project_id == project_id, Event.seq > after_seq)
            .order_by(Event.seq.asc())
            .limit(limit)
            .all()
        )
        return [e.to_dict() for e in rows]


def get_artifacts(project_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(Artifact)
            .filter(Artifact.project_id == project_id)
            .order_by(Artifact.path.asc())
            .all()
        )
        return [a.to_dict() for a in rows]


def get_messages(project_id: str) -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(Message)
            .filter(Message.project_id == project_id)
            .order_by(Message.id.asc())
            .all()
        )
        return [m.to_dict() for m in rows]


def get_file_content(project_id: str, rel_path: str) -> Optional[str]:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project or not project.name:
            return None
        name = project.name
    sandbox = SandboxManager(project_id, name)
    try:
        return sandbox.read_file(rel_path)
    except (FileNotFoundError, ValueError):
        return None


def delete_project(project_id: str) -> bool:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project:
            return False
        workspace = project.workspace_path
        session.delete(project)
    if workspace:
        p = Path(workspace)
        if p.exists() and p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    return True
