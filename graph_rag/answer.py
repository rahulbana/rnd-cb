"""Generate a final answer from the graph-derived context."""

from . import config

_SYSTEM_PROMPT = """\
You are a helpful assistant answering questions using ONLY the knowledge-graph
facts provided. The facts are relationships extracted from a document set.

Rules:
- Base your answer strictly on the provided facts.
- If the facts do not contain the answer, say you don't have enough
  information in the graph rather than guessing.
- Be concise and explain the reasoning by referring to the relationships.
"""


def generate_answer(question: str, context: str, client=None) -> str:
    """Answer the question given a context block of graph facts."""
    client = client or config.get_client()

    if not context.strip():
        return (
            "I couldn't find any related entities in the knowledge graph for "
            "this question. Try rephrasing, or rebuild the graph with more data."
        )

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Knowledge-graph facts:\n{context}\n\n"
                    f"Question: {question}"
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()
