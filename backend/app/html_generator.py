"""Render a StudyMaterial into self-contained, printable HTML documents.

Three variants are produced:
- notes only
- questions with answers
- questions only (no answers) — a clean practice/exam sheet
"""
from __future__ import annotations

import html
import re
from datetime import datetime

from .schemas import QUESTION_TYPE_LABELS, StudyMaterial


def _e(value) -> str:
    return html.escape(str(value if value is not None else ""))


def render_html(
    material: StudyMaterial,
    source_filename: str,
    grade_level: str = "",
    *,
    include_notes: bool = True,
    include_questions: bool = True,
    include_answers: bool = True,
    doc_label: str = "",
    sources: list[str] | None = None,
) -> str:
    """Render an HTML document with the requested sections."""
    notes = material.notes
    q = material.questions
    base_title = notes.title or "Study Material"
    title = f"{base_title} — {doc_label}" if doc_label else base_title
    generated = datetime.now().strftime("%d %b %Y, %I:%M %p")

    parts: list[str] = []
    parts.append(_HEAD.format(title=_e(title)))

    # ---- Header -----------------------------------------------------------
    parts.append('<header class="doc-header">')
    parts.append(f"<h1>{_e(title)}</h1>")
    meta = [f"Source: {_e(source_filename)}"]
    if grade_level:
        meta.append(f"Level: {_e(grade_level)}")
    meta.append(f"Generated: {_e(generated)}")
    parts.append('<p class="meta">' + " &nbsp;•&nbsp; ".join(meta) + "</p>")
    parts.append("</header>")

    # ---- Notes ------------------------------------------------------------
    if include_notes:
        _render_notes(parts, notes)

    # ---- Questions --------------------------------------------------------
    if include_questions:
        _render_true_false(parts, q.true_false, include_answers)
        _render_mcq(parts, q.mcq, include_answers)
        _render_fill(parts, q.fill_blanks, include_answers)
        _render_simple(parts, "very_short", q.very_short, include_answers)
        _render_simple(parts, "short", q.short, include_answers)
        _render_simple(parts, "long", q.long, include_answers)
        _render_case(parts, q.case_based, include_answers)

    # ---- References (from online research) --------------------------------
    if sources:
        parts.append('<section class="refs card"><h2>🌐 References</h2>')
        parts.append(
            '<p class="refs-note">Reference material gathered from reputable '
            "educational sources online to enrich this material.</p><ol class='refs-list'>"
        )
        for url in sources:
            safe = _e(url)
            parts.append(f'<li><a href="{safe}" target="_blank" rel="noopener">{safe}</a></li>')
        parts.append("</ol></section>")

    parts.append(_FOOTER)
    return "".join(parts)


def render_variants(
    material: StudyMaterial,
    source_filename: str,
    grade_level: str = "",
    sources: list[str] | None = None,
) -> dict[str, str]:
    """Produce the three downloadable HTML documents."""
    return {
        "notes": render_html(
            material, source_filename, grade_level,
            include_notes=True, include_questions=False, doc_label="Notes",
            sources=sources,
        ),
        "questions_with_answers": render_html(
            material, source_filename, grade_level,
            include_notes=False, include_questions=True, include_answers=True,
            doc_label="Questions & Answers", sources=sources,
        ),
        # Keep the practice sheet clean — no reference list.
        "questions_only": render_html(
            material, source_filename, grade_level,
            include_notes=False, include_questions=True, include_answers=False,
            doc_label="Question Paper",
        ),
    }


