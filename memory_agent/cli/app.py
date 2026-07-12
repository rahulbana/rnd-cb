"""Interactive command-line chat loop.

Run with ``python -m memory_agent``. Each user gets a persistent conversation
thread (short-term memory) plus a private long-term memory store.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from ..agent import build_agent
from ..config import settings
from ..observability import build_langfuse_handler, flush, instrument
from ..storage import Database
from . import commands
from .session import Session


def _respond(app, db: Database, session: Session, text: str, handler=None) -> None:
    db.log_message(session.user_id, session.thread_id, "user", text)
    config = instrument(
        session.config, handler,
        user_id=session.user_id, session_id=session.thread_id,
    )
    result = app.invoke({"messages": [HumanMessage(text)]}, config=config)
    reply = result["messages"][-1].content
    db.log_message(session.user_id, session.thread_id, "assistant", reply)
    print(f"\nbot> {reply}\n")


def run() -> None:
    settings.require_api_key()
    db = Database(settings.db_path)

    # The checkpointer stores short-term conversation state per thread in the
    # same SQLite file, surviving restarts.
    with SqliteSaver.from_conn_string(settings.db_path) as checkpointer:
        app, memory, tools = build_agent(db, settings, checkpointer)
        langfuse = build_langfuse_handler(settings)

        print("=" * 60)
        print("  Memory Chatbot  —  short-term + long-term memory")
        print("  model:", settings.chat_model)
        if langfuse is not None:
            print("  observability: Langfuse tracing enabled")
        print("=" * 60)
        session = Session(commands.prompt_user_id(db))
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
                print(commands.HELP)
                continue
            if cmd == "/tools":
                commands.print_tools(tools)
                continue
            if cmd == "/memories":
                commands.print_memories(memory, session.user_id)
                continue
            if cmd == "/history":
                commands.print_history(db, session.user_id)
                continue
            if cmd == "/new":
                session.new_thread()
                print("Started a fresh conversation (long-term memory kept).")
                continue
            if cmd == "/whoami":
                print(f"user_id={session.user_id} thread_id={session.thread_id}")
                continue
            if cmd == "/switch":
                session = Session(commands.prompt_user_id(db))
                print(f"Switched to {session.user_id}.")
                continue

            try:
                _respond(app, db, session, text, handler=langfuse)
            except Exception as exc:  # keep the loop alive on transient errors
                print(f"\n[error] {exc}\n")

        flush()  # send any buffered Langfuse events before exit

    db.close()
