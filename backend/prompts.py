"""Prompt templates for the AI Code Explainer.

Each action maps to an instruction that is combined with a shared system
persona. Keeping the prompts here (rather than inline) makes them easy to
tune without touching the request-handling code.
"""

from __future__ import annotations

# Shared persona used for every request. It keeps the model focused on
# explaining code clearly and honestly.
SYSTEM_PROMPT = (
    "You are AI Code Explainer, a patient senior software engineer who is "
    "great at teaching. You explain source code in plain, simple language. "
    "You are accurate: if something is ambiguous or you are unsure, you say "
    "so instead of guessing. You never invent behaviour that is not in the "
    "code. Use Markdown in your answers (headings, bullet lists, and fenced "
    "code blocks with a language tag) so the response is easy to read."
)

# Audience presets change the tone/depth of the explanation.
AUDIENCE_GUIDANCE = {
    "beginner": (
        "Write for a beginner who is new to programming. Avoid jargon, and "
        "when you must use a technical term, define it in one short sentence. "
        "Use everyday analogies where they help."
    ),
    "intermediate": (
        "Write for an intermediate developer. You can use common technical "
        "terms without defining every one, but keep the explanation clear."
    ),
    "expert": (
        "Write for an experienced engineer. Be concise and precise, focus on "
        "non-obvious details, edge cases, and design trade-offs."
    ),
}

# Per-action instructions. The user's code is appended after this.
ACTION_PROMPTS = {
    "explain": (
        "Explain what this code does, step by step. Start with a one-sentence "
        "summary of its overall purpose, then walk through the important parts "
        "in order. Mention inputs, outputs, and any side effects."
    ),
    "explain_function": (
        "Explain the function(s) in this code. For each function describe: its "
        "purpose, its parameters (name, meaning, expected type), what it "
        "returns, and any side effects or edge cases. If there are several "
        "functions, use a short section for each."
    ),
    "explain_variables": (
        "Explain the variables in this code. For each meaningful variable give "
        "its name, its inferred type, and what role it plays. Present the "
        "result as a Markdown table with columns: Variable, Type, Purpose. "
        "Skip trivial loop counters unless they matter."
    ),
    "find_bugs": (
        "Review this code for potential bugs, logic errors, edge cases, and "
        "security or performance issues. For each finding give: the problem, "
        "why it is a problem, and a concrete suggested fix. If you find no "
        "real issues, say so clearly. Order findings from most to least "
        "severe. Do not flag style-only nitpicks as bugs."
    ),
    "generate_docs": (
        "Generate clear documentation for this code. Produce a Markdown "
        "document with: an Overview, a Usage example, and a reference section "
        "describing each public function/class (parameters, return value, "
        "exceptions raised). Keep it practical."
    ),
    "add_comments": (
        "Add helpful comments to this code. Return the SAME code, unchanged in "
        "behaviour, but with clear comments added: a docstring/summary comment "
        "where appropriate and inline comments explaining non-obvious lines. "
        "Do not over-comment trivial lines. Return only one fenced code block "
        "containing the fully commented code, using the correct language tag."
    ),
    "complexity": (
        "Analyse the complexity of this code. Give the time complexity and "
        "space complexity in Big-O notation, and explain in plain language WHY "
        "each holds (what drives the growth). If relevant, mention the "
        "best/average/worst cases and suggest whether a more efficient "
        "approach exists."
    ),
}

# Human-friendly labels, also exposed to the frontend via /api/actions.
ACTION_LABELS = {
    "explain": "Explain Code",
    "explain_function": "Explain Function",
    "explain_variables": "Explain Variables",
    "find_bugs": "Find Potential Bugs",
    "generate_docs": "Generate Documentation",
    "add_comments": "Add Comments",
    "complexity": "Complexity Analysis",
}


def build_user_prompt(action: str, code: str, language: str | None) -> str:
    """Assemble the user-facing prompt for a given action and snippet."""
    instruction = ACTION_PROMPTS[action]
    lang_note = (
        f"The code is written in {language}.\n\n"
        if language and language.lower() != "unknown"
        else ""
    )
    return (
        f"{instruction}\n\n"
        f"{lang_note}"
        "Here is the code:\n\n"
        f"```{language or ''}\n{code}\n```"
    )


def build_system_prompt(audience: str | None) -> str:
    """Combine the base persona with optional audience guidance."""
    guidance = AUDIENCE_GUIDANCE.get((audience or "").lower())
    if guidance:
        return f"{SYSTEM_PROMPT}\n\n{guidance}"
    return SYSTEM_PROMPT
