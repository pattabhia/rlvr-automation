"""OpenAI Embedding Adapter - Cloud embeddings via OpenAI API."""

from typing import List

try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    from langchain.embeddings.base import Embeddings  # type: ignore

from langchain_openai import OpenAIEmbeddings

from src.config import settings
from src.ports.output import EmbeddingsPort


class OpenAIEmbeddingAdapter(Embeddings, EmbeddingsPort):
    """
    Embedding adapter using OpenAI's embedding models.

    Uses OpenAI API for generating embeddings (paid, requires API key).
    Supports text-embedding-3-small, text-embedding-3-large, etc.

    Trade-offs:
    - ✅ High quality embeddings
    - ✅ Fast (cloud-based)
    - ✅ Works on Streamlit Cloud
    - ❌ Costs money (~$0.02 per 1M tokens)
    - ❌ Requires API key
    """

    def __init__(self) -> None:
        super().__init__()
        self.client = OpenAIEmbeddings(
            model=settings.llm.openai.embedding_model,
            api_key=settings.llm.openai.api_key,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents via OpenAI API."""
        return self.client.embed_documents(list(texts))

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query via OpenAI API."""
        return self.client.embed_query(query)
