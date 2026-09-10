"""Analysis API routes."""
import csv
import io

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..aggregate import summarize
from ..analyzer import analyze_text
from ..config import get_settings
from ..schemas import (
    AnalysisResult,
    AnalyzeRequest,
    BatchAnalysisResponse,
    BatchAnalyzeRequest,
)

router = APIRouter(prefix="/api", tags=["analysis"])


def _analyze_many(texts: list[str]) -> list[AnalysisResult]:
    settings = get_settings()
    cleaned = [t.strip() for t in texts if t and t.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail="No non-empty texts provided.")
    if len(cleaned) > settings.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch too large. Max is {settings.max_batch_size} items.",
        )
    results: list[AnalysisResult] = []
    for text in cleaned:
        try:
            results.append(analyze_text(text))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Analysis failed: {exc}")
    return results


@router.post("/analyze", response_model=AnalysisResult)
def analyze_single(req: AnalyzeRequest) -> AnalysisResult:
    """Analyze a single piece of text."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    try:
        return analyze_text(req.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Analysis failed: {exc}")


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
def analyze_batch(req: BatchAnalyzeRequest) -> BatchAnalysisResponse:
    """Analyze a list of texts and return per-item results plus aggregate stats."""
    results = _analyze_many(req.texts)
    return BatchAnalysisResponse(results=results, summary=summarize(results))


@router.post("/analyze/csv", response_model=BatchAnalysisResponse)
async def analyze_csv(
    file: UploadFile = File(...),
    column: str | None = None,
) -> BatchAnalysisResponse:
    """Analyze texts from an uploaded CSV file.

    If a `column` is given, that column is used. Otherwise the first column
    named one of text/review/comment/content/message is used, falling back to
    the first column in the file.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    raw = await file.read()
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = raw.decode("latin-1")

    reader = csv.reader(io.StringIO(decoded))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty.")

    header = [h.strip() for h in rows[0]]
    preferred = ["text", "review", "comment", "content", "message", "feedback"]
    lower_header = [h.lower() for h in header]

    # Decide whether the first row is a header.
    has_header = any(h in preferred for h in lower_header) or (column is not None)

    if column is not None:
        if column not in header:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{column}' not found. Available: {header}",
            )
        col_idx = header.index(column)
        data_rows = rows[1:]
    elif has_header:
        col_idx = next(
            (lower_header.index(p) for p in preferred if p in lower_header), 0
        )
        data_rows = rows[1:]
    else:
        # No header: treat every row's first column as text.
        col_idx = 0
        data_rows = rows

    texts = [row[col_idx] for row in data_rows if len(row) > col_idx]
    results = _analyze_many(texts)
    return BatchAnalysisResponse(results=results, summary=summarize(results))
