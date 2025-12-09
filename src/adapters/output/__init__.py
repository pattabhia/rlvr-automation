"""
Output Adapters (Secondary/Driven Adapters)

Concrete implementations of infrastructure dependencies.
Examples: Qdrant, OpenAI, Ollama, File Storage

These adapters:
- Implement output ports
- Handle technical details of external systems
- Abstract away third-party libraries
"""

from .llm import ChatOllamaAdapter, ChatOpenAIAdapter
from .embedding import (
    SentenceTransformerAdapter,
    HashingAdapter,
    OpenAIEmbeddingAdapter,
)
from .vectorstore import QdrantAdapter
from .verification import RagasAdapter

__all__ = [
    "ChatOllamaAdapter",
    "ChatOpenAIAdapter",
    "SentenceTransformerAdapter",
    "HashingAdapter",
    "OpenAIEmbeddingAdapter",
    "QdrantAdapter",
    "RagasAdapter",
]
