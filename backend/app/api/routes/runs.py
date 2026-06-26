"""Run-history endpoints: list past runs and fetch a single run's full trace."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from ...persistence.models import RunRecord, RunSummary
from ..deps import RunStoreDep, SettingsDep

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=List[RunSummary])
async def list_runs(
    store: RunStoreDep,
    settings: SettingsDep,
    limit: int = Query(default=50, ge=1, le=500),
) -> List[RunSummary]:
    return await store.list(limit=min(limit, settings.runs_list_limit))


@router.get("/runs/{run_id}", response_model=RunRecord)
async def get_run(run_id: str, store: RunStoreDep) -> RunRecord:
    record = await store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return record
