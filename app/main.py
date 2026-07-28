"""FastAPI application: submit research jobs, stream progress over SSE, fetch
reports, and export to Word/PDF."""

from __future__ import annotations

import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.export import export_docx, export_pdf
from app.jobs import JobManager
from app.models.schemas import JobStatus, ResearchRequest

FRONTEND = Path(__file__).parent.parent / "frontend" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.manager = JobManager(settings)
    app.state.settings = settings
    yield


app = FastAPI(title="Deep Research Agent", version="0.1.0", lifespan=lifespan)


def _manager(app: FastAPI) -> JobManager:
    return app.state.manager


@app.get("/healthz")
async def healthz():
    s = get_settings()
    return {
        "status": "ok",
        "backends": s.enabled_backends(),
        "checkpointer": "postgres" if s.has_postgres else "memory",
        "langfuse": s.has_langfuse,
        "llm_configured": bool(s.anthropic_api_key),
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    if FRONTEND.exists():
        return HTMLResponse(FRONTEND.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Deep Research Agent</h1><p>Frontend not found.</p>")


@app.post("/research")
async def start_research(request: ResearchRequest):
    record = _manager(app).create_job(request)
    return JSONResponse(
        {"job_id": record.job_id, "status": record.status.value},
        status_code=202,
    )


@app.get("/research/{job_id}/stream")
async def stream(job_id: str):
    manager = _manager(app)
    if manager.get(job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_gen():
        async for event in manager.subscribe(job_id):
            yield {
                "event": event.phase,
                "data": event.model_dump_json(),
            }
        yield {"event": "end", "data": json.dumps({"job_id": job_id})}

    return EventSourceResponse(event_gen())


@app.get("/research/{job_id}")
async def get_job(job_id: str):
    record = _manager(app).get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "job_id": record.job_id,
        "status": record.status.value,
        "topic": record.request.topic,
        "error": record.error,
        "usd_spent": record.budget.usd_spent if record.budget else 0.0,
        "iterations": record.budget.iterations if record.budget else 0,
        "factuality": record.factuality.model_dump() if record.factuality else None,
        "report": record.report.model_dump() if record.report else None,
    }


@app.get("/research/{job_id}/report.md")
async def get_markdown(job_id: str):
    record = _require_report(job_id)
    return HTMLResponse(record.report.to_markdown(), media_type="text/markdown")


@app.get("/research/{job_id}/export")
async def export(job_id: str, format: str = Query("pdf", pattern="^(pdf|docx)$")):
    record = _require_report(job_id)
    suffix = ".pdf" if format == "pdf" else ".docx"
    tmp = Path(tempfile.gettempdir()) / f"report_{job_id}{suffix}"
    if format == "pdf":
        export_pdf(record.report, tmp)
        media = "application/pdf"
    else:
        export_docx(record.report, tmp)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(str(tmp), media_type=media, filename=f"report{suffix}")


@app.post("/research/{job_id}/cancel")
async def cancel(job_id: str):
    ok = await _manager(app).cancel(job_id)
    if not ok:
        raise HTTPException(status_code=409, detail="job not cancellable")
    return {"job_id": job_id, "status": JobStatus.cancelled.value}


def _require_report(job_id: str):
    record = _manager(app).get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="job not found")
    if record.report is None:
        raise HTTPException(status_code=409, detail=f"report not ready (status: {record.status.value})")
    return record
