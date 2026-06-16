"""Tiny shared HTTP helper used by the network-backed tools."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from .. import config

_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": config.USER_AGENT})
    return _session


def get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """GET ``url`` and return parsed JSON, raising for HTTP errors."""
    resp = _get_session().get(url, params=params, timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_text(url: str, params: Optional[Dict[str, Any]] = None) -> str:
    """GET ``url`` and return the response body as text."""
    resp = _get_session().get(url, params=params, timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def post_text(url: str, data: Optional[Dict[str, Any]] = None) -> str:
    """POST form ``data`` to ``url`` and return the response body as text."""
    resp = _get_session().post(url, data=data, timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.text
