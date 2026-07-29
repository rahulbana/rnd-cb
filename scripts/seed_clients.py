"""Seed the client directory SQLite DB with a few sample records.

Usage:
    python scripts/seed_clients.py
"""

from __future__ import annotations

from agentic_app.config import get_settings
from mcp_server.db import ClientStore

SAMPLE_CLIENTS = [
    dict(name="Acme Corp", country="USA", state="California", city="San Francisco",
         contact_number="+1-415-555-0100", email="hello@acme.example"),
    dict(name="Globex Ltd", country="UK", state="England", city="London",
         contact_number="+44-20-7946-0000", email="contact@globex.example"),
    dict(name="Tata Solutions", country="India", state="Maharashtra", city="Mumbai",
         contact_number="+91-22-5555-1234", email="info@tatasol.example"),
    dict(name="Nordwind GmbH", country="Germany", state="Bavaria", city="Munich",
         contact_number="+49-89-5555-9876", email="kontakt@nordwind.example"),
]


def main() -> None:
    settings = get_settings()
    store = ClientStore(settings.mcp_db_path)
    created = 0
    for c in SAMPLE_CLIENTS:
        existing = store.search_clients(c["name"])
        if any(e["name"].lower() == c["name"].lower() for e in existing):
            continue
        store.add_client(**c)
        created += 1
    print(f"Seed complete. Added {created} new client(s). Total: {store.count()}")


if __name__ == "__main__":
    main()
