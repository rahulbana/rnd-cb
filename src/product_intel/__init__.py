"""Multi-Agent Product Review & Feature Intelligence System.

Turn a product detail page + its customer reviews into a prioritized vNext
product backlog via a five-agent pipeline. See :class:`Orchestrator`.
"""

from __future__ import annotations

from .orchestrator import Orchestrator, PipelineState
from .schemas import ProductReviewReport

__version__ = "0.1.0"

__all__ = ["Orchestrator", "PipelineState", "ProductReviewReport", "__version__"]
