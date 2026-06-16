"""The base review agent that every category agent is built from."""

from __future__ import annotations

from ..collector import CodeFile
from ..llm import LLMClient, LLMError, number_lines
from ..models import CategoryResult, Finding

_SYSTEM_TEMPLATE = """\
You are a meticulous senior software engineer performing a focused code review.
Your single responsibility is reviewing for: {category}.

{description}

Review checklist for this category:
{checklist}

Rules:
- Only report issues that fall under "{category}". Ignore unrelated problems;
  other specialised reviewers cover those.
- Be concrete and actionable. Reference the line number when you can.
- Do not invent issues. If the code is clean for this category, return an
  empty findings list and say so in the summary.
- Calibrate severity honestly: critical/high for real correctness or security
  risks, low/info for style or minor nits.
- The code is for the {language} programming language.
"""

_USER_TEMPLATE = """\
Review the following {language} file: {path}{truncation_note}

```{language}
{code}
```
"""


class ReviewAgent:
    """Reviews a single file for one category via the LLM."""

    def __init__(
        self,
        key: str,
        category: str,
        description: str,
        checklist: list[str],
    ):
        self.key = key
        self.category = category
        self.description = description
        self.checklist = checklist

    def _system_prompt(self, language: str) -> str:
        checklist = "\n".join(f"- {item}" for item in self.checklist)
        return _SYSTEM_TEMPLATE.format(
            category=self.category,
            description=self.description,
            checklist=checklist,
            language=language,
        )

    def review_file(
        self, client: LLMClient, code_file: CodeFile, language: str
    ) -> CategoryResult:
        """Run the review for one file, returning findings or an error."""
        truncation_note = (
            " (NOTE: file was truncated; review only what is shown)"
            if code_file.truncated
            else ""
        )
        user_prompt = _USER_TEMPLATE.format(
            language=language,
            path=code_file.relpath,
            truncation_note=truncation_note,
            code=number_lines(code_file.content),
        )

        try:
            data = client.review(self._system_prompt(language), user_prompt)
        except LLMError as exc:
            return CategoryResult(
                category=self.category,
                file_path=code_file.relpath,
                error=str(exc),
            )

        findings = [
            Finding.from_dict(item) for item in data.get("findings", []) or []
        ]
        return CategoryResult(
            category=self.category,
            file_path=code_file.relpath,
            findings=findings,
            summary=str(data.get("summary", "")).strip(),
        )
