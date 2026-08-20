"""Render a StudyMaterial into self-contained, printable HTML documents.

Three variants are produced:
- notes only
- questions with answers
- questions only (no answers) — a clean practice/exam sheet
"""
from __future__ import annotations

import html
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
        parts.append('<section class="notes card"><h2>📘 Study Notes</h2>')
        if notes.summary:
            parts.append(f'<p class="summary">{_e(notes.summary)}</p>')
        if notes.key_points:
            parts.append("<h3>Key Points</h3><ul>")
            parts.extend(f"<li>{_e(p)}</li>" for p in notes.key_points)
            parts.append("</ul>")
        for section in notes.sections:
            if section.heading:
                parts.append(f"<h3>{_e(section.heading)}</h3>")
            if section.points:
                parts.append("<ul>")
                parts.extend(f"<li>{_e(p)}</li>" for p in section.points)
                parts.append("</ul>")
        if notes.glossary:
            parts.append("<h3>Glossary</h3><ul class='glossary'>")
            parts.extend(f"<li>{_e(g)}</li>" for g in notes.glossary)
            parts.append("</ul>")
        parts.append("</section>")

    # ---- Questions --------------------------------------------------------
    if include_questions:
        _render_true_false(parts, q.true_false, include_answers)
        _render_mcq(parts, q.mcq, include_answers)
        _render_fill(parts, q.fill_blanks, include_answers)
        _render_simple(parts, "very_short", q.very_short, include_answers)
        _render_simple(parts, "short", q.short, include_answers)
        _render_simple(parts, "long", q.long, include_answers)
        _render_case(parts, q.case_based, include_answers)

    parts.append(_FOOTER)
    return "".join(parts)


def render_variants(
    material: StudyMaterial, source_filename: str, grade_level: str = ""
) -> dict[str, str]:
    """Produce the three downloadable HTML documents."""
    return {
        "notes": render_html(
            material, source_filename, grade_level,
            include_notes=True, include_questions=False, doc_label="Notes",
        ),
        "questions_with_answers": render_html(
            material, source_filename, grade_level,
            include_notes=False, include_questions=True, include_answers=True,
            doc_label="Questions & Answers",
        ),
        "questions_only": render_html(
            material, source_filename, grade_level,
            include_notes=False, include_questions=True, include_answers=False,
            doc_label="Question Paper",
        ),
    }


def _answer_block(inner: str) -> str:
    # Answers are collapsible so the sheet can be used as a quiz first.
    return (
        '<details class="answer"><summary>Show answer</summary>'
        f'<div class="answer-body">{inner}</div></details>'
    )


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
            f'<li class="opt">{_e(chr(65 + i))}. {_e(opt)}</li>'
            for i, opt in enumerate(it.options)
        )
        parts.append(
            f'<li><div class="q">{_e(it.question)}</div>'
            f'<ol class="options" type="A">{opts}</ol>'
        )
        if include_answers:
            body = f"<strong>{_e(it.answer)}</strong>"
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
