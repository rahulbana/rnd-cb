"""Regression test: generation must not crash when the model omits fields.

Reproduces the production failure where the model returned JSON without a
'summary' key and Pydantic validation 500'd, losing the whole generation.
"""
from app.services.llm import _finalize, _loads


def main() -> None:
    # The exact failure shape: no 'summary', no 'seo_description'.
    data = {
        "title": "Is a College Degree Worth It?",
        "body": "## Intro\nThe value of a degree is debated across many angles, "
        "and this body is long enough to derive a readable summary from.",
        "keywords": ["college", "roi"],
        "sources": [{"title": "Example", "type": "reference"}],
    }
    c = _finalize(data)
    assert c.title == "Is a College Degree Worth It?"
    assert c.summary.strip(), "summary should be backfilled from the body"
    assert "\n" not in c.summary, "summary should be a clean single line"
    assert c.seo_description.strip(), "seo_description should be backfilled"
    assert len(c.sources) == 1

    # Totally minimal payload still validates with defaults.
    c2 = _finalize({"body": "Hello body."})
    assert c2.title == "Untitled"
    assert c2.summary == "Hello body."

    # Tolerates code-fenced / prose-wrapped JSON.
    assert _loads('```json\n{"title":"T"}\n```')["title"] == "T"
    assert _loads('Here you go: {"title":"Z"} thanks')["title"] == "Z"

    print("LLM FINALIZE TEST PASSED ✅  (missing fields backfilled, no crash)")


if __name__ == "__main__":
    main()
