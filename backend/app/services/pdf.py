"""Document generation: structured resume -> HTML template -> PDF.

We render a Jinja2 HTML template (chosen by style) and convert it to a PDF with
WeasyPrint. The same rendered HTML is also exposed to the frontend for a live
preview, so what the user sees matches the downloaded document.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..schemas import Resume, ResumeStyle

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_html(resume: Resume, style: ResumeStyle) -> str:
    """Render the resume to a standalone HTML document."""

    template = _env.get_template("resume.html")
    return template.render(r=resume, style=style.value)


def render_pdf(resume: Resume, style: ResumeStyle) -> bytes:
    """Render the resume to PDF bytes.

    Raises RuntimeError with an actionable message if WeasyPrint's native
    dependencies are missing.
    """

    html = render_html(resume, style)
    try:
        from weasyprint import HTML
    except OSError as exc:  # native libs (pango/cairo) missing
        raise RuntimeError(
            "PDF engine unavailable: WeasyPrint's system libraries "
            "(libpango, libcairo, libgdk-pixbuf) are not installed. "
            "See setup.sh for installation instructions."
        ) from exc

    return HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf()
