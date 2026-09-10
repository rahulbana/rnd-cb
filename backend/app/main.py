from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import generate

app = FastAPI(
    title="AI Blog Generator API",
    description="Multi-step, prompt-chained blog article generation powered by OpenAI.",
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

app.include_router(generate.router)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "model": settings.openai_model,
        "openai_configured": bool(settings.openai_api_key),
    }