def _slug(text: str, i: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return f"sec-{i}-{base}"[:60] or f"sec-{i}"


def _paragraphs(text: str) -> str:
    """Split a prose block into <p> paragraphs on blank lines / newlines."""
    blocks = re.split(r"\n\s*\n", str(text).strip())
    out = []
    for b in blocks:
        b = b.strip()
        if b:
            out.append(f"<p>{_e(b)}</p>")
    return "".join(out)


def _render_notes(parts: list[str], notes) -> None:
    sections = notes.sections or []

    parts.append('<section class="notes card"><h2>📘 Study Notes</h2>')
    if notes.summary:
        parts.append(f'<p class="summary">{_e(notes.summary)}</p>')

    # Table of contents for easy navigation of a long, detailed document.
    if len(sections) > 1:
        parts.append('<nav class="toc"><h3>Contents</h3><ol>')
        for i, s in enumerate(sections, start=1):
            if s.heading:
                parts.append(f'<li><a href="#{_slug(s.heading, i)}">{_e(s.heading)}</a></li>')
        parts.append("</ol></nav>")

    if notes.key_points:
        parts.append('<div class="keypoints"><h3>Key Points at a Glance</h3><ul>')
        parts.extend(f"<li>{_e(p)}</li>" for p in notes.key_points)
        parts.append("</ul></div>")
    parts.append("</section>")

    # One card per sub-topic, studied in depth.
    for i, s in enumerate(sections, start=1):
        anchor = _slug(s.heading, i)
        parts.append(f'<section class="notes-section card" id="{anchor}">')
        if s.heading:
            parts.append(f'<h2 class="sec-h"><span class="sec-n">{i}</span> {_e(s.heading)}</h2>')
        if getattr(s, "overview", ""):
            parts.append(f'<p class="sec-overview">{_e(s.overview)}</p>')

        img = getattr(s, "image", None)
        if img and getattr(img, "url", ""):
            cap = _e(img.caption or s.heading)
            src = _e(img.source or img.url)
            parts.append(
                '<figure class="note-figure">'
                f'<img src="{_e(img.url)}" alt="{cap}" loading="lazy" '
                'referrerpolicy="no-referrer">'
                f'<figcaption>{cap} '
                f'<a href="{src}" target="_blank" rel="noopener">source</a></figcaption>'
                "</figure>"
            )

        if getattr(s, "explanation", ""):
            parts.append(f'<div class="sec-body">{_paragraphs(s.explanation)}</div>')

        # Back-compat: older shape used "points".
        legacy = getattr(s, "points", None) or []
        kp = getattr(s, "key_points", None) or legacy
        if kp:
            parts.append('<h3>Key Points</h3><ul>')
            parts.extend(f"<li>{_e(p)}</li>" for p in kp)
            parts.append("</ul>")

        if getattr(s, "examples", None):
            parts.append('<h3>Examples</h3><ul class="examples">')
            parts.extend(f"<li>{_e(p)}</li>" for p in s.examples)
            parts.append("</ul>")

        if getattr(s, "formulas", None):
            parts.append('<h3>Formulas</h3><ul class="formulas">')
            parts.extend(f"<li><code>{_e(p)}</code></li>" for p in s.formulas)
            parts.append("</ul>")

        parts.append("</section>")

    if notes.glossary:
        parts.append('<section class="glossary-card card"><h2>📖 Glossary</h2>')
        parts.append("<ul class='glossary'>")
        parts.extend(f"<li>{_e(g)}</li>" for g in notes.glossary)
        parts.append("</ul></section>")


def _answer_block(inner: str) -> str:
    # Answers are shown by default (open) but can be collapsed.
    return (
        '<details class="answer" open><summary>Answer</summary>'
        f'<div class="answer-body">{inner}</div></details>'
    )


# Leading option labels the model sometimes bakes into the option text, e.g.
# "A. ", "A) ", "(A) ", "a. ", "1. ", "1) ". We add our own label, so strip these.
_OPTION_LABEL_RE = re.compile(r"^\s*[\(\[]?[A-Za-z0-9][\)\].:]\s+")


def _clean_option(opt: str) -> str:
    text = str(opt or "")
    # Strip once; guards against a single embedded label without eating content.
    return _OPTION_LABEL_RE.sub("", text, count=1).strip()


def _section_open(parts: list[str], key: str, count: int) -> None:
    parts.append(
        f'<section class="qsection card"><h2>{_e(QUESTION_TYPE_LABELS[key])} '
        f'<span class="count">{count}</span></h2><ol class="qlist">'
    )


def _render_true_false(parts, items, include_answers):
    if not items:
        return
    _section_open(parts, "true_false", len(items))
    for it in items:
        parts.append(f'<li><div class="q">{_e(it.statement)}</div>')
        if include_answers:
            body = f"<strong>{'True' if it.answer else 'False'}</strong>"
            if it.explanation:
                body += f"<p>{_e(it.explanation)}</p>"
            parts.append(_answer_block(body))
        else:
            parts.append('<div class="tf-line">True / False</div>')
        parts.append("</li>")
    parts.append("</ol></section>")


def _render_mcq(parts, items, include_answers):
    if not items:
        return
    _section_open(parts, "mcq", len(items))
    for it in items:
        opts = "".join(
            f'<li class="opt">{_e(chr(65 + i))}. {_e(_clean_option(opt))}</li>'
            for i, opt in enumerate(it.options)
        )
        parts.append(
            f'<li><div class="q">{_e(it.question)}</div>'
            f'<ol class="options" type="A">{opts}</ol>'
        )
        if include_answers:
            body = f"<strong>{_e(_clean_option(it.answer))}</strong>"
            if it.explanation:
                body += f"<p>{_e(it.explanation)}</p>"
            parts.append(_answer_block(body))
        parts.append("</li>")
    parts.append("</ol></section>")


def _render_fill(parts, items, include_answers):
    if not items:
        return
    _section_open(parts, "fill_blanks", len(items))
    for it in items:
        parts.append(f'<li><div class="q">{_e(it.question)}</div>')
        if include_answers:
            parts.append(_answer_block(f"<strong>{_e(it.answer)}</strong>"))
        parts.append("</li>")
    parts.append("</ol></section>")


def _render_simple(parts, key, items, include_answers):
    if not items:
        return
    _section_open(parts, key, len(items))
    long_answer = key in ("short", "long")
    for it in items:
        parts.append(f'<li><div class="q">{_e(it.question)}</div>')
        if include_answers:
            parts.append(_answer_block(_e(it.answer)))
        else:
            # Leave writing space on the practice sheet.
            parts.append('<div class="write-space long"></div>' if long_answer
                         else '<div class="write-space"></div>')
        parts.append("</li>")
    parts.append("</ol></section>")


def _render_case(parts, items, include_answers):
    if not items:
        return
    _section_open(parts, "case_based", len(items))
    for it in items:
        parts.append(f'<li><div class="case">{_e(it.case)}</div>')
        if it.questions:
            parts.append('<ol class="subq">')
            for sub in it.questions:
                parts.append(f'<li><div class="q">{_e(sub.question)}</div>')
                if include_answers:
                    parts.append(_answer_block(_e(sub.answer)))
                else:
                    parts.append('<div class="write-space"></div>')
                parts.append("</li>")
            parts.append("</ol>")
        parts.append("</li>")
    parts.append("</ol></section>")


_HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --ink:#1f2937; --muted:#6b7280; --accent:#4f46e5; --line:#e5e7eb;
  --bg:#f8fafc; --card:#ffffff; }}
* {{ box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--ink); background:var(--bg); margin:0; padding:32px 16px; line-height:1.6; }}
.doc-header, section {{ max-width:820px; margin:0 auto 20px; }}
.doc-header h1 {{ margin:0 0 6px; font-size:1.8rem; }}
.meta {{ color:var(--muted); font-size:.85rem; margin:0; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
  padding:22px 26px; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
h2 {{ font-size:1.25rem; margin:0 0 14px; color:var(--accent);
  display:flex; align-items:center; gap:10px; }}
h3 {{ font-size:1.02rem; margin:18px 0 6px; }}
.count {{ font-size:.75rem; background:var(--accent); color:#fff; border-radius:999px;
  padding:2px 10px; font-weight:600; }}
.summary {{ background:#eef2ff; border-left:4px solid var(--accent); padding:12px 14px;
  border-radius:8px; }}
ul, ol {{ margin:8px 0; padding-left:22px; }}
li {{ margin:6px 0; }}
.qlist > li {{ margin:16px 0; padding-bottom:14px; border-bottom:1px dashed var(--line); }}
.qlist > li:last-child {{ border-bottom:none; }}
.q {{ font-weight:600; }}
.options {{ margin:8px 0; }}
.opt {{ font-weight:400; }}
.tf-line {{ color:var(--muted); font-size:.9rem; margin-top:4px; }}
.write-space {{ border-bottom:1px solid var(--line); height:1.6em; margin-top:8px; }}
.write-space.long {{ height:4.8em;
  background-image:repeating-linear-gradient(transparent,transparent 1.5em,var(--line) 1.5em,var(--line) calc(1.5em + 1px)); }}
.case {{ background:#fff7ed; border-left:4px solid #f59e0b; padding:12px 14px;
  border-radius:8px; font-style:italic; }}
.subq {{ margin-top:10px; }}
.answer {{ margin-top:8px; }}
.answer summary {{ cursor:pointer; color:var(--accent); font-weight:600; font-size:.9rem;
  list-style:none; display:inline-block; padding:4px 10px; background:#eef2ff;
  border-radius:8px; }}
.answer summary::-webkit-details-marker {{ display:none; }}
.answer-body {{ margin-top:8px; background:#ecfdf5; border-left:4px solid #10b981;
  padding:10px 14px; border-radius:8px; }}
.glossary li {{ font-weight:400; }}
/* Detailed notes */
.toc {{ background:#f8fafc; border:1px solid var(--line); border-radius:10px;
  padding:12px 16px; margin-top:14px; }}
.toc h3 {{ margin:0 0 6px; font-size:.95rem; }}
.toc ol {{ margin:0; padding-left:20px; }}
.toc a {{ color:var(--accent); text-decoration:none; }}
.toc a:hover {{ text-decoration:underline; }}
.keypoints {{ margin-top:14px; }}
.notes-section {{ scroll-margin-top:16px; }}
.sec-h {{ align-items:baseline; }}
.sec-n {{ flex:none; background:var(--accent); color:#fff; border-radius:8px;
  min-width:26px; height:26px; display:inline-flex; align-items:center;
  justify-content:center; font-size:.85rem; font-weight:700; }}
.sec-overview {{ color:#374151; font-weight:500; }}
.sec-body p {{ margin:0 0 10px; }}
.note-figure {{ margin:12px 0; text-align:center; }}
.note-figure img {{ max-width:100%; height:auto; border:1px solid var(--line);
  border-radius:10px; background:#fff; }}
.note-figure figcaption {{ color:var(--muted); font-size:.82rem; margin-top:6px; }}
.note-figure figcaption a {{ color:var(--accent); }}
.examples li {{ font-weight:400; }}
.formulas li {{ font-weight:400; }}
.formulas code {{ background:#f1f5f9; padding:2px 6px; border-radius:6px; }}
.refs-note {{ color:var(--muted); font-size:.88rem; margin:0 0 8px; }}
.refs-list li {{ font-weight:400; word-break:break-all; }}
.refs-list a {{ color:var(--accent); }}
@media print {{
  body {{ background:#fff; padding:0; }}
  .card {{ box-shadow:none; border:1px solid #ccc; break-inside:avoid; }}
  .answer summary {{ display:none; }}
  .answer-body {{ display:block !important; }}
}}
</style></head><body>
"""

_FOOTER = (
    '<footer style="max-width:820px;margin:24px auto 0;text-align:center;'
    'color:#9ca3af;font-size:.8rem;">Generated with the Study Notes &amp; '
    "Question Generator — for learning and revision.</footer></body></html>"
)
