"""Remote MCP server exposing TMDB, translation, and world-time tools.

Run with::

    python -m app.server

The server speaks the MCP *streamable-HTTP* transport, so any MCP-capable
client (including the LangGraph backend in this repo) can connect over the
network at ``http://<host>:<port>/mcp``.

Every tool has a rich docstring: the docstring *is* the tool description the
LLM sees, so it is written to guide correct tool selection and argument use.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

from . import timetools, translation
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
    name="movies-and-utilities",
    instructions=(
        "Tools for The Movie Database (TMDB) plus general utilities: language "
        "translation and world-time/timezone calculations. Prefer these tools "
        "over guessing when a user asks about films, actors, showtimes across "
        "regions, or translations."
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


# ---------------------------------------------------------------------------
# Translation tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def translate(
    text: Annotated[str, Field(description="The text to translate.")],
    target_language: Annotated[
        str, Field(description="Target language as ISO code ('es') or name ('spanish').")
    ],
    source_language: Annotated[
        str, Field(description="Source language, or 'auto' to detect.")
    ] = "auto",
) -> dict[str, Any]:
    """Translate text between languages (source auto-detected by default).

    Accepts either ISO 639-1 codes (``en``, ``fr``, ``ja``) or plain language
    names (``english``, ``french``, ``japanese``).
    """
    return await translation.translate_text(text, target_language, source_language)


@mcp.tool()
def list_supported_languages() -> dict[str, str]:
    """Return supported translation languages as a name -> ISO code map."""
    return translation.list_languages()


# ---------------------------------------------------------------------------
# World-time tools
# ---------------------------------------------------------------------------
@mcp.tool()
def get_current_time(
    location: Annotated[
        str, Field(description="City, country, or IANA timezone, e.g. 'Tokyo' or 'Asia/Tokyo'.")
    ],
) -> dict[str, Any]:
    """Get the current local date/time and UTC offset for a location."""
    return timetools.current_time(location)


@mcp.tool()
def compare_timezones(
    location_a: Annotated[str, Field(description="First city/country/timezone.")],
    location_b: Annotated[str, Field(description="Second city/country/timezone.")],
) -> dict[str, Any]:
    """Compare the current time in two locations and report the hour difference."""
    return timetools.compare_timezones(location_a, location_b)


@mcp.tool()
def convert_time(
    time_str: Annotated[str, Field(description="A 24-hour time 'HH:MM', e.g. '14:30'.")],
    from_location: Annotated[str, Field(description="Source city/country/timezone.")],
    to_location: Annotated[str, Field(description="Target city/country/timezone.")],
) -> dict[str, Any]:
    """Convert a wall-clock time (today) from one location's zone to another's."""
    return timetools.convert_time(time_str, from_location, to_location)


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
