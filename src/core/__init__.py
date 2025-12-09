"""
Core Domain Logic - RLVR PDF Chat

This package contains the pure business logic of the RLVR system.

KEY PRINCIPLE:
    The core domain NEVER depends on external frameworks or adapters.
    It only depends on ports (interfaces).

    This means:
    - No imports from adapters/
    - No imports from config/
    - No imports from external frameworks (except LangChain as domain model)
    - Only ports and domain models

The core represents the "essence" of what the application does,
independent of how it's delivered (web, CLI, API) or what external
systems it uses (Ollama, OpenAI, Qdrant, etc.).
"""

from .rag_service import RAGService
from .training_logger import TrainingDataLogger

__all__ = [
    "RAGService",
    "TrainingDataLogger",
]
