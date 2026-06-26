"""FastAPI dependency providers."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from ..core.config import Settings, get_settings
from ..services.search_service import SearchService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_search_service(settings: SettingsDep) -> SearchService:
    return SearchService(settings)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
