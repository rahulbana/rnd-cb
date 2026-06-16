"""Orchestrator — coordinates the four agents end to end.

Flow:  plan  ->  search  ->  validate  ->  download  ->  manifest

Each stage's output feeds the next. The orchestrator owns logging, the run
manifest, and the overall policy (how many papers, confidence threshold).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

from .agents import DownloaderAgent, PlannerAgent, SearchAgent, ValidatorAgent
from .config import Settings
from .llm import LLMClient
from .models import (
    DownloadResult,
    PaperRequest,
    SearchPlan,
    SearchResult,
    ValidatedPaper,
    ValidationReport,
)


def _default_logger(message: str) -> None:
    print(message, flush=True)


@dataclass
class RunReport:
    """Everything produced by a single end-to-end run."""

    request: PaperRequest
    plan: Optional[SearchPlan] = None
    search: Optional[SearchResult] = None
    validation: Optional[ValidationReport] = None
    accepted: List[ValidatedPaper] = field(default_factory=list)
    downloads: List[DownloadResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict:
        return {
            "request": self.request.model_dump(),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "plan": self.plan.model_dump() if self.plan else None,
            "candidates_found": len(self.search.candidates) if self.search else 0,
            "accepted": [a.model_dump() for a in self.accepted],
            "downloads": [d.model_dump() for d in self.downloads],
            "summary": {
                "downloaded": sum(1 for d in self.downloads if d.success),
                "failed": sum(1 for d in self.downloads if not d.success),
            },
        }


class Orchestrator:
    """Drives the planner → searcher → validator → downloader pipeline."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        min_confidence: float = 0.5,
        dry_run: bool = False,
        logger: Callable[[str], None] = _default_logger,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self._log = logger
        llm = LLMClient(self.settings)
        self.planner = PlannerAgent(llm)
        self.searcher = SearchAgent(llm)
        self.validator = ValidatorAgent(llm, min_confidence=min_confidence)
        self.downloader = DownloaderAgent(self.settings, dry_run=dry_run)
        self._dry_run = dry_run

    def run(self, request: PaperRequest) -> RunReport:
        report = RunReport(
            request=request,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        self._log(f"[1/4] Planning   → {request.describe()}")
        report.plan = self.planner.run(request)
        self._log(
            f"        planned {len(report.plan.queries)} searches; "
            f"sources: {', '.join(report.plan.trusted_sources) or 'open web'}"
        )

        self._log("[2/4] Searching → running web searches")
        report.search = self.searcher.run(request, report.plan)
        # Respect the global candidate cap.
        report.search = SearchResult(
            candidates=report.search.candidates[: self.settings.max_candidates]
        )
        self._log(f"        found {len(report.search.candidates)} candidate(s)")

        self._log("[3/4] Validating → checking candidates against the request")
        report.validation = self.validator.run(request, report.plan, report.search)
        report.accepted = self.validator.accepted(report.validation)[
            : request.max_papers
        ]
        self._log(
            f"        accepted {len(report.accepted)} of "
            f"{len(report.validation.results)} assessed"
        )

        verb = "Would download" if self._dry_run else "Downloading"
        self._log(f"[4/4] {verb} → {len(report.accepted)} paper(s)")
        subdir = self._subdir(request)
        report.downloads = self.downloader.run(report.accepted, subdir=subdir)
        ok = sum(1 for d in report.downloads if d.success)
        for d in report.downloads:
            mark = "✓" if d.success else "✗"
            detail = d.path if d.success else d.error
            self._log(f"        {mark} {d.title} — {detail}")

        report.finished_at = datetime.now(timezone.utc).isoformat()
        self._write_manifest(report, subdir)
        self._log(f"Done. {ok}/{len(report.downloads)} downloaded.")
        return report

    @staticmethod
    def _subdir(request: PaperRequest) -> str:
        from .agents.downloader import _slugify

        return _slugify(
            f"{request.board}_class{request.klass}_{request.subject}"
        )

    def _write_manifest(self, report: RunReport, subdir: str) -> None:
        if self._dry_run:
            return
        dest = os.path.join(self.settings.output_dir, subdir)
        os.makedirs(dest, exist_ok=True)
        path = os.path.join(dest, "manifest.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report.to_dict(), fh, indent=2, ensure_ascii=False)
        self._log(f"        manifest written to {path}")
