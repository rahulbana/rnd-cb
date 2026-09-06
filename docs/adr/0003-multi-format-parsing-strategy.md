# ADR 0003 — Multi-format parsing strategy & fallback chain

- Status: Accepted
- Date: 2026-09-06
- Phase: 2

## Context

Any uploaded file — PDF, DOCX, TXT, MD, PNG/JPG (scanned) — must become the
same canonical `ParsedDocument`. No single parser is best for every format,
and a silent drop from a strong parser to a weak one quietly degrades answer
quality.

## Decision

Each parser is an adapter behind the `Parser` port and declares which MIME
types it `supports()`. A `ParserRouter` (itself a `Parser`) selects, per MIME
type, an ordered **fallback chain** from `PARSER_PRIORITY` and tries each in
turn; a parser that raises is skipped and the next runs. When a non-primary
parser succeeds, the result is flagged `used_fallback=True` and the fallback is
logged — never silent (per the plan's parser-fallback-correctness risk).

Parsers shipped in Phase 2:

| Adapter | Handles | Notes |
|---|---|---|
| `plain` | txt, md | stdlib; keeps Markdown headings for chunk boundaries |
| `pymupdf` | pdf | fast path for text-heavy, digitally-native PDFs |
| `docx` | docx | lightweight (python-docx); fully local, testable |
| `tesseract_image` | png/jpg/tiff/… | OCR path for scanned images |
| `docling` | pdf, docx, pptx, html, images (+OCR) | production primary; heavy ML deps, lazy-imported |
| `unstructured` | eml, html, office, pdf | alternate pipeline / second opinion |

Heavy imports (Docling, Unstructured, PyMuPDF, Tesseract) are **lazy** — pulled
in only when a parser actually runs — so the app boots and unrelated tests run
without them. Docling/Unstructured are an optional `parsers-heavy` extra;
they're installed in the container image.

The default local/dev priority puts lightweight, fully-local parsers first
(`plain,pymupdf,docx,tesseract_image,…`) with Docling/Unstructured as
fallbacks. Production may reorder to put Docling first for layout- and
table-heavy corpora.

## Consequences

- Adding a format or a better parser is a new adapter plus one entry in
  `PARSER_PRIORITY`; no route or service changes.
- The exit test uploads a PDF, DOCX, scanned PNG, and Markdown file and asserts
  an identical canonical shape from each (`tests/test_upload.py`).
- Tesseract is a system dependency (installed in the Docker images and CI); the
  OCR tests skip cleanly where the binary is absent.
- Object storage is now a real `local_disk` adapter (raw files are content-
  addressed by `org_id/checksum`); GCS/S3 implement the same port later.
