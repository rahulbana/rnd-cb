"""FastAPI dependency providers."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from ..core.config import Settings, get_settings
from ..persistence.store import RunStore, build_run_store
from ..services.search_service import SearchService

SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_run_store() -> RunStore:
    """Single shared run store for the process."""
    return build_run_store(get_settings())


RunStoreDep = Annotated[RunStore, Depends(get_run_store)]


def get_search_service(settings: SettingsDep, store: RunStoreDep) -> SearchService:
    return SearchService(settings, store)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
