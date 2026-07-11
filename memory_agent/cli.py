"""Interactive command-line chat loop.

Run with::

    python -m memory_agent

Each user gets a persistent conversation thread (short-term memory) plus a
private long-term memory store. Type ``/help`` inside the chat for commands.
"""

from __future__ import annotations

import time

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from .agent import build_agent
from .config import settings
from .db import Database

HELP = """\
Commands:
  /help          show this help
  /memories      list everything I remember long-term about you
  /history       show recent messages from your chat archive
  /new           start a fresh conversation (clears short-term context)
  /whoami        show your current user id and thread
  /switch        switch to a different user
  /exit, /quit   leave
Anything else is sent to the assistant.
"""


class Session:
    """Tracks the active user and their current conversation thread."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.thread_id = f"{user_id}::main"

    def new_thread(self) -> None:
        self.thread_id = f"{self.user_id}::{int(time.time())}"

    @property
    def config(self) -> dict:
        return {"configurable": {"thread_id": self.thread_id, "user_id": self.user_id}}


def _prompt_user_id(db: Database) -> str:
    known = list(db.known_users())
    if known:
        print("Returning users:", ", ".join(known))
    while True:
        uid = input("Who are you? (username): ").strip()
        if uid:
            return uid
        print("Please enter a username.")


def _print_memories(memory, user_id: str) -> None:
    items = memory.list_all(user_id)
    if not items:
        print("(I have no long-term memories about you yet.)")
        return
    print(f"Long-term memories for {user_id}:")
    for i, m in enumerate(items, 1):
        print(f"  {i}. {m}")


def _print_history(db: Database, user_id: str) -> None:
    rows = db.recent_messages(user_id, limit=20)
    if not rows:
        print("(no messages yet)")
        return
    for r in rows:
        who = "you" if r["role"] == "user" else "bot"
        print(f"  [{who}] {r['content']}")


def _respond(app, db: Database, session: Session, text: str) -> None:
    db.log_message(session.user_id, session.thread_id, "user", text)
    result = app.invoke(
        {"messages": [HumanMessage(text)]},
        config=session.config,
    )
    reply = result["messages"][-1].content
    db.log_message(session.user_id, session.thread_id, "assistant", reply)
    print(f"\nbot> {reply}\n")


def run() -> None:
    settings.require_api_key()
    db = Database(settings.db_path)

    # The checkpointer stores short-term conversation state per thread in the
    # same SQLite file, surviving restarts.
    with SqliteSaver.from_conn_string(settings.db_path) as checkpointer:
        app, memory = build_agent(db, settings, checkpointer)

        print("=" * 60)
        print("  Memory Chatbot  —  short-term + long-term memory")
        print("  model:", settings.chat_model)
        print("=" * 60)
        session = Session(_prompt_user_id(db))
        print(f"\nHi {session.user_id}! Type /help for commands.\n")

        while True:
            try:
                text = input(f"{session.user_id}> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not text:
                continue

            cmd = text.lower()
            if cmd in ("/exit", "/quit"):
                print("Bye!")
                break
            if cmd == "/help":
                print(HELP)
                continue
            if cmd == "/memories":
                _print_memories(memory, session.user_id)
                continue
            if cmd == "/history":
                _print_history(db, session.user_id)
                continue
            if cmd == "/new":
                session.new_thread()
                print("Started a fresh conversation (long-term memory kept).")
                continue
            if cmd == "/whoami":
                print(f"user_id={session.user_id} thread_id={session.thread_id}")
                continue
            if cmd == "/switch":
                session = Session(_prompt_user_id(db))
                print(f"Switched to {session.user_id}.")
                continue

            try:
                _respond(app, db, session, text)
            except Exception as exc:  # keep the loop alive on transient errors
                print(f"\n[error] {exc}\n")

    db.close()


if __name__ == "__main__":
    run()
