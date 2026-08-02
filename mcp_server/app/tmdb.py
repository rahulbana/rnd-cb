"""Thin async client around the TMDB REST API.

The client is intentionally small: it centralises auth, error handling and
response shaping so the MCP tool functions stay declarative. Responses are
trimmed to the fields that are useful to an LLM agent to keep tool payloads
compact and cheap to reason over.
"""

from __future__ import annotations

from typing import Any

import httpx

from .settings import Settings


class TMDBError(RuntimeError):
    """Raised when TMDB returns an error or is not configured."""


class TMDBClient:
    """Async wrapper over the TMDB v3 API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle -----------------------------------------------------------
    async def __aenter__(self) -> "TMDBClient":
        self._client = httpx.AsyncClient(
            base_url=self._settings.tmdb_base_url,
            timeout=self._settings.tmdb_timeout_seconds,
            headers=self._auth_headers(),
        )
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._settings.tmdb_read_access_token:
            headers["Authorization"] = f"Bearer {self._settings.tmdb_read_access_token}"
        return headers

    # -- core request --------------------------------------------------------
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._settings.tmdb_configured:
            raise TMDBError(
                "TMDB is not configured. Set MCP_TMDB_READ_ACCESS_TOKEN or "
                "MCP_TMDB_API_KEY in the server environment."
            )
        assert self._client is not None, "TMDBClient must be used as an async context manager"

        query = dict(params or {})
        # v3 API keys are passed as a query param; v4 tokens go in the header.
        if self._settings.tmdb_api_key and not self._settings.tmdb_read_access_token:
            query["api_key"] = self._settings.tmdb_api_key

        try:
            response = await self._client.get(path, params=query)
        except httpx.RequestError as exc:  # network / DNS / timeout
            raise TMDBError(f"Could not reach TMDB: {exc}") from exc

        if response.status_code == 401:
            raise TMDBError("TMDB authentication failed. Check your API credentials.")
        if response.status_code == 404:
            raise TMDBError("The requested TMDB resource was not found.")
        if response.status_code >= 400:
            raise TMDBError(f"TMDB returned HTTP {response.status_code}: {response.text[:200]}")

        return response.json()

    def _poster_url(self, path: str | None, size: str = "w500") -> str | None:
        if not path:
            return None
        return f"{self._settings.tmdb_image_base_url}/{size}{path}"

    # -- shaping helpers -----------------------------------------------------
    def _shape_movie(self, movie: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": movie.get("id"),
            "title": movie.get("title") or movie.get("name"),
            "release_date": movie.get("release_date") or movie.get("first_air_date"),
            "overview": movie.get("overview"),
            "rating": movie.get("vote_average"),
            "vote_count": movie.get("vote_count"),
            "popularity": movie.get("popularity"),
            "genre_ids": movie.get("genre_ids"),
            "poster_url": self._poster_url(movie.get("poster_path")),
        }

    def _shape_person(self, person: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": person.get("id"),
            "name": person.get("name"),
            "known_for_department": person.get("known_for_department"),
            "popularity": person.get("popularity"),
            "profile_url": self._poster_url(person.get("profile_path")),
            "known_for": [
                (item.get("title") or item.get("name"))
                for item in person.get("known_for", [])
            ],
        }

    # -- public tool operations ---------------------------------------------
    async def search_movies(self, query: str, *, page: int = 1) -> dict[str, Any]:
        data = await self._get(
            "/search/movie",
            {"query": query, "page": page, "include_adult": "false"},
        )
        return {
            "query": query,
            "page": data.get("page", page),
            "total_results": data.get("total_results", 0),
            "results": [self._shape_movie(m) for m in data.get("results", [])[:10]],
        }

    async def movie_details(self, movie_id: int) -> dict[str, Any]:
        data = await self._get(
            f"/movie/{movie_id}",
            {"append_to_response": "credits,videos"},
        )
        credits = data.get("credits", {})
        cast = [
            {"name": c.get("name"), "character": c.get("character")}
            for c in credits.get("cast", [])[:8]
        ]
        directors = [
            c.get("name")
            for c in credits.get("crew", [])
            if c.get("job") == "Director"
        ]
        trailers = [
            f"https://www.youtube.com/watch?v={v.get('key')}"
            for v in data.get("videos", {}).get("results", [])
            if v.get("site") == "YouTube" and v.get("type") == "Trailer"
        ]
        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "tagline": data.get("tagline"),
            "release_date": data.get("release_date"),
            "runtime_minutes": data.get("runtime"),
            "genres": [g.get("name") for g in data.get("genres", [])],
            "overview": data.get("overview"),
            "rating": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "budget": data.get("budget"),
            "revenue": data.get("revenue"),
            "homepage": data.get("homepage"),
            "poster_url": self._poster_url(data.get("poster_path")),
            "directors": directors,
            "top_cast": cast,
            "trailers": trailers[:3],
        }

    async def trending(self, *, media_type: str = "movie", time_window: str = "day") -> dict[str, Any]:
        if media_type not in {"movie", "tv", "all"}:
            raise TMDBError("media_type must be one of: movie, tv, all")
        if time_window not in {"day", "week"}:
            raise TMDBError("time_window must be 'day' or 'week'")
        data = await self._get(f"/trending/{media_type}/{time_window}")
        return {
            "media_type": media_type,
            "time_window": time_window,
            "results": [self._shape_movie(m) for m in data.get("results", [])[:10]],
        }

    async def discover_movies(
        self,
        *,
        with_genres: str | None = None,
        primary_release_year: int | None = None,
        sort_by: str = "popularity.desc",
        vote_average_gte: float | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"sort_by": sort_by, "include_adult": "false"}
        if with_genres:
            params["with_genres"] = with_genres
        if primary_release_year:
            params["primary_release_year"] = primary_release_year
        if vote_average_gte is not None:
            params["vote_average.gte"] = vote_average_gte
            params["vote_count.gte"] = 100  # avoid noisy low-vote outliers
        data = await self._get("/discover/movie", params)
        return {
            "filters": params,
            "total_results": data.get("total_results", 0),
            "results": [self._shape_movie(m) for m in data.get("results", [])[:10]],
        }

    async def search_person(self, name: str) -> dict[str, Any]:
        data = await self._get("/search/person", {"query": name, "include_adult": "false"})
        return {
            "query": name,
            "results": [self._shape_person(p) for p in data.get("results", [])[:5]],
        }

    async def genre_map(self) -> dict[str, int]:
        data = await self._get("/genre/movie/list")
        return {g["name"]: g["id"] for g in data.get("genres", [])}
