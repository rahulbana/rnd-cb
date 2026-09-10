from fastapi import APIRouter, HTTPException

from ..schemas import (
    ArticleRequest,
    ArticleResponse,
    MetaDescriptionRequest,
    MetaDescriptionResponse,
    OutlineRequest,
    OutlineResponse,
    RewriteRequest,
    RewriteResponse,
    SectionRequest,
    SectionResponse,
    TitleRequest,
    TitleResponse,
)
from ..services import llm

router = APIRouter(prefix="/api", tags=["generate"])


def _guard(func, *args, **kwargs):
    """Run an LLM call and translate LLMError into a clean 400/502 response."""
    try:
        return func(*args, **kwargs)
    except llm.LLMError as exc:
        message = str(exc)
        status = 400 if "OPENAI_API_KEY" in message else 502
        raise HTTPException(status_code=status, detail=message) from exc


@router.post("/outline", response_model=OutlineResponse)
def outline(req: OutlineRequest) -> OutlineResponse:
    items = _guard(llm.generate_outline, req)
    return OutlineResponse(outline=items)


@router.post("/section", response_model=SectionResponse)
def section(req: SectionRequest) -> SectionResponse:
    content = _guard(
        llm.generate_section,
        req,
        req.heading,
        req.section_summary,
        req.outline,
    )
    return SectionResponse(heading=req.heading, content=content)


@router.post("/title", response_model=TitleResponse)
def title(req: TitleRequest) -> TitleResponse:
    titles = _guard(llm.generate_titles, req)
    return TitleResponse(titles=titles)


@router.post("/meta-description", response_model=MetaDescriptionResponse)
def meta_description(req: MetaDescriptionRequest) -> MetaDescriptionResponse:
    text = _guard(llm.generate_meta_description, req)
    return MetaDescriptionResponse(meta_description=text)


@router.post("/rewrite", response_model=RewriteResponse)
def rewrite(req: RewriteRequest) -> RewriteResponse:
    content = _guard(
        llm.rewrite_section, req, req.heading, req.content, req.instruction
    )
    return RewriteResponse(heading=req.heading, content=content)


@router.post("/article", response_model=ArticleResponse)
def article(req: ArticleRequest) -> ArticleResponse:
    result = _guard(llm.generate_article, req)
    return ArticleResponse(**result)
