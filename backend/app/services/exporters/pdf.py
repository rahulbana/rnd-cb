"""Generate a downloadable PDF from a StudyPlan using ReportLab."""
from __future__ import annotations

import io
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.core.exceptions import ExportError
from app.schemas import StudyPlan

# ReportLab's built-in fonts can't render emoji; strip them so nothing breaks.
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U0000FE0F\U00002190-\U000021FF\U00002B00-\U00002BFF]+",
    flags=re.UNICODE,
)

_PRIMARY = colors.HexColor("#4f46e5")
_ACCENT = colors.HexColor("#06b6d4")
_MUTED = colors.HexColor("#64748b")
_ANSWER = "#16a34a"


def _clean(text: str) -> str:
    """Remove emoji and escape XML special chars for ReportLab paragraphs."""
    text = _EMOJI_RE.sub("", str(text)).strip()
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PlanTitle", parent=base["Title"], fontSize=22, textColor=_PRIMARY,
            spaceAfter=4,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["Normal"], fontSize=9, textColor=_MUTED,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontSize=14, textColor=_PRIMARY,
            spaceBefore=12, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"], fontSize=11.5,
            textColor=colors.HexColor("#0f172a"), spaceBefore=6, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontSize=10, leading=14, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"], fontSize=9, textColor=_ACCENT,
            spaceAfter=4,
        ),
    }


def _bullets(items: list[str], style: ParagraphStyle) -> ListFlowable:
    """Bullet list of render-ready markup strings (callers must pre-clean text)."""
    return ListFlowable(
        [ListItem(Paragraph(it, style), leftIndent=10) for it in items],
        bulletType="bullet",
        bulletColor=_PRIMARY,
        start="•",
        leftIndent=12,
    )


def _text_bullets(items: list[str], style: ParagraphStyle) -> ListFlowable:
    """Bullet list of plain text — escapes each item before rendering."""
    return _bullets([_clean(it) for it in items], style)


def _qa_rows(items) -> list[str]:
    return [
        f"{_clean(it.question)}<br/><font color='{_ANSWER}'><b>Answer:</b> "
        f"{_clean(it.answer)}</font>"
        for it in items
    ]


