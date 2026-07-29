"""Remote MCP server exposing a SQLite-backed client directory.

Runs over the streamable-HTTP transport so it behaves as a real *remote* MCP
server the agent connects to at ``http://<host>:<port>/mcp``.

Run standalone:
    python -m mcp_server.server
    # or, after `pip install -e .`
    mcp-server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from agentic_app.config import get_settings
from mcp_server.db import ClientStore

settings = get_settings()

mcp = FastMCP(
    name="client-directory",
    instructions=(
        "A CRM-style client directory. Use these tools to create, look up, "
        "update, list, and delete client contact records (name, country, state, "
        "city, contact number, email). Prefer `search_clients` for fuzzy lookups "
        "and `list_clients` with filters for browsing."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
)

store = ClientStore(settings.mcp_db_path)


@mcp.tool()
def add_client(
    name: str,
    country: str,
    state: str,
    email: str,
    city: str | None = None,
    contact_number: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create a new client record and return it (including the assigned id).

    Required fields — the record cannot be created without all four:
        name: Full client / company name.
        country: Country of the client.
        state: State or province.
        email: Email address (validated).

    Optional fields:
        city: City.
        contact_number: Phone number in any format.
        notes: Free-form notes.

    If any required field is missing, ask the user for it before calling this tool.
    Returns an ``{"error": ...}`` dict if validation fails.
    """
    try:
        return store.add_client(
            name=name,
            country=country,
            state=state,
            email=email,
            city=city,
            contact_number=contact_number,
            notes=notes,
        )
    except ValueError as exc:
        return {"error": "validation_error", "detail": str(exc)}


@mcp.tool()
def get_client(client_id: int) -> dict[str, Any]:
    """Fetch a single client by id. Returns an error dict if not found."""
    client = store.get_client(client_id)
    if client is None:
        return {"error": "not_found", "client_id": client_id}
    return client


@mcp.tool()
def list_clients(
    country: str | None = None,
    state: str | None = None,
    city: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List clients, optionally filtered by country / state / city.

    Filters are case-insensitive exact matches. Returns up to `limit` rows
    (max 500), newest first.
    """
    rows = store.list_clients(country=country, state=state, city=city, limit=limit, offset=offset)
    return {"count": len(rows), "clients": rows}


@mcp.tool()
def search_clients(query: str, limit: int = 50) -> dict[str, Any]:
    """Fuzzy search clients by substring across name, location, phone, and email."""
    rows = store.search_clients(query=query, limit=limit)
    return {"count": len(rows), "query": query, "clients": rows}


@mcp.tool()
def update_client(
    client_id: int,
    name: str | None = None,
    country: str | None = None,
    state: str | None = None,
    city: str | None = None,
    contact_number: str | None = None,
    email: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Update the provided fields of an existing client. Omitted fields are unchanged."""
    updated = store.update_client(
        client_id,
        name=name,
        country=country,
        state=state,
        city=city,
        contact_number=contact_number,
        email=email,
        notes=notes,
    )
    if updated is None:
        return {"error": "not_found", "client_id": client_id}
    return updated


@mcp.tool()
def delete_client(client_id: int) -> dict[str, Any]:
    """Delete a client by id. Returns whether a row was removed."""
    deleted = store.delete_client(client_id)
    return {"deleted": deleted, "client_id": client_id}


@mcp.tool()
def count_clients() -> dict[str, int]:
    """Return the total number of client records in the directory."""
    return {"count": store.count()}


def main() -> None:
    """Entrypoint: serve over streamable-HTTP."""
    print(
        f"Starting client-directory MCP server on "
        f"http://{settings.mcp_host}:{settings.mcp_port}/mcp "
        f"(db: {settings.mcp_db_path})"
    )
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
