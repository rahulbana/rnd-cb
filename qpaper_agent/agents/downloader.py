"""Downloader agent — stage 4.

Takes the validated papers and fetches them to disk. This stage is deliberately
deterministic (plain HTTP, no LLM): by the time we get here the LLM-driven
stages have already decided *what* to download.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, List
from urllib.parse import unquote, urlparse

import requests

from ..config import Settings
from ..models import DownloadResult, ValidatedPaper

# Browser-ish UA: some education portals reject the default requests UA.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _slugify(text: str, fallback: str = "paper") -> str:
    slug = _SAFE_NAME.sub("_", text).strip("_")
    return slug or fallback


class DownloaderAgent:
    """Downloads validated papers, skipping anything that is not a real file."""

    name = "downloader"

    def __init__(self, settings: Settings, dry_run: bool = False) -> None:
        self._settings = settings
        self._dry_run = dry_run

    def run(
        self,
        papers: Iterable[ValidatedPaper],
        subdir: str = "",
    ) -> List[DownloadResult]:
        dest = os.path.join(self._settings.output_dir, subdir) if subdir else (
            self._settings.output_dir
        )
        if not self._dry_run:
            os.makedirs(dest, exist_ok=True)

        results: List[DownloadResult] = []
        for vp in papers:
            results.append(self._download_one(vp, dest))
        return results

    def _download_one(self, vp: ValidatedPaper, dest: str) -> DownloadResult:
        cand = vp.candidate
        if self._dry_run:
            return DownloadResult(
                title=cand.title,
                url=cand.url,
                path=os.path.join(dest, self._filename(vp)),
                success=True,
                error="dry-run: not downloaded",
            )

        try:
            resp = requests.get(
                cand.url,
                headers=_HEADERS,
                timeout=self._settings.request_timeout,
                stream=True,
                allow_redirects=True,
            )
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "").lower()
            # Reject obvious HTML landing pages — we want actual paper files.
            if "text/html" in content_type and not cand.url.lower().endswith(".pdf"):
                return DownloadResult(
                    title=cand.title,
                    url=cand.url,
                    success=False,
                    error=f"Skipped: response was HTML ({content_type}), not a file.",
                )

            path = os.path.join(dest, self._filename(vp, content_type))
            written = 0
            with open(path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
                        written += len(chunk)

            if written == 0:
                os.remove(path)
                return DownloadResult(
                    title=cand.title,
                    url=cand.url,
                    success=False,
                    error="Empty response body.",
                )

            return DownloadResult(
                title=cand.title,
                url=cand.url,
                path=path,
                success=True,
                bytes_written=written,
            )
        except Exception as exc:  # network / IO / HTTP errors.
            return DownloadResult(
                title=cand.title, url=cand.url, success=False, error=str(exc)
            )

    def _filename(self, vp: ValidatedPaper, content_type: str = "") -> str:
        cand = vp.candidate
        # Try to keep a sensible extension.
        url_name = os.path.basename(urlparse(unquote(cand.url)).path)
        _, ext = os.path.splitext(url_name)
        if not ext:
            ext = ".pdf" if "pdf" in content_type or cand.is_pdf else ".bin"

        parts = [
            cand.board or "",
            f"class{cand.klass}" if cand.klass else "",
            cand.subject or "",
            str(cand.year) if cand.year else "",
            cand.title,
        ]
        base = _slugify("_".join(p for p in parts if p))
        return f"{base}{ext}"
