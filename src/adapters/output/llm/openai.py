"""OpenAI LLM Adapter - Cloud LLM via OpenAI API."""

from langchain_openai import ChatOpenAI

from src.config import settings
from src.ports.output import LLMPort


class ChatOpenAIAdapter(LLMPort):
    """
    LLM adapter for OpenAI Chat models.

    Uses OpenAI API for LLM inference (paid, requires API key).
    Supports GPT-4, GPT-4o-mini, etc.
    """

    def __init__(self):
        self.client = ChatOpenAI(
            model=settings.llm.openai.model,
            api_key=settings.llm.openai.api_key,
            temperature=0,
        )

    def invoke(self, inputs) -> object:
        """Invoke OpenAI chat model with given inputs."""
        return self.client.invoke(inputs)

    def __getattr__(self, item):
        """Proxy other attributes to underlying client."""
        return getattr(self.client, item)
