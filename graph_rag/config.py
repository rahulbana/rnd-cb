"""Central configuration and the shared OpenAI client.

Loads settings from environment variables (via a .env file if present) so the
rest of the package never touches os.environ directly.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Chat model used for extraction and answering. gpt-4o-mini is cheap and fine
# for learning; swap for gpt-4o if you want higher-quality extraction.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Where the built graph is saved / loaded from.
GRAPH_PATH = os.getenv("GRAPH_PATH", "graph.gml")

# Chunking: how many characters per chunk and how much chunks overlap.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# How many hops out from a matched entity we walk when gathering context.
TRAVERSAL_DEPTH = int(os.getenv("TRAVERSAL_DEPTH", "1"))


def get_client() -> OpenAI:
    """Return an OpenAI client, failing early with a clear message if no key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your "
            "key, or export OPENAI_API_KEY in your shell."
        )
    return OpenAI(api_key=api_key)
