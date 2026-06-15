"""Quiz agent: researches board materials, then generates a quiz."""
from __future__ import annotations

from app.agents import llm
from app.agents.nodes.base import timed_node
from app.agents.prompts import quiz_prompt
from app.agents.state import PlanState
from app.core.logging import get_logger
from app.schemas import QuizOutput
from app.services import research

log = get_logger("agents.quiz")


@timed_node("quiz")
async def quiz_node(state: PlanState) -> PlanState:
    req = state["request"]

    # Ground the quiz in real board materials when web research is available.
    references = await research.research_quiz_context(req.grade, req.subject, req.topic)
    if references:
        log.info("quiz grounded in %d chars of web research", len(references))

    system, user = quiz_prompt(req, state["outline"], references)
    quiz = await llm.run_structured(system, user, QuizOutput, temperature=0.6)
    return {"quiz": quiz}
