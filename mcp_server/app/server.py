"""Remote MCP server exposing The Movie Database (TMDB) tools.

Run with::

    python -m app.server

The server speaks the MCP *streamable-HTTP* transport, so any MCP-capable
client (including the LangGraph backend in this repo) can connect over the
network at ``http://<host>:<port>/mcp``.

Scope: this server provides *movie* tools only. The application's other
capabilities (translation, world-time) are native tools that live in the
backend, not here.

Every tool has a rich docstring: the docstring *is* the tool description the
LLM sees, so it is written to guide correct tool selection and argument use.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

from .settings import get_settings
from .tmdb import TMDBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | mcp | %(message)s",
)
logger = logging.getLogger("mcp.server")

settings = get_settings()

# DNS-rebinding protection guards browser-originated requests. This server is an
# internal tool endpoint reached by the trusted backend, whose Host header varies
# by deployment, so the check is disabled by default (see settings).
_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=not settings.disable_host_check,
    allowed_hosts=settings.allowed_hosts,
    allowed_origins=settings.allowed_hosts,
)

mcp = FastMCP(
    name="tmdb-movies",
    instructions=(
        "Tools for The Movie Database (TMDB). Use these to look up films, TV, "
        "people (actors/directors), ratings, and what's trending. Prefer these "
        "tools over guessing whenever a user asks about movies or the people who "
        "make them."
    ),
    host=settings.host,
    port=settings.port,
    transport_security=_transport_security,
)


# ---------------------------------------------------------------------------
# TMDB tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def search_movies(
    query: Annotated[str, Field(description="Free-text movie title or keywords.")],
    page: Annotated[int, Field(description="Result page (1-based).", ge=1)] = 1,
) -> dict[str, Any]:
    """Search TMDB for movies matching a title or keywords.

    Returns up to 10 shaped results with id, title, release date, rating and
    poster URL. Use the returned ``id`` with ``get_movie_details`` for a full
    breakdown (cast, director, runtime, trailers).
    """
    async with TMDBClient(settings) as client:
        return await client.search_movies(query, page=page)


@mcp.tool()
async def get_movie_details(
    movie_id: Annotated[int, Field(description="TMDB numeric movie id.")],
) -> dict[str, Any]:
    """Fetch full details for a movie by its TMDB id.

    Includes overview, genres, runtime, rating, budget/revenue, the director,
    the top billed cast, and YouTube trailer links.
    """
    async with TMDBClient(settings) as client:
        return await client.movie_details(movie_id)


@mcp.tool()
async def get_trending(
    media_type: Annotated[
        str, Field(description="One of: 'movie', 'tv', 'all'.")
    ] = "movie",
    time_window: Annotated[
        str, Field(description="'day' for today or 'week' for the last 7 days.")
    ] = "day",
) -> dict[str, Any]:
    """List what is trending on TMDB right now (movies, TV, or both)."""
    async with TMDBClient(settings) as client:
        return await client.trending(media_type=media_type, time_window=time_window)


@mcp.tool()
async def discover_movies(
    with_genres: Annotated[
        str | None,
        Field(description="Comma-separated TMDB genre ids, e.g. '28,12'. Use list_movie_genres to resolve names."),
    ] = None,
    primary_release_year: Annotated[
        int | None, Field(description="Restrict to a release year, e.g. 2021.")
    ] = None,
    sort_by: Annotated[
        str,
        Field(description="TMDB sort key, e.g. 'popularity.desc', 'vote_average.desc', 'revenue.desc'."),
    ] = "popularity.desc",
    min_rating: Annotated[
        float | None, Field(description="Minimum average vote (0-10).", ge=0, le=10)
    ] = None,
) -> dict[str, Any]:
    """Discover movies by filters (genre, year, rating) rather than by title.

    Ideal for open-ended recommendations like 'top rated sci-fi from 2019'.
    Resolve genre names to ids first with ``list_movie_genres``.
    """
    async with TMDBClient(settings) as client:
        return await client.discover_movies(
            with_genres=with_genres,
            primary_release_year=primary_release_year,
            sort_by=sort_by,
            vote_average_gte=min_rating,
        )


@mcp.tool()
async def search_person(
    name: Annotated[str, Field(description="Full or partial name of an actor, director, etc.")],
) -> dict[str, Any]:
    """Search TMDB for people (actors, directors, crew) by name."""
    async with TMDBClient(settings) as client:
        return await client.search_person(name)


@mcp.tool()
async def list_movie_genres() -> dict[str, int]:
    """Return the TMDB genre name -> id map (needed for ``discover_movies``)."""
    async with TMDBClient(settings) as client:
        return await client.genre_map()


def main() -> None:
    if not settings.tmdb_configured:
        logger.warning(
            "TMDB credentials are not set — movie tools will return an error until "
            "MCP_TMDB_READ_ACCESS_TOKEN or MCP_TMDB_API_KEY is provided."
        )
    logger.info("Starting MCP server on http://%s:%s/mcp", settings.host, settings.port)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
