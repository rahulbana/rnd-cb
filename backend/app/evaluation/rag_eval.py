"""End-to-end RAG evaluation: run a golden Q&A set through the pipeline.

Executes each golden question through the chat service to capture the answer and
its retrieved contexts, then scores the batch with the configured EvalHarness
into a pass/fail Scorecard.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.interfaces import EvalHarness
from app.domain.models import EvalCase, Scorecard
from app.services.chat_service import ChatService

# (question, ground_truth) -- a small default golden set. In production this is
# curated per corpus and stored/versioned; here it seeds the eval endpoint.
GoldenItem = tuple[str, str]

DEFAULT_GOLDEN: list[GoldenItem] = [
    ("what is the powerhouse of the cell", "mitochondria powerhouse cell"),
    ("how much did revenue grow", "revenue grew twenty percent"),
]


async def build_cases(
    chat: ChatService, golden: Sequence[GoldenItem], *, namespace: str
) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for question, ground_truth in golden:
        result = await chat.answer(question, namespace=namespace)
        cases.append(
            EvalCase(
                question=question,
                answer=result.answer,
                contexts=result.contexts,
                ground_truth=ground_truth,
            )
        )
    return cases


async def run_eval(
    chat: ChatService,
    harness: EvalHarness,
    golden: Sequence[GoldenItem],
    *,
    namespace: str,
    threshold: float,
) -> Scorecard:
    cases = await build_cases(chat, golden, namespace=namespace)
    return await harness.evaluate(cases, threshold=threshold)
