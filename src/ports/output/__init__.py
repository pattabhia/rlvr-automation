"""
Output Ports (Secondary/Driven Ports)

Define what the application NEEDS from external systems.
These represent dependencies and infrastructure contracts.

Core domain depends on these interfaces.
Output adapters (DB, APIs, etc.) implement these interfaces.
"""

from .llm import LLMPort
from .embedding import EmbeddingsPort
from .vectorstore import VectorStorePort
from .verification import VerificationPort
from .pdf_processor import PDFProcessorPort

__all__ = [
    "LLMPort",
    "EmbeddingsPort",
    "VectorStorePort",
    "VerificationPort",
    "PDFProcessorPort",
]
