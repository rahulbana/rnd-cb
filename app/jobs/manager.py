"""Async job manager: runs research graphs and fans out progress to subscribers.

Each job runs as a background asyncio task. Progress events emitted by graph
nodes are appended to a per-job history and pushed to every live subscriber
queue, so the SSE endpoint can (a) replay everything that happened before a
client connected and (b) tail new events until the job ends. A sentinel `None`
closes each subscriber stream.

The graph is run with `thread_id = job_id`, so the Postgres checkpointer stores
one resumable thread per job — the basis for crash recovery.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field

from app.budget import BudgetTracker
from app.config import Settings
from app.eval.factuality import FactualityReport, judge_report
from app.graph.builder import build_graph
from app.graph.checkpointer import open_checkpointer
from app.graph.context import RuntimeContext
from app.llm import LLM
from app.models.report import ResearchReport
from app.models.schemas import JobStatus, ProgressEvent, ResearchRequest
from app.observability import get_langfuse_handler
from app.search import SearchAggregator

logger = logging.getLogger(__name__)

_SENTINEL = None


@dataclass
class JobRecord:
    job_id: str
    request: ResearchRequest
    status: JobStatus = JobStatus.queued
    history: list[ProgressEvent] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    report: ResearchReport | None = None
    factuality: FactualityReport | None = None
    budget: BudgetTracker | None = None
    error: str | None = None
    task: asyncio.Task | None = None
    done: asyncio.Event = field(default_factory=asyncio.Event)


class JobManager:
    def __init__(self, settings: Settings, *, run_factuality: bool = True) -> None:
        self._settings = settings
        self._llm = LLM(settings)
        self._aggregator = SearchAggregator.from_settings(settings)
        self._jobs: dict[str, JobRecord] = {}
        self._run_factuality = run_factuality

    # ── lifecycle ────────────────────────────────────────────────────────────
    def create_job(self, request: ResearchRequest) -> JobRecord:
        job_id = uuid.uuid4().hex[:16]
        record = JobRecord(job_id=job_id, request=request)
        self._jobs[job_id] = record
        record.task = asyncio.create_task(self._run(record))
        return record

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[JobRecord]:
        return list(self._jobs.values())

    async def cancel(self, job_id: str) -> bool:
        record = self._jobs.get(job_id)
        if not record or not record.task or record.task.done():
            return False
        record.task.cancel()
        record.status = JobStatus.cancelled
        self._emit(record, phase="cancel", message="Job cancelled by request.",
                   status=JobStatus.cancelled)
        self._close(record)
        return True

    # ── pub/sub ──────────────────────────────────────────────────────────────
    def _emit(self, record: JobRecord, **kwargs) -> None:
        budget = record.budget
        event = ProgressEvent(
            job_id=record.job_id,
            iteration=budget.iterations if budget else 0,
            usd_spent=budget.usd_spent if budget else 0.0,
            **kwargs,
        )
        record.history.append(event)
        for q in list(record.subscribers):
            q.put_nowait(event)

    def _emit_event(self, record: JobRecord, event: ProgressEvent) -> None:
        record.history.append(event)
        for q in list(record.subscribers):
            q.put_nowait(event)

    def _close(self, record: JobRecord) -> None:
        record.done.set()
        for q in list(record.subscribers):
            q.put_nowait(_SENTINEL)

    async def subscribe(self, job_id: str):
        """Yield ProgressEvents for a job: replay history, then tail until done.

        Registering the subscriber and snapshotting history happen without an
        intervening `await`, so under asyncio's single-thread scheduling every
        event lands in exactly one of {backlog, queue} — none dropped, none
        duplicated. If the job already finished, a sentinel is queued so the
        stream still terminates after the backlog is drained.
        """
        record = self._jobs.get(job_id)
        if record is None:
            return
        q: asyncio.Queue = asyncio.Queue()
        record.subscribers.append(q)
        backlog = list(record.history)  # atomic wrt the append above (no await)
        if record.done.is_set():
            q.put_nowait(_SENTINEL)
        try:
            for event in backlog:
                yield event
            while True:
                event = await q.get()
                if event is _SENTINEL:
                    break
                yield event
        finally:
            if q in record.subscribers:
                record.subscribers.remove(q)

    # ── execution ────────────────────────────────────────────────────────────
    async def _run(self, record: JobRecord) -> None:
        req = record.request
        settings = self._settings

        max_iter = req.max_iterations or self._depth_iterations(req)
        max_cost = req.max_usd_cost or settings.max_usd_cost
        budget = BudgetTracker(max_iterations=max_iter, max_usd_cost=max_cost)
        record.budget = budget
        record.status = JobStatus.running

        handler = get_langfuse_handler(settings, job_id=record.job_id, topic=req.topic)
        ctx = RuntimeContext(
            settings=settings,
            llm=self._llm,
            aggregator=self._aggregator,
            job_id=record.job_id,
            emit=lambda ev: self._emit_event(record, ev),
            langfuse_handler=handler,
        )

        try:
            async with open_checkpointer(settings) as checkpointer:
                graph = build_graph(checkpointer=checkpointer)
                config = {
                    "configurable": {"ctx": ctx, "thread_id": record.job_id},
                    "recursion_limit": 2 + max_iter * 4 + 4,
                }
                initial: dict = {
                    "job_id": record.job_id,
                    "request": req,
                    "budget": budget,
                    "sources": [],
                    "iteration": 0,
                }
                final_state = await graph.ainvoke(initial, config=config)

            record.report = final_state.get("report")
            record.budget = final_state.get("budget", budget)

            if record.report is None:
                raise RuntimeError("graph finished without producing a report")

            stop_reason = final_state.get("stop_reason")
            record.status = (
                JobStatus.killed_budget if stop_reason and final_state.get("gaps")
                else JobStatus.completed
            )

            if self._run_factuality:
                await self._score_factuality(record, final_state, ctx)

            self._emit(
                record,
                phase="done",
                message=f"Research complete. Spent ${record.budget.usd_spent:.2f} "
                        f"over {record.budget.iterations} iteration(s).",
                status=record.status,
            )
        except asyncio.CancelledError:
            record.status = JobStatus.cancelled
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("job %s failed", record.job_id)
            record.status = JobStatus.failed
            record.error = str(exc)
            self._emit(record, phase="error", message=f"Job failed: {exc}",
                       status=JobStatus.failed)
        finally:
            self._close(record)

    async def _score_factuality(self, record: JobRecord, final_state: dict, ctx: RuntimeContext) -> None:
        try:
            self._emit(record, phase="eval", message="Running factuality evaluation…")
            fr = await judge_report(
                record.report,
                final_state.get("sources", []),
                self._llm,
                budget=record.budget,
                callbacks=ctx.callbacks(),
            )
            record.factuality = fr
            self._emit(
                record,
                phase="eval",
                message=f"Factuality score: {fr.score:.0%} "
                        f"({fr.supported} supported, {fr.contradicted} contradicted).",
                data={"factuality": fr.model_dump()},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("factuality eval failed for %s: %s", record.job_id, exc)

    @staticmethod
    def _depth_iterations(req: ResearchRequest) -> int:
        from app.models.schemas import ResearchDepth

        return {
            ResearchDepth.quick: 2,
            ResearchDepth.standard: 4,
            ResearchDepth.deep: 6,
        }[req.depth]
