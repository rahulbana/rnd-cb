"""The multi-agent CrewAI crew that researches and verifies reviews."""

import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

from .models import ReviewReport
from .tools import DeepSearchTool


def _build_llm() -> LLM:
    """OpenAI LLM shared by every agent."""
    model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
    return LLM(model=model, temperature=0.2)


@CrewBase
class ReviewAuthenticityCrew:
    """A crew of three agents: deep researcher -> sentiment analyst -> verifier."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self) -> None:
        self.llm = _build_llm()
        self.deep_search = DeepSearchTool()

    # ----- Agents -----
    @agent
    def deep_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["deep_researcher"],
            tools=[self.deep_search],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def sentiment_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["sentiment_analyst"],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def verification_specialist(self) -> Agent:
        # The verifier ALSO gets the search tool so it can independently re-check claims.
        return Agent(
            config=self.agents_config["verification_specialist"],
            tools=[self.deep_search],
            llm=self.llm,
            verbose=True,
        )

    # ----- Tasks -----
    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @task
    def analysis_task(self) -> Task:
        return Task(config=self.tasks_config["analysis_task"])

    @task
    def verification_task(self) -> Task:
        # Final task emits the structured, validated report.
        return Task(
            config=self.tasks_config["verification_task"],
            output_pydantic=ReviewReport,
        )

    # ----- Crew -----
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
