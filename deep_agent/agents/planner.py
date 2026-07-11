"""Planner Agent — decomposes a topic into a structured research plan."""
from __future__ import annotations

from deep_agent.agents.base import BaseAgent
from deep_agent.models.schemas import ResearchPlan
from deep_agent.state import ResearchState

_SYSTEM = (
    "You are an expert research planner. Given a topic, produce a focused "
    "research plan that breaks it into 3-5 distinct sub-topics. For each "
    "sub-topic provide a short rationale and 2-3 specific, high-signal web "
    "search queries. Prefer queries that surface primary sources, data and "
    "recent developments. Avoid redundant or overly broad queries."
)

_USER = (
    "Topic: {topic}\n\n"
    "Produce a research plan with a clear objective describing what a "
    "complete, well-cited report on this topic must cover."
)


class PlannerAgent(BaseAgent):
    """Turns a raw topic into a :class:`ResearchPlan`."""

    name = "planner"

    def run(self, state: ResearchState) -> dict:
        topic = state["topic"]
        self.logger.info("Planning research for topic: %s", topic)

        plan = self._structured(
            ResearchPlan,
            system=_SYSTEM,
            user=_USER.format(topic=topic),
        )
        # Ensure the topic is preserved even if the model omits/renames it.
        plan.topic = topic

        queries = plan.all_queries()
        self.logger.info(
            "Plan ready: %d sub-topics, %d initial queries",
            len(plan.sub_topics),
            len(queries),
        )
        return {
            "plan": plan,
            "pending_queries": queries,
            "iteration": 0,
        }
