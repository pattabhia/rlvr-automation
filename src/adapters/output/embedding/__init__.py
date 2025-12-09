"""Embedding Adapters - Concrete implementations of EmbeddingsPort."""

from .sentence import SentenceTransformerAdapter
from .hashing import HashingAdapter
from .openai import OpenAIEmbeddingAdapter

__all__ = [
    "SentenceTransformerAdapter",
    "HashingAdapter",
    "OpenAIEmbeddingAdapter",
]
