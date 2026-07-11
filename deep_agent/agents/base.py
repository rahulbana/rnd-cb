"""Base class shared by every agent node.

An agent is a thin, testable unit that exposes a single ``run(state)``
method used as a LangGraph node.  Shared concerns — the LLM handle, a
namespaced logger and structured-output helpers — live here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from deep_agent.llm import get_chat_model
from deep_agent.state import ResearchState
from deep_agent.utils.logging import get_logger

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """Common functionality for all agents."""

    #: Node name used in the LangGraph graph.
    name: str = "agent"

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self.llm = llm or get_chat_model()
        self.logger = get_logger(f"agents.{self.name}")

    @abstractmethod
    def run(self, state: ResearchState) -> dict:
        """Execute the agent and return a partial state update."""

    # -- Helpers ---------------------------------------------------------
    def _structured(
        self, schema: type[T], system: str, user: str
    ) -> T:
        """Invoke the LLM and coerce the reply into ``schema``."""

        model = self.llm.with_structured_output(schema)
        return model.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )

    def _complete(self, system: str, user: str) -> str:
        """Invoke the LLM for a plain-text completion."""

        reply = self.llm.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        return reply.content if isinstance(reply.content, str) else str(reply.content)
