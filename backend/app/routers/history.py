"""Query-history endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..deps import get_history_store
from ..schemas import HistoryItem, HistoryList
from ..services.history import HistoryStore

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryList)
def list_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    store: HistoryStore = Depends(get_history_store),
) -> HistoryList:
    items, total = store.list(limit=limit, offset=offset)
    return HistoryList(items=items, total=total)


@router.get("/{item_id}", response_model=HistoryItem)
def get_history_item(
    item_id: int,
    store: HistoryStore = Depends(get_history_store),
) -> HistoryItem:
    item = store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="History item not found.")
    return item


@router.delete("/{item_id}", status_code=204, response_class=Response)
def delete_history_item(
    item_id: int,
    store: HistoryStore = Depends(get_history_store),
) -> Response:
    if not store.delete(item_id):
        raise HTTPException(status_code=404, detail="History item not found.")
    return Response(status_code=204)


@router.delete("", status_code=204, response_class=Response)
def clear_history(store: HistoryStore = Depends(get_history_store)) -> Response:
    store.clear()
    return Response(status_code=204)
