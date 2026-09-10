"""Endpoints for generating, explaining, formatting and validating SQL."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..config import Settings, get_settings
from ..deps import get_history_store, resolve_dialect
from ..schemas import (
    ExplainRequest,
    ExplainResponse,
    FormatRequest,
    FormatResponse,
    GenerateRequest,
    GenerateResponse,
    ValidateRequest,
    ValidationResult,
)
from ..services import llm, sql_tools
from ..services.history import HistoryStore

router = APIRouter(tags=["sql"])


@router.post("/generate", response_model=GenerateResponse)
def generate(
    req: GenerateRequest,
    settings: Settings = Depends(get_settings),
    history: HistoryStore = Depends(get_history_store),
) -> GenerateResponse:
    dialect = resolve_dialect(settings, req.dialect)
    try:
        result = llm.generate_sql(req.question, req.schema_text, dialect, settings)
    except llm.LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - upstream/API failures
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}") from exc

    formatted = sql_tools.format_sql(result["sql"], dialect)
    validation = sql_tools.validate_sql(formatted, dialect)

    history_id = history.add(
        question=req.question,
        sql=formatted,
        explanation=result["explanation"],
        dialect=dialect,
        valid=validation.valid,
    )

    return GenerateResponse(
        sql=formatted,
        explanation=result["explanation"],
        tables_used=result.get("tables_used", []),
        assumptions=result.get("assumptions", []),
        validation=validation,
        history_id=history_id,
    )


@router.post("/explain", response_model=ExplainResponse)
def explain(
    req: ExplainRequest,
    settings: Settings = Depends(get_settings),
) -> ExplainResponse:
    dialect = resolve_dialect(settings, req.dialect)
    try:
        explanation = llm.explain_sql(req.sql, req.schema_text, dialect, settings)
    except llm.LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Explanation failed: {exc}") from exc
    return ExplainResponse(explanation=explanation)


@router.post("/format", response_model=FormatResponse)
def format_query(
    req: FormatRequest,
    settings: Settings = Depends(get_settings),
) -> FormatResponse:
    dialect = resolve_dialect(settings, req.dialect)
    return FormatResponse(sql=sql_tools.format_sql(req.sql, dialect))


@router.post("/validate", response_model=ValidationResult)
def validate(
    req: ValidateRequest,
    settings: Settings = Depends(get_settings),
) -> ValidationResult:
    dialect = resolve_dialect(settings, req.dialect)
    return sql_tools.validate_sql(req.sql, dialect)
