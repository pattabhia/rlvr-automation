"""
Dependency Injection / Factory Functions

This module creates and wires together all dependencies (adapters)
based on configuration. This is where hexagonal architecture comes alive:

- Factories read configuration
- Create appropriate adapters (implementations)
- Return them as ports (interfaces)
- Core domain receives ports, not concrete adapters

This ensures the core domain is decoupled from infrastructure.
"""

from __future__ import annotations

from src.config import settings
from src.adapters.output.embedding import HashingAdapter, OpenAIEmbeddingAdapter, SentenceTransformerAdapter
from src.adapters.output.llm import ChatOllamaAdapter, ChatOpenAIAdapter
from src.adapters.output.vectorstore import QdrantAdapter
from src.adapters.output.verification import RagasAdapter
from src.adapters.output.pdf_processor import PDFPlumberAdapter
from src.core import RAGService
from src.logging import get_logger
from src.ports.output import EmbeddingsPort, LLMPort, PDFProcessorPort, VerificationPort, VectorStorePort

logger = get_logger(__name__)


def create_embeddings() -> EmbeddingsPort:
    backend = getattr(settings.embedding, "backend", "sentence").lower()
    if backend == "hashing":
        logger.info("Using hashing embeddings (offline, no download)")
        return HashingAdapter()
    if backend == "openai":
        logger.info("Using OpenAI embeddings backend")
        return OpenAIEmbeddingAdapter()
    logger.info("Using sentence-transformer embeddings backend")
    return SentenceTransformerAdapter()


def create_vector_store(embeddings: EmbeddingsPort) -> VectorStorePort:
    backend = settings.vector_store.backend.lower()
    if backend == "qdrant":
        return QdrantAdapter(embeddings=embeddings)
    raise ValueError(f"Unsupported VECTOR_STORE_BACKEND: {backend}")


def create_llm() -> LLMPort:
    backend = settings.llm.backend.lower()
    if backend == "ollama":
        return ChatOllamaAdapter()
    if backend == "openai":
        return ChatOpenAIAdapter()
    raise ValueError(f"Unsupported LLM_BACKEND: {backend}")


def create_pdf_processor() -> PDFProcessorPort:
    """Create PDF processor adapter."""
    return PDFPlumberAdapter()


def create_verifier() -> VerificationPort:
    """Create verification adapter (RAGAS)."""
    return RagasAdapter()


def create_rag_service(embeddings: EmbeddingsPort | None = None) -> RAGService:
    """
    Create fully-wired RAG service (core domain).

    This is the main factory that assembles the entire application.
    It creates all necessary adapters and injects them into the core domain.

    Args:
        embeddings: Optional embeddings adapter (uses create_embeddings() if None)

    Returns:
        Fully configured RAGService instance
    """
    embeddings_adapter = embeddings or create_embeddings()
    vector_store = create_vector_store(embeddings=embeddings_adapter)
    pdf_processor = create_pdf_processor()
    verifier = create_verifier()
    llm = create_llm()

    return RAGService(
        vector_store=vector_store,
        embeddings=embeddings_adapter,
        pdf_processor=pdf_processor,
        verifier=verifier,
        llm=llm,
        top_k=settings.retrieval.top_k,
    )


# Backward compatibility alias
build_service = create_rag_service

