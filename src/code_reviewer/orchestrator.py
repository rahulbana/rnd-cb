"""Coordinate the review agents across files and aggregate results."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

from .agents import ReviewAgent
from .collector import CodeFile
from .config import Settings
from .llm import LLMClient
from .models import CategoryResult, FileReview, ReviewReport

ProgressCallback = Callable[[str, str], None]


def run_review(
    settings: Settings,
    files: List[CodeFile],
    agents: List[ReviewAgent],
    client: Optional[LLMClient] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> ReviewReport:
    """Run every agent against every file concurrently and aggregate.

    Each (file, agent) pair is an independent LLM call, dispatched to a
    thread pool since the calls are I/O bound.
    """
    client = client or LLMClient(settings.model)

    # Group results by file so the report stays organised.
    results_by_file: dict[str, List[CategoryResult]] = {
        f.relpath: [] for f in files
    }

    tasks = [(f, agent) for f in files for agent in agents]

    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_map = {
            executor.submit(
                agent.review_file, client, code_file, settings.language
            ): (code_file, agent)
            for code_file, agent in tasks
        }
        for future in as_completed(future_map):
            code_file, agent = future_map[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - never lose a result
                result = CategoryResult(
                    category=agent.category,
                    file_path=code_file.relpath,
                    error=str(exc),
                )
            results_by_file[code_file.relpath].append(result)
            if on_progress is not None:
                on_progress(code_file.relpath, agent.category)

    file_reviews: List[FileReview] = []
    for code_file in files:
        results = results_by_file[code_file.relpath]
        # Keep agent/category order stable in the output.
        results.sort(
            key=lambda r: [a.category for a in agents].index(r.category)
            if r.category in [a.category for a in agents]
            else len(agents)
        )
        file_reviews.append(
            FileReview(file_path=code_file.relpath, results=results)
        )

    return ReviewReport(
        root=settings.path,
        language=settings.language,
        model=settings.model,
        files=file_reviews,
    )
