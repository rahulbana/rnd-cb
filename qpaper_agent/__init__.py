"""qpaper_agent — a multi-agent system that finds and downloads board exam
question papers (CBSE / ICSE / UP Board / etc.) for a given subject and class.

The system is built from four cooperating agents driven by an OpenAI LLM:

    1. PlannerAgent     — turns a request into a concrete search plan.
    2. SearchAgent      — uses web search to find candidate papers.
    3. ValidatorAgent   — verifies each candidate matches the request.
    4. DownloaderAgent  — downloads the validated papers to disk.

The :class:`~qpaper_agent.orchestrator.Orchestrator` wires them together.
"""

from .models import PaperRequest
from .orchestrator import Orchestrator

__all__ = ["PaperRequest", "Orchestrator"]
__version__ = "0.1.0"
