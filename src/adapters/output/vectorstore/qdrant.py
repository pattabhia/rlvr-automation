"""Qdrant Vector Store Adapter - Vector database for similarity search."""

from typing import Iterable, List

from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from src.config import settings
from src.logging import get_logger
from src.ports.output import EmbeddingsPort, VectorStorePort

logger = get_logger(__name__)


def _create_client() -> QdrantClient:
    """Create Qdrant client (cloud or local based on configuration)."""
    if settings.qdrant.is_cloud:
        logger.info(
            "Initializing Qdrant cloud client for collection=%s",
            settings.qdrant.collection_name
        )
        return QdrantClient(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            prefer_grpc=False,
        )

    logger.info(
        "Initializing Qdrant local client for collection=%s",
        settings.qdrant.collection_name
    )
    return QdrantClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        prefer_grpc=False,
    )


def _extract_vector_size(collection_info) -> int | None:
    """Extract vector dimension from collection info."""
    try:
        vectors = collection_info.config.params.vectors
        if hasattr(vectors, "size"):
            return vectors.size  # type: ignore[attr-defined]
        if isinstance(vectors, dict):
            return vectors.get("size")
    except Exception:
        return None
    return None


def _ensure_collection(client: QdrantClient, collection: str) -> None:
    """
    Ensure collection exists with expected vector dimension.

    Recreates collection if dimension mismatch detected (prevents errors
    when switching between different embedding models).
    """
    expected_dim = settings.embedding.dimension
    try:
        info = client.get_collection(collection)
        actual_dim = _extract_vector_size(info)
        if actual_dim and actual_dim != expected_dim:
            logger.warning(
                "Collection %s dimension mismatch (expected %s, found %s). "
                "Recreating collection and dropping existing vectors.",
                collection,
                expected_dim,
                actual_dim,
            )
            raise ValueError("dimension_mismatch")
        return
    except Exception:
        logger.info("Creating (or recreating) collection %s with dim=%s", collection, expected_dim)
        client.recreate_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=expected_dim,
                distance=Distance.COSINE,
            ),
        )


class QdrantAdapter(VectorStorePort):
    """
    Qdrant vector database adapter.

    Supports both local (Docker) and cloud (Qdrant Cloud) deployments.
    Handles vector storage, similarity search, and retrieval.

    Local setup:
    - Requires Qdrant Docker container
    - Free, runs on your machine
    - Data stored locally

    Cloud setup:
    - Uses Qdrant Cloud service
    - Free tier: 1GB storage
    - Accessible from anywhere (Streamlit Cloud compatible)
    """

    def __init__(self, embeddings: EmbeddingsPort, collection_name: str | None = None):
        collection = collection_name or settings.qdrant.collection_name
        client = _create_client()
        _ensure_collection(client, collection)

        # Expose client for direct access (retrieval fallback)
        self.client = client

        # Provide search method fallback for clients missing it
        if not hasattr(client, "search"):
            search_points = getattr(client, "search_points", None)
            if search_points:
                client.search = search_points  # type: ignore[attr-defined,assignment]
            else:
                http = getattr(client, "http", None)
                http_search = getattr(getattr(http, "points_api", None), "search_points", None)
                query_points = getattr(client, "query_points", None)
                if http_search:
                    client.search = http_search  # type: ignore[attr-defined,assignment]
                elif query_points:
                    def _search_wrapper(**kwargs):
                        using = kwargs.get("vector_name") or kwargs.get("using")
                        return client.query_points(
                            collection_name=kwargs.get("collection_name"),
                            query=kwargs.get("query_vector"),
                            query_filter=kwargs.get("query_filter"),
                            search_params=kwargs.get("search_params"),
                            limit=kwargs.get("limit"),
                            with_payload=kwargs.get("with_payload", True),
                            with_vectors=kwargs.get("with_vectors", True),
                            score_threshold=kwargs.get("score_threshold"),
                            using=using,
                        )
                    client.search = _search_wrapper  # type: ignore[attr-defined,assignment]
                else:
                    logger.error("Qdrant client missing search/search_points/query_points; update qdrant-client")

        logger.info(
            "Setting up Qdrant vector store (collection=%s, profile=%s)",
            collection,
            settings.qdrant.active_profile
        )
        self.store = Qdrant(
            client=client,
            collection_name=collection,
            embeddings=embeddings,
        )

    def add_documents(self, documents: Iterable) -> List[str]:
        """Add documents to the vector store."""
        docs = list(documents)
        logger.info("Adding %d documents to vector store", len(docs))
        return self.store.add_documents(docs)

    def as_retriever(self, k: int):
        """Create a retriever for similarity search."""
        logger.info("Creating retriever with top_k=%d", k)
        return self.store.as_retriever(search_kwargs={"k": k})
