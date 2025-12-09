"""Ollama LLM Adapter - Local LLM via Ollama."""

from langchain_ollama import ChatOllama

from src.config import settings
from src.ports.output import LLMPort


class ChatOllamaAdapter(LLMPort):
    """
    LLM adapter for Ollama Chat models.

    Uses local Ollama server for LLM inference (free, runs on your machine).
    Supports models like Llama 3.2, Mistral, etc.
    """

    def __init__(self):
        self.client = ChatOllama(
            base_url=settings.llm.ollama.base_url,
            model=settings.llm.ollama.model
        )

    def invoke(self, inputs) -> object:
        """Invoke Ollama chat model with given inputs."""
        return self.client.invoke(inputs)

    def __getattr__(self, item):
        """Proxy other attributes to underlying client."""
        return getattr(self.client, item)
