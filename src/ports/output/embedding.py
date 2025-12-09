"""Embeddings Port - Interface for embedding model adapters."""

from typing import List, Protocol


class EmbeddingsPort(Protocol):
    """Port for embedding model implementations."""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents.

        Args:
            texts: List of text documents to embed

        Returns:
            List of embedding vectors (one per document)
        """
        ...

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query.

        Args:
            query: Query text to embed

        Returns:
            Embedding vector for the query
        """
        ...
