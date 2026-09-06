"""Admin, analytics, feedback, evaluation, and trace routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import task_queue
from app.api.v1.deps_auth import get_current_user, require_admin
from app.api.v1.routes.chat import _build_chat_service
from app.api.v1.schemas import (
    AdminUserOut,
    AnalyticsResponse,
    CitationOut,
    FeedbackRequest,
    JobOut,
    ProviderCostOut,
    QueueMonitorResponse,
    ReprocessResponse,
    TraceResponse,
)
from app.core.config import settings
from app.core.registry import get_eval_harness
from app.db.base import get_db
from app.db.models import (
    ApiKey,
    Conversation,
    Document,
    Feedback,
    IngestionJob,
    Message,
    User,
)
from app.domain.interfaces import TaskQueue
from app.domain.models import Scorecard
from app.evaluation.rag_eval import DEFAULT_GOLDEN, run_eval
from app.services.analytics_service import AnalyticsService
from app.services.conversation_memory import ConversationMemory

router = APIRouter(tags=["admin"])


# --- Admin dashboard (admin-only) ------------------------------------------


@router.get("/admin/users", response_model=list[AdminUserOut])
async def admin_users(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> list[AdminUserOut]:
    stmt = select(User).where(User.org_id == admin.org_id)
    return [
        AdminUserOut(id=u.id, email=u.email, role=u.role, org_id=u.org_id)
        for u in db.execute(stmt).scalars().all()
    ]


@router.get("/admin/api-keys")
async def admin_api_keys(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> list[dict]:
    stmt = (
        select(ApiKey)
        .join(User, User.id == ApiKey.user_id)
        .where(User.org_id == admin.org_id)
    )
    return [
        {"id": k.id, "user_id": k.user_id, "scopes": k.scopes}
        for k in db.execute(stmt).scalars().all()
    ]


@router.get("/admin/queue", response_model=QueueMonitorResponse)
async def admin_queue(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> QueueMonitorResponse:
    monitor = AnalyticsService(db, admin.org_id).queue_monitor()
    return QueueMonitorResponse(**monitor)


@router.get("/admin/providers")
async def admin_providers(admin: User = Depends(require_admin)) -> dict[str, str]:
    """Active adapter behind every port -- the live wiring, for operators."""
    return {
        "llm": settings.LLM_PROVIDER,
        "embedder": settings.EMBEDDER_PROVIDER,
        "vector_store": settings.VECTOR_STORE_PROVIDER,
        "reranker": settings.RERANKER_PROVIDER,
        "retriever": settings.RETRIEVER_STRATEGY,
        "parser": settings.PARSER_STRATEGY,
        "chunker": settings.CHUNKER_STRATEGY,
        "storage": settings.STORAGE_PROVIDER,
        "task_queue": settings.TASK_QUEUE_PROVIDER,
        "tracer": settings.TRACER_PROVIDER,
        "eval_harness": settings.EVAL_HARNESS,
    }


@router.post("/admin/documents/{document_id}/reprocess", response_model=ReprocessResponse)
async def admin_reprocess(
    document_id: str,
    db: Session = Depends(get_db),
    queue: TaskQueue = Depends(task_queue),
    admin: User = Depends(require_admin),
) -> ReprocessResponse:
    document = db.get(Document, document_id)
    if document is None or document.org_id != admin.org_id:
        raise HTTPException(status_code=404, detail="Document not found")
    job = IngestionJob(
        document_id=document.id, stage="parsing", status="queued", progress=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    await queue.enqueue("ingest_document", document_id=document.id, job_id=job.id)
    db.refresh(job)
    return ReprocessResponse(
        document_id=document.id,
        job=JobOut(
            id=job.id,
            document_id=job.document_id,
            stage=job.stage,
            progress=job.progress,
            status=job.status,
            error=job.error,
            retries=job.retries,
        ),
    )


@router.get("/admin/analytics", response_model=AnalyticsResponse)
async def admin_analytics(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> AnalyticsResponse:
    result = AnalyticsService(db, admin.org_id).compute()
    return AnalyticsResponse(
        conversations=result.conversations,
        messages=result.messages,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_by_provider=[ProviderCostOut(**vars(c)) for c in result.cost_by_provider],
        latency_p50_ms=result.latency_p50_ms,
        latency_p95_ms=result.latency_p95_ms,
        latency_p99_ms=result.latency_p99_ms,
        top_documents=result.top_documents,
        feedback_up=result.feedback_up,
        feedback_down=result.feedback_down,
    )


@router.post("/admin/eval/run", response_model=Scorecard)
async def admin_eval_run(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> Scorecard:
    """Run the golden Q&A eval and return a pass/fail scorecard."""
    chat = _build_chat_service(db, admin)
    return await run_eval(
        chat,
        get_eval_harness(),
        DEFAULT_GOLDEN,
        namespace=admin.org_id,
        threshold=settings.EVAL_THRESHOLD,
    )


# --- Feedback + trace (any authenticated owner) ----------------------------


def _owned_message(message_id: str, db: Session, user: User) -> Message:
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    conv = db.get(Conversation, message.conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.post("/feedback", status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    _owned_message(body.message_id, db, user)
    rating = 1 if body.rating > 0 else -1
    feedback = Feedback(message_id=body.message_id, rating=rating, note=body.note)
    db.add(feedback)
    db.commit()
    return {"status": "recorded"}


@router.get("/messages/{message_id}/trace", response_model=TraceResponse)
async def message_trace(
    message_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TraceResponse:
    """Explain an answer: prompt version, provider, cost, and cited chunks."""
    message = _owned_message(message_id, db, user)
    citations = ConversationMemory.serialize_citations(message.citations)
    return TraceResponse(
        message_id=message.id,
        role=message.role,
        provider=message.provider,
        prompt_version=message.prompt_version,
        tokens_in=message.tokens_in,
        tokens_out=message.tokens_out,
        latency_ms=message.latency_ms,
        citations=[CitationOut(**c) for c in citations],
    )
