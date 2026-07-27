"""FastAPI application exposing the dataset generator.

Endpoints:
* ``POST /plan``      -> infer a :class:`DatasetSpec` from a prompt (review step)
* ``POST /generate``  -> plan + generate + analyse, returns a run summary
* ``POST /generate/spec`` -> generate from an explicit, edited spec
* ``GET  /scenarios`` -> list domain templates
* ``GET  /health``    -> liveness probe

The generate endpoints run synchronously here; for very large datasets the
design calls for offloading to Celery, which can wrap :class:`DatasetService`
unchanged.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.models.spec import DatasetSpec
from app.prompts.scenarios import SCENARIOS
from app.services.generator import DatasetService

app = FastAPI(title="ML Dataset Generator Agent", version="1.0.0")
_service = DatasetService()


class PlanRequest(BaseModel):
    prompt: str = Field(..., examples=["fraud detection dataset with 2% fraud rate"])


class GenerateRequest(BaseModel):
    prompt: str
    rows: int | None = None
    seed: int | None = None
    formats: list[str] = ["csv"]
    full: bool = True


class SpecGenerateRequest(BaseModel):
    spec: DatasetSpec
    formats: list[str] = ["csv"]
    full: bool = True


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "planner_backend": settings.planner_backend}


@app.get("/scenarios")
def scenarios() -> dict[str, Any]:
    return {
        key: {
            "task_type": cfg["task_type"].value,
            "domain": cfg["domain"],
            "keywords": cfg["keywords"],
            "n_features": len(cfg["features"]),
        }
        for key, cfg in SCENARIOS.items()
    }


@app.post("/plan")
def plan(req: PlanRequest) -> dict[str, Any]:
    spec = _service.plan(req.prompt)
    return spec.model_dump(mode="json")


@app.post("/generate")
def generate(req: GenerateRequest) -> dict[str, Any]:
    settings.ensure_dirs()
    try:
        result = _service.generate_from_prompt(
            req.prompt,
            rows=req.rows,
            seed=req.seed,
            formats=req.formats,
            full=req.full,
        )
    except Exception as exc:  # pragma: no cover - surfaced to client
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _payload(result)


@app.post("/generate/spec")
def generate_from_spec(req: SpecGenerateRequest) -> dict[str, Any]:
    settings.ensure_dirs()
    try:
        result = _service.generate_from_spec(
            req.spec, formats=req.formats, full=req.full
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _payload(result)


def _payload(result) -> dict[str, Any]:
    return {
        "summary": result.summary(),
        "data_dictionary": result.data_dictionary,
        "eda": result.eda,
        "validation": (
            {"passed": result.validation.passed, "checks": result.validation.checks}
            if result.validation
            else None
        ),
        "evaluation": (
            {
                "baseline_model": result.evaluation.baseline_model,
                "metrics": result.evaluation.metrics,
                "ml_readiness_score": result.evaluation.ml_readiness_score,
            }
            if result.evaluation
            else None
        ),
        "exports": result.exports,
    }
