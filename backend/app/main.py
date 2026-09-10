"""FastAPI application exposing the AI JSON Generator API."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .config import get_settings
from .generator import GenerationError, JSONGenerator
from .models import (
    GenerateRequest,
    GenerateResponse,
    ValidateRequest,
    ValidateResponse,
)
from .validator import SchemaInvalidError, validate

settings = get_settings()

app = FastAPI(
    title="AI JSON Generator",
    description="Convert natural language into validated JSON.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

generator = JSONGenerator(settings)


@app.get("/api/health")
def health() -> dict[str, object]:
    """Report service status and whether an API key is configured."""
    return {
        "status": "ok",
        "configured": settings.is_configured,
        "model": settings.model,
    }


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    """Generate validated JSON from a natural-language prompt."""
    try:
        result = generator.generate(request.prompt, request.schema_)
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SchemaInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface upstream errors cleanly
        raise HTTPException(
            status_code=502, detail=f"LLM request failed: {exc}"
        ) from exc

    return GenerateResponse(
        data=result.data,
        valid=result.valid,
        attempts=result.attempts,
        errors=result.errors,  # type: ignore[arg-type]
        raw_output=result.raw_output,
    )


@app.post("/api/validate", response_model=ValidateResponse)
def validate_endpoint(request: ValidateRequest) -> ValidateResponse:
    """Validate a JSON value against a JSON Schema."""
    try:
        errors = validate(request.data, request.schema_)
    except SchemaInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ValidateResponse(valid=not errors, errors=errors)  # type: ignore[arg-type]


@app.post("/api/download")
def download(request: GenerateRequest) -> Response:
    """Generate JSON and return it as a downloadable file attachment."""
    try:
        result = generator.generate(request.prompt, request.schema_)
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SchemaInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"LLM request failed: {exc}"
        ) from exc

    body = json.dumps(result.data, indent=2, ensure_ascii=False)
    return JSONResponse(
        content=json.loads(body),
        headers={"Content-Disposition": 'attachment; filename="generated.json"'},
    )
