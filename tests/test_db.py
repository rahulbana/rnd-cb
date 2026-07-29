"""Unit tests for the SQLite ClientStore (no external services required)."""

from __future__ import annotations

import pytest

from mcp_server.db import ClientStore


@pytest.fixture
def store(tmp_path):
    return ClientStore(str(tmp_path / "test_clients.db"))


def test_add_and_get(store):
    created = store.add_client(
        name="Acme Corp",
        country="USA",
        state="California",
        city="San Francisco",
        contact_number="+1-415-555-0100",
        email="hello@acme.example",
    )
    assert created["id"] > 0
    assert created["name"] == "Acme Corp"
    assert created["created_at"] == created["updated_at"]

    fetched = store.get_client(created["id"])
    assert fetched == created


def test_add_requires_name(store):
    with pytest.raises(ValueError):
        store.add_client(name="   ")


def test_invalid_email_rejected(store):
    with pytest.raises(ValueError):
        store.add_client(name="Bad Email", email="not-an-email")


def test_list_and_filter(store):
    store.add_client(name="A", country="India", city="Mumbai")
    store.add_client(name="B", country="India", city="Delhi")
    store.add_client(name="C", country="USA", city="Austin")

    all_rows = store.list_clients()
    assert all_rows[0]["name"] == "C"  # newest first

    india = store.list_clients(country="india")  # case-insensitive
    assert {r["name"] for r in india} == {"A", "B"}

    mumbai = store.list_clients(city="Mumbai")
    assert len(mumbai) == 1 and mumbai[0]["name"] == "A"


def test_search(store):
    store.add_client(name="Globex Ltd", country="UK", city="London")
    store.add_client(name="Acme", country="USA", city="London")  # shared city

    by_name = store.search_clients("glob")
    assert len(by_name) == 1 and by_name[0]["name"] == "Globex Ltd"

    by_city = store.search_clients("london")
    assert len(by_city) == 2

    assert store.search_clients("") == []


def test_update(store):
    c = store.add_client(name="Old Name", city="OldCity")
    updated = store.update_client(c["id"], name="New Name", city="NewCity")
    assert updated["name"] == "New Name"
    assert updated["city"] == "NewCity"
    assert updated["updated_at"] >= c["updated_at"]

    # Omitted / None fields are unchanged.
    again = store.update_client(c["id"], country="Canada")
    assert again["name"] == "New Name"
    assert again["country"] == "Canada"


def test_update_missing_returns_none(store):
    assert store.update_client(9999, name="x") is None


def test_delete(store):
    c = store.add_client(name="Temp")
    assert store.delete_client(c["id"]) is True
    assert store.get_client(c["id"]) is None
    assert store.delete_client(c["id"]) is False


def test_count(store):
    assert store.count() == 0
    store.add_client(name="X")
    store.add_client(name="Y")
    assert store.count() == 2
