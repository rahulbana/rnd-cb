"""Tool abstraction (spec section 20).

Agents access external capabilities exclusively through tools registered in the
:class:`ToolRegistry`, never by coupling directly to an SDK. Every tool returns
a :class:`ToolResult` carrying provenance so downstream data trust is preserved.
"""
from __future__ import annotations

import abc
from typing import Any

from pydantic import BaseModel, Field

from ..schemas.common import DataTrust, Freshness


class ToolResult(BaseModel):
    tool: str
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    trust: DataTrust = DataTrust.ESTIMATED
    freshness: Freshness = Freshness.UNKNOWN
    source: str = "internal"
    error: str | None = None


class Tool(abc.ABC):
    name: str = "tool"
    description: str = ""

    @abc.abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        ...

    def _ok(self, **data: Any) -> ToolResult:
        return ToolResult(tool=self.name, ok=True, data=data)

    def _fail(self, error: str) -> ToolResult:
        return ToolResult(tool=self.name, ok=False, error=error)
