"""ML Dataset Generator Agent.

An agentic pipeline that turns a natural-language request into a complete,
ML-ready dataset plus metadata, EDA, validation, a baseline evaluation, and
multi-format exports.
"""

__version__ = "1.0.0"

from app.services.generator import DatasetService

__all__ = ["DatasetService", "__version__"]
