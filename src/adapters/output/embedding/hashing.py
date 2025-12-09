"""Hashing Embedding Adapter - Lightweight, download-free embeddings."""

from typing import List

try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    from langchain.embeddings.base import Embeddings  # type: ignore

from sklearn.feature_extraction.text import HashingVectorizer

from src.ports.output import EmbeddingsPort


class HashingAdapter(Embeddings, EmbeddingsPort):
    """
    Lightweight embedding adapter using HashingVectorizer.

    Uses sklearn's hashing trick for fast, deterministic embeddings.
    No model download required - perfect for quick prototyping.

    Trade-offs:
    - ✅ Extremely fast, no downloads
    - ✅ Deterministic (same text = same embedding)
    - ❌ Lower quality than neural embeddings
    - ❌ No semantic understanding
    """

    def __init__(self, n_features: int = 4096) -> None:
        super().__init__()
        self.vectorizer = HashingVectorizer(
            n_features=n_features,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using hashing."""
        if isinstance(texts, str):
            texts = [texts]
        mat = self.vectorizer.transform(texts)
        return mat.toarray().tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query using hashing."""
        return self.embed_documents([query])[0]
