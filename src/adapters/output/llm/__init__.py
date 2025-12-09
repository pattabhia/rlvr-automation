"""LLM Adapters - Concrete implementations of LLMPort."""

from .ollama import ChatOllamaAdapter
from .openai import ChatOpenAIAdapter

__all__ = [
    "ChatOllamaAdapter",
    "ChatOpenAIAdapter",
]
