"""Slash-command helpers and their presentation logic."""

from __future__ import annotations

from ..storage import Database, LongTermMemory

HELP = """\
Commands:
  /help          show this help
  /tools         list the tools I can use (search, converters, etc.)
  /memories      list everything I remember long-term about you
  /history       show recent messages from your chat archive
  /new           start a fresh conversation (clears short-term context)
  /whoami        show your current user id and thread
  /switch        switch to a different user
  /exit, /quit   leave
Anything else is sent to the assistant.
"""


def prompt_user_id(db: Database) -> str:
    known = list(db.known_users())
    if known:
        print("Returning users:", ", ".join(known))
    while True:
        uid = input("Who are you? (username): ").strip()
        if uid:
            return uid
        print("Please enter a username.")


def print_tools(tools) -> None:
    print("Tools available to the assistant:")
    for t in tools:
        # first line of the description keeps the list tidy
        summary = (t.description or "").strip().splitlines()[0]
        print(f"  - {t.name}: {summary}")


def print_memories(memory: LongTermMemory, user_id: str) -> None:
    items = memory.list_all(user_id)
    if not items:
        print("(I have no long-term memories about you yet.)")
        return
    print(f"Long-term memories for {user_id}:")
    for i, m in enumerate(items, 1):
        print(f"  {i}. {m}")


def print_history(db: Database, user_id: str) -> None:
    rows = db.recent_messages(user_id, limit=20)
    if not rows:
        print("(no messages yet)")
        return
    for r in rows:
        who = "you" if r["role"] == "user" else "bot"
        print(f"  [{who}] {r['content']}")
