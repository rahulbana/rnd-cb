"""Per-user CLI session state."""

from __future__ import annotations

import time


class Session:
    """Tracks the active user and their current conversation thread."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.thread_id = f"{user_id}::main"

    def new_thread(self) -> None:
        """Start a fresh conversation (new short-term context) for this user."""
        self.thread_id = f"{self.user_id}::{int(time.time())}"

    @property
    def config(self) -> dict:
        """LangGraph config: thread scopes short-term memory, user scopes long-term."""
        return {"configurable": {"thread_id": self.thread_id, "user_id": self.user_id}}
