"""Sentence Transformer Embedding Adapter - Local embeddings via sentence-transformers."""

from functools import lru_cache
from typing import List
from urllib.parse import urlparse

from langchain_community.embeddings import SentenceTransformerEmbeddings

try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    from langchain.embeddings.base import Embeddings  # type: ignore

from src.config import settings
from src.logging import get_logger
from src.ports.output import EmbeddingsPort

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def load_embedding_model() -> SentenceTransformerEmbeddings:
    """Load sentence-transformer model (cached for reuse)."""
    logger.info("Loading embedding model %s", settings.embedding.model_name)

    # Shim for huggingface_hub>=0.36 where cached_download was removed
    try:
        import huggingface_hub
        if not hasattr(huggingface_hub, "cached_download"):
            def cached_download(**kwargs):  # type: ignore[override]
                url = kwargs.get("url")
                cache_dir = kwargs.get("cache_dir")
                local_only = kwargs.get("local_files_only", False)
                force_download = kwargs.get("force_download", False)
                token = kwargs.get("token")
                if not url:
                    raise RuntimeError("cached_download called without url")
                parsed = urlparse(url)
                parts = parsed.path.strip("/").split("/")
                if "resolve" not in parts or len(parts) < 4:
                    raise RuntimeError(f"Unexpected HF URL format: {url}")
                resolve_idx = parts.index("resolve")
                repo_id = "/".join(parts[:resolve_idx])
                revision = parts[resolve_idx + 1]
                filename = "/".join(parts[resolve_idx + 2 :])
                return huggingface_hub.hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    revision=revision,
                    cache_dir=cache_dir,
                    local_files_only=local_only,
                    force_download=force_download,
                    token=token,
                )

            huggingface_hub.cached_download = cached_download  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Could not patch huggingface_hub cached_download: %s", exc)

    return SentenceTransformerEmbeddings(model_name=settings.embedding.model_name)


class SentenceTransformerAdapter(Embeddings, EmbeddingsPort):
    """
    Embedding adapter using sentence-transformers library.

    Uses local transformer models for generating embeddings (free, open-source).
    Supports models like multi-qa-mpnet-base-dot-v1, all-MiniLM-L6-v2, etc.

    Works on Streamlit Cloud (pure Python, no Docker required).
    """

    def __init__(self) -> None:
        super().__init__()
        self.model = load_embedding_model()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        if isinstance(texts, str):
            texts = [texts]
        return self.model.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query."""
        return self.model.embed_query(query)
