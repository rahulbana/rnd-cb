"""Runtime dependencies injected into graph nodes via `config["configurable"]`.

LangGraph nodes are plain functions; they receive state + config. We stash the
non-serializable runtime deps (LLM client, search aggregator, progress emitter,
Langfuse handler) under a single `ctx` key so nodes can pull them with
`RuntimeContext.from_config(config)`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.llm import LLM
from app.models.schemas import ProgressEvent
from app.search import SearchAggregator


@dataclass
class RuntimeContext:
    settings: Settings
    llm: LLM
    aggregator: SearchAggregator
    job_id: str
    emit: Any = None            # ProgressEmitter | None
    langfuse_handler: Any = None

    def emit_progress(self, event: ProgressEvent) -> None:
        if self.emit is not None:
            self.emit(event)

    def callbacks(self) -> list:
        return [self.langfuse_handler] if self.langfuse_handler else []

    @classmethod
    def from_config(cls, config: dict) -> RuntimeContext:
        ctx = (config or {}).get("configurable", {}).get("ctx")
        if ctx is None:
            raise RuntimeError("RuntimeContext missing from graph config['configurable']['ctx']")
        return ctx
