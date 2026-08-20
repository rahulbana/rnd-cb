"""Render a StudyMaterial into a self-contained, printable HTML document."""
from __future__ import annotations

import html
from datetime import datetime

from .schemas import QUESTION_TYPE_LABELS, StudyMaterial


def _e(value) -> str:
    return html.escape(str(value if value is not None else ""))


def render_html(material: StudyMaterial, source_filename: str, grade_level: str = "") -> str:
    notes = material.notes
    q = material.questions
    title = notes.title or "Study Notes & Questions"
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
    q_index = 0
    q_index = _render_true_false(parts, q.true_false, q_index)
    q_index = _render_mcq(parts, q.mcq, q_index)
    q_index = _render_fill(parts, q.fill_blanks, q_index)
    q_index = _render_simple(parts, "very_short", q.very_short, q_index)
    q_index = _render_simple(parts, "short", q.short, q_index)
    q_index = _render_simple(parts, "long", q.long, q_index)
    q_index = _render_case(parts, q.case_based, q_index)

    parts.append(_FOOTER)
    return "".join(parts)


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


def _render_true_false(parts, items, idx):
    if not items:
        return idx
    _section_open(parts, "true_false", len(items))
    for it in items:
        idx += 1
        ans = "True" if it.answer else "False"
        body = f"<strong>{_e(ans)}</strong>"
        if it.explanation:
            body += f"<p>{_e(it.explanation)}</p>"
        parts.append(
            f'<li><div class="q">{_e(it.statement)}</div>{_answer_block(body)}</li>'
        )
    parts.append("</ol></section>")
    return idx


def _render_mcq(parts, items, idx):
    if not items:
        return idx
    _section_open(parts, "mcq", len(items))
    for it in items:
        idx += 1
        opts = "".join(
            f'<li class="opt">{_e(chr(65 + i))}. {_e(opt)}</li>'
            for i, opt in enumerate(it.options)
        )
        body = f"<strong>{_e(it.answer)}</strong>"
        if it.explanation:
            body += f"<p>{_e(it.explanation)}</p>"
        parts.append(
            f'<li><div class="q">{_e(it.question)}</div>'
            f'<ol class="options" type="A">{opts}</ol>{_answer_block(body)}</li>'
        )
    parts.append("</ol></section>")
    return idx


def _render_fill(parts, items, idx):
    if not items:
        return idx
    _section_open(parts, "fill_blanks", len(items))
    for it in items:
        idx += 1
        body = f"<strong>{_e(it.answer)}</strong>"
        parts.append(
            f'<li><div class="q">{_e(it.question)}</div>{_answer_block(body)}</li>'
        )
    parts.append("</ol></section>")
    return idx


def _render_simple(parts, key, items, idx):
    if not items:
        return idx
    _section_open(parts, key, len(items))
    for it in items:
        idx += 1
        body = _e(it.answer)
        parts.append(
            f'<li><div class="q">{_e(it.question)}</div>{_answer_block(body)}</li>'
        )
    parts.append("</ol></section>")
    return idx


def _render_case(parts, items, idx):
    if not items:
        return idx
    _section_open(parts, "case_based", len(items))
    for it in items:
        idx += 1
        parts.append(f'<li><div class="case">{_e(it.case)}</div>')
        if it.questions:
            parts.append('<ol class="subq">')
            for sub in it.questions:
                inner = _answer_block(_e(sub.answer))
                parts.append(f'<li><div class="q">{_e(sub.question)}</div>{inner}</li>')
            parts.append("</ol>")
        parts.append("</li>")
    parts.append("</ol></section>")
    return idx


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
  .answer[open] summary {{ display:none; }}
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