def _build_story(plan: StudyPlan, s: dict[str, ParagraphStyle]) -> list:
    req = plan.request
    story: list = []

    story.append(Paragraph(_clean(plan.outline.title) or "Study Plan", s["title"]))
    story.append(
        Paragraph(
            f"Class {req.grade} &nbsp;·&nbsp; {_clean(req.subject)} &nbsp;·&nbsp; "
            f"{_clean(req.topic)} &nbsp;·&nbsp; {req.duration_weeks} week(s) "
            f"&nbsp;·&nbsp; ~{req.hours_per_week} hrs/week &nbsp;·&nbsp; "
            f"level: {_clean(req.level)}",
            s["meta"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(_clean(plan.outline.overview), s["body"]))

    if plan.outline.learning_goals:
        story.append(Paragraph("Learning Goals", s["h2"]))
        story.append(_text_bullets(plan.outline.learning_goals, s["body"]))

    if plan.outline.prerequisites:
        story.append(Paragraph("Prerequisites", s["h2"]))
        story.append(_text_bullets(plan.outline.prerequisites, s["body"]))

    if plan.curriculum.modules:
        story.append(Paragraph("Curriculum", s["h2"]))
        for i, m in enumerate(plan.curriculum.modules, 1):
            story.append(Paragraph(f"Module {i}: {_clean(m.title)}", s["h3"]))
            if m.objectives:
                story.append(_text_bullets(m.objectives, s["body"]))
            if m.subtopics:
                story.append(
                    Paragraph("Subtopics: " + _clean(", ".join(m.subtopics)), s["small"])
                )

    if plan.schedule.weeks:
        story.append(Paragraph("Schedule", s["h2"]))
        for w in plan.schedule.weeks:
            story.append(Paragraph(f"Week {w.week_number} — {_clean(w.focus)}", s["h3"]))
            rows = [
                f"<b>{_clean(se.day)}</b> ({se.duration_minutes} min): {_clean(se.activity)}"
                for se in w.sessions
            ]
            if rows:
                story.append(_bullets(rows, s["body"]))

    if plan.resources.resources:
        story.append(Paragraph("Resources", s["h2"]))
        rows = []
        for r in plan.resources.resources:
            line = f"<b>[{_clean(r.type)}]</b> {_clean(r.title)} — {_clean(r.description)}"
            if r.link:
                link = _clean(r.link)
                line += f' (<link href="{link}"><font color="#4f46e5">{link}</font></link>)'
            rows.append(line)
        story.append(_bullets(rows, s["body"]))

    if plan.assessment.assessments:
        story.append(Paragraph("Assessments &amp; Checkpoints", s["h2"]))
        for a in plan.assessment.assessments:
            story.append(Paragraph(f"{_clean(a.title)} ({_clean(a.type)})", s["h3"]))
            story.append(Paragraph(_clean(a.description), s["body"]))
            if a.sample_questions:
                story.append(_text_bullets(a.sample_questions, s["body"]))

    _append_quiz(plan, s, story)

    if plan.study_tips:
        story.append(Paragraph("Study Tips", s["h2"]))
        story.append(_text_bullets(plan.study_tips, s["body"]))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    story.append(Paragraph("Generated by the Multi-Agent Study Planner.", s["meta"]))
    return story


def _append_quiz(plan: StudyPlan, s: dict[str, ParagraphStyle], story: list) -> None:
    q = plan.quiz
    if not q.total():
        return

    story.append(Paragraph("Quiz", s["h2"]))

    if q.short_questions:
        story.append(Paragraph("Short Questions", s["h3"]))
        story.append(_bullets(_qa_rows(q.short_questions), s["body"]))

    if q.mcqs:
        story.append(Paragraph("Multiple Choice (single answer)", s["h3"]))
        rows = []
        for it in q.mcqs:
            opts = "  ".join(
                f"{chr(65 + j)}. {_clean(o)}" for j, o in enumerate(it.options)
            )
            rows.append(
                f"{_clean(it.question)}<br/>{opts}<br/>"
                f"<font color='{_ANSWER}'><b>Answer:</b> {_clean(it.answer)}</font>"
            )
        story.append(_bullets(rows, s["body"]))

    if q.multi_select_mcqs:
        story.append(Paragraph("Multiple Select (MMCQ)", s["h3"]))
        rows = []
        for it in q.multi_select_mcqs:
            opts = "  ".join(
                f"{chr(65 + j)}. {_clean(o)}" for j, o in enumerate(it.options)
            )
            rows.append(
                f"{_clean(it.question)}<br/>{opts}<br/>"
                f"<font color='{_ANSWER}'><b>Answers:</b> "
                f"{_clean(', '.join(it.answers))}</font>"
            )
        story.append(_bullets(rows, s["body"]))

    if q.fill_in_the_blanks:
        story.append(Paragraph("Fill in the Blanks", s["h3"]))
        story.append(_bullets(_qa_rows(q.fill_in_the_blanks), s["body"]))

    if q.true_false:
        story.append(Paragraph("True / False", s["h3"]))
        rows = [
            f"{_clean(it.statement)}<br/><font color='{_ANSWER}'><b>Answer:</b> "
            f"{'True' if it.answer else 'False'}</font>"
            for it in q.true_false
        ]
        story.append(_bullets(rows, s["body"]))

    if q.case_studies:
        story.append(Paragraph("Case-Based Questions", s["h3"]))
        for i, case in enumerate(q.case_studies, 1):
            story.append(
                Paragraph(f"<b>Case {i}.</b> {_clean(case.scenario)}", s["body"])
            )
            if case.questions:
                story.append(_bullets(_qa_rows(case.questions), s["body"]))

    if q.long_questions:
        story.append(Paragraph("Long Answer Questions", s["h3"]))
        story.append(_bullets(_qa_rows(q.long_questions), s["body"]))


def build_pdf(plan: StudyPlan) -> bytes:
    """Render the study plan into PDF bytes."""
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=_clean(plan.outline.title) or "Study Plan",
    )
    try:
        doc.build(_build_story(plan, s))
    except Exception as exc:  # noqa: BLE001
        raise ExportError(f"Failed to render PDF: {exc}") from exc
    return buf.getvalue()
