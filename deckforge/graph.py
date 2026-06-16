"""LangGraph orchestration of the DeckForge multi-agent pipeline.

The graph is a linear state machine:

    research -> outline -> content -> design -> render

Each node mutates a shared :class:`PipelineState`. The flow is intentionally
explicit and inspectable; swap in branching/loops here without touching the
agents themselves.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .agents import ContentAgent, DesignAgent, OutlineAgent, ResearchAgent
from .config import Settings, get_settings
from .deck.builder import render_deck
from .llm import LLMClient
from .models import Deck, Outline, ResearchFinding


class PipelineState(TypedDict, total=False):
    # Inputs
    topic: str
    source: str
    theme: str
    target_slides: int
    # Intermediate artifacts
    findings: List[ResearchFinding]
    outline: Outline
    deck: Deck
    # Output
    output_path: str


# A status callback lets the CLI render progress without the graph knowing
# anything about the terminal.
ProgressFn = Callable[[str], None]


def build_pipeline(
    settings: Optional[Settings] = None,
    progress: Optional[ProgressFn] = None,
):
    """Compile and return the runnable LangGraph pipeline."""
    settings = settings or get_settings()
    llm = LLMClient(settings)
    say = progress or (lambda _msg: None)

    research_agent = ResearchAgent(settings, llm)
    outline_agent = OutlineAgent(llm)
    content_agent = ContentAgent(llm)
    design_agent = DesignAgent(llm)

    def research_node(state: PipelineState) -> PipelineState:
        if settings.research_enabled:
            say("Researching the web for supporting facts…")
        else:
            say("Skipping web research (no TAVILY_API_KEY).")
        findings = research_agent.run(state["topic"], state["source"])
        if findings:
            say(f"Gathered {len(findings)} research finding(s).")
        return {"findings": findings}

    def outline_node(state: PipelineState) -> PipelineState:
        say("Designing the narrative outline…")
        outline = outline_agent.run(
            state["topic"],
            state["source"],
            state.get("findings", []),
            target_slides=state.get("target_slides", 10),
        )
        say(f"Outline ready: {len(outline.sections)} sections.")
        return {"outline": outline}

    def content_node(state: PipelineState) -> PipelineState:
        say("Writing slide content…")
        deck = content_agent.run(
            state["outline"],
            state["source"],
            state.get("findings", []),
            theme=state.get("theme", settings.theme),
        )
        say(f"Drafted {len(deck.slides)} slide(s).")
        return {"deck": deck}

    def design_node(state: PipelineState) -> PipelineState:
        say("Art-directing layout and theme…")
        deck = design_agent.run(state["deck"], theme=state.get("theme", settings.theme))
        say(f"Theme locked: {deck.theme}.")
        return {"deck": deck}

    def render_node(state: PipelineState) -> PipelineState:
        say("Rendering PowerPoint…")
        path = render_deck(state["deck"], settings.output_dir)
        say(f"Saved deck → {path}")
        return {"output_path": str(path)}

    graph = StateGraph(PipelineState)
    graph.add_node("research", research_node)
    graph.add_node("outline", outline_node)
    graph.add_node("content", content_node)
    graph.add_node("design", design_node)
    graph.add_node("render", render_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "outline")
    graph.add_edge("outline", "content")
    graph.add_edge("content", "design")
    graph.add_edge("design", "render")
    graph.add_edge("render", END)

    return graph.compile()


def generate_deck(
    *,
    topic: str,
    source: str,
    theme: Optional[str] = None,
    target_slides: int = 10,
    settings: Optional[Settings] = None,
    progress: Optional[ProgressFn] = None,
) -> Path:
    """High-level convenience: run the whole pipeline and return the .pptx path."""
    settings = settings or get_settings()
    pipeline = build_pipeline(settings, progress)
    final_state = pipeline.invoke(
        {
            "topic": topic,
            "source": source,
            "theme": theme or settings.theme,
            "target_slides": target_slides,
        }
    )
    return Path(final_state["output_path"])
