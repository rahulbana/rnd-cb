"""Research graph package.

Import concrete entry points from their modules to avoid pulling heavy
dependencies (langgraph) when you only need a pure submodule such as
`app.graph.citations`:

    from app.graph.builder import build_graph
    from app.graph.state import ResearchState
"""
