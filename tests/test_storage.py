"""Tests for the SQLite chat archive and long-term memory store."""

from __future__ import annotations

from memory_agent.storage import Database, LongTermMemory


# --- chat archive ---------------------------------------------------------

def test_log_and_recent_messages(db):
    db.log_message("alice", "t1", "user", "hello")
    db.log_message("alice", "t1", "assistant", "hi there")
    rows = db.recent_messages("alice")
    assert [(r["role"], r["content"]) for r in rows] == [
        ("user", "hello"),
        ("assistant", "hi there"),
    ]


def test_recent_messages_are_chronological_and_limited(db):
    for i in range(30):
        db.log_message("alice", "t1", "user", f"msg{i}")
    rows = db.recent_messages("alice", limit=5)
    assert [r["content"] for r in rows] == ["msg25", "msg26", "msg27", "msg28", "msg29"]


def test_known_users_spans_messages_and_memory(db):
    db.log_message("alice", "t1", "user", "hi")
    db.insert_memory("bob", "likes hiking", None)
    assert sorted(db.known_users()) == ["alice", "bob"]


# --- long-term memory -----------------------------------------------------

def test_add_and_list(memory):
    memory.add("alice", "User is allergic to peanuts")
    memory.add("alice", "User is learning Spanish")
    assert memory.list_all("alice") == [
        "User is allergic to peanuts",
        "User is learning Spanish",
    ]


def test_blank_facts_are_ignored(memory):
    memory.add("alice", "   ")
    assert memory.list_all("alice") == []


def test_semantic_recall_ranks_relevant_first(db, fake_embeddings):
    mem = LongTermMemory(db, fake_embeddings, top_k=2, min_score=-1.0)
    mem.add("alice", "User is allergic to peanuts")
    mem.add("alice", "User is learning Spanish")
    mem.add("alice", "User owns a dog")
    hits = mem.search("alice", "what snack given my peanut allergy?")
    assert hits[0] == "User is allergic to peanuts"
    assert len(hits) == 2


def test_min_score_filters_weak_matches(db, fake_embeddings):
    mem = LongTermMemory(db, fake_embeddings, top_k=5, min_score=0.99)
    mem.add("alice", "User is allergic to peanuts")
    # An unrelated query should not clear a very high threshold.
    assert mem.search("alice", "completely unrelated topic zzz") == []


def test_recall_is_user_scoped(memory):
    memory.add("alice", "alice secret")
    memory.add("bob", "bob secret")
    assert memory.list_all("alice") == ["alice secret"]
    assert memory.search("bob", "secret") == ["bob secret"]


def test_empty_user_skips_embedding(db):
    class BoomEmbeddings:
        def embed_query(self, text):
            raise AssertionError("should not embed for a user with no memories")

    mem = LongTermMemory(db, BoomEmbeddings())
    assert mem.search("nobody", "anything") == []


def test_falls_back_to_recent_when_no_vectors(db, fake_embeddings):
    # Insert rows with NULL embeddings directly (simulating an offline add).
    db.insert_memory("alice", "old fact", None)
    db.insert_memory("alice", "new fact", None)
    mem = LongTermMemory(db, fake_embeddings, top_k=1)
    assert mem.search("alice", "q") == ["new fact"]
