"""FastAPI application exposing the product description generator."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .generator import generate_variants, regenerate_section
from .models import (
    GenerateRequest,
    GenerateResponse,
    RegenerateSectionRequest,
    RegenerateSectionResponse,
    WritingStyle,
    DescriptionLength,
)

app = FastAPI(
    title="AI Product Description Generator",
    description="Generate structured e-commerce product descriptions with OpenAI.",
    version="1.0.0",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": settings.openai_model, "configured": bool(settings.openai_api_key)}


@app.get("/api/options")
def options() -> dict:
    """Expose available styles and lengths so the frontend stays in sync."""
    return {
        "styles": [s.value for s in WritingStyle],
        "lengths": [length.value for length in DescriptionLength],
        "sections": [
            "title",
            "short_description",
            "detailed_description",
            "key_features",
            "benefits",
            "seo_keywords",
            "meta_description",
        ],
    }


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    try:
        variants = generate_variants(req.product, req.config)
        return GenerateResponse(variants=variants)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}")


@app.post("/api/regenerate-section", response_model=RegenerateSectionResponse)
def regenerate(req: RegenerateSectionRequest) -> RegenerateSectionResponse:
    try:
        value = regenerate_section(req.product, req.config, req.section)
        return RegenerateSectionResponse(section=req.section, value=value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Regeneration failed: {exc}")
