"""Unit tests for the SQLite ClientStore (no external services required)."""

from __future__ import annotations

import pytest

from mcp_server.db import ClientStore

# Valid values for the four mandatory fields, reused across tests.
REQUIRED = dict(name="Client", country="USA", state="California", email="c@example.com")


def _make(store: ClientStore, **overrides):
    """Create a client with all required fields present, overriding as needed."""
    return store.add_client(**{**REQUIRED, **overrides})


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


@pytest.mark.parametrize("field", ["name", "country", "state", "email"])
def test_required_fields_enforced(store, field):
    # Missing entirely (empty string) must raise, naming the offending field.
    with pytest.raises(ValueError, match=field):
        _make(store, **{field: ""})


def test_required_fields_whitespace_only(store):
    with pytest.raises(ValueError, match="country"):
        _make(store, country="   ")


def test_invalid_email_rejected(store):
    with pytest.raises(ValueError):
        _make(store, email="not-an-email")


def test_optional_fields_not_required(store):
    # city and contact_number may be omitted.
    c = _make(store, name="No Phone")
    assert c["city"] is None
    assert c["contact_number"] is None


def test_list_and_filter(store):
    _make(store, name="A", country="India", state="Maharashtra", city="Mumbai")
    _make(store, name="B", country="India", state="Delhi", city="Delhi")
    _make(store, name="C", country="USA", state="Texas", city="Austin")

    all_rows = store.list_clients()
    assert all_rows[0]["name"] == "C"  # newest first

    india = store.list_clients(country="india")  # case-insensitive
    assert {r["name"] for r in india} == {"A", "B"}

    mumbai = store.list_clients(city="Mumbai")
    assert len(mumbai) == 1 and mumbai[0]["name"] == "A"


def test_search(store):
    _make(store, name="Globex Ltd", country="UK", state="England", city="London")
    _make(store, name="Acme", country="USA", state="New York", city="London")

    by_name = store.search_clients("glob")
    assert len(by_name) == 1 and by_name[0]["name"] == "Globex Ltd"

    by_city = store.search_clients("london")
    assert len(by_city) == 2

    assert store.search_clients("") == []


def test_update(store):
    c = _make(store, name="Old Name", city="OldCity")
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
    c = _make(store, name="Temp")
    assert store.delete_client(c["id"]) is True
    assert store.get_client(c["id"]) is None
    assert store.delete_client(c["id"]) is False


def test_count(store):
    assert store.count() == 0
    _make(store, name="X")
    _make(store, name="Y")
    assert store.count() == 2
