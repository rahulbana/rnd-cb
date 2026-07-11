"""Base class shared by every agent node.

An agent is a thin, testable unit that exposes a single ``run(state)``
method used as a LangGraph node.  Shared concerns — a lazily-built,
per-role LLM handle, a namespaced logger, structured-output helpers and
token-usage logging — live here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from deep_agent.config import LLMTier
from deep_agent.llm import get_chat_model
from deep_agent.state import ResearchState
from deep_agent.utils.logging import get_logger

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """Common functionality for all agents."""

    #: Node name used in the LangGraph graph.
    name: str = "agent"
    #: Model tier this agent requests (override per agent for cost control).
    llm_tier: LLMTier = LLMTier.SMART

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        # Built lazily so LLM-free agents (search/collector/scraper) never
        # construct a model or require an API key.
        self._llm = llm
        self.logger = get_logger(f"agents.{self.name}")

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_chat_model(role=self.name, tier=self.llm_tier)
        return self._llm

    @abstractmethod
    def run(self, state: ResearchState) -> dict:
        """Execute the agent and return a partial state update."""

    # -- Helpers ---------------------------------------------------------
    def _structured(self, schema: type[T], system: str, user: str) -> T:
        """Invoke the LLM and coerce the reply into ``schema``.

        Uses ``include_raw`` so token usage can be logged even for
        structured-output calls.
        """

        model = self.llm.with_structured_output(schema, include_raw=True)
        result = model.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        self._log_usage(result.get("raw"))
        return result["parsed"]

    def _complete(self, system: str, user: str) -> str:
        """Invoke the LLM for a plain-text completion."""

        reply = self.llm.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        self._log_usage(reply)
        return reply.content if isinstance(reply.content, str) else str(reply.content)

    def _log_usage(self, message) -> None:
        """Log token usage from a response message, if present."""

        usage = getattr(message, "usage_metadata", None)
        if usage:
            self.logger.info(
                "LLM tokens — input=%s output=%s total=%s",
                usage.get("input_tokens"),
                usage.get("output_tokens"),
                usage.get("total_tokens"),
            )
