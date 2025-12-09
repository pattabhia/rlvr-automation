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
from src.adapters.output.reward import PricingRewardAdapter
from src.core import RAGService
from src.core.rlvr import RLVRCandidateService, RLVRTrainingLogger
from src.logging import get_logger
from src.ports.output import EmbeddingsPort, LLMPort, PDFProcessorPort, RewardPort, VerificationPort, VectorStorePort

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


def create_reward_function() -> RewardPort:
    """
    Create reward function adapter for RLVR.

    Currently uses PricingRewardAdapter for Taj Hotels pricing use case.
    Can be extended to support other reward functions based on configuration.

    Returns:
        Reward function adapter implementing RewardPort
    """
    logger.info("Creating pricing reward adapter for RLVR")
    return PricingRewardAdapter()


def create_rlvr_candidate_service(
    llm: LLMPort | None = None,
    reward_function: RewardPort | None = None,
    num_candidates: int = 3,
) -> RLVRCandidateService:
    """
    Create RLVR candidate generation service.

    This service generates multiple candidate answers and selects the best
    one based on verifiable rewards.

    Args:
        llm: Optional LLM adapter (uses create_llm() if None)
        reward_function: Optional reward adapter (uses create_reward_function() if None)
        num_candidates: Number of candidates to generate per question

    Returns:
        Configured RLVRCandidateService instance
    """
    llm_adapter = llm or create_llm()
    reward_adapter = reward_function or create_reward_function()

    logger.info(f"Creating RLVR candidate service with {num_candidates} candidates")
    return RLVRCandidateService(
        llm=llm_adapter,
        reward_function=reward_adapter,
        num_candidates=num_candidates,
    )


def create_rlvr_training_logger(log_path: str = "training_data/rlvr_training.jsonl") -> RLVRTrainingLogger:
    """
    Create RLVR training logger for JSONL output.

    This logger records all candidate generations for later DPO training.

    Args:
        log_path: Path to JSONL log file

    Returns:
        Configured RLVRTrainingLogger instance
    """
    logger.info(f"Creating RLVR training logger: {log_path}")
    return RLVRTrainingLogger(log_path=log_path)


def create_rag_service_with_rlvr(
    embeddings: EmbeddingsPort | None = None,
    num_candidates: int = 3,
    enable_rlvr: bool = True,
) -> RAGService:
    """
    Create fully-wired RAG service with RLVR support.

    This creates a RAG service with optional RLVR multi-candidate generation.
    When RLVR is enabled, the service can use answer_question_rlvr() method
    to generate and score multiple candidates.

    Args:
        embeddings: Optional embeddings adapter (uses create_embeddings() if None)
        num_candidates: Number of RLVR candidates to generate per question
        enable_rlvr: Whether to enable RLVR components

    Returns:
        Fully configured RAGService instance with RLVR support
    """
    # Create standard components
    embeddings_adapter = embeddings or create_embeddings()
    vector_store = create_vector_store(embeddings=embeddings_adapter)
    pdf_processor = create_pdf_processor()
    verifier = create_verifier()
    llm = create_llm()

    # Create RLVR components if enabled
    rlvr_candidate_service = None
    rlvr_training_logger = None

    if enable_rlvr:
        rlvr_candidate_service = create_rlvr_candidate_service(
            llm=llm,
            num_candidates=num_candidates,
        )
        rlvr_training_logger = create_rlvr_training_logger()
        logger.info("RLVR components created and injected into RAG service")

    return RAGService(
        vector_store=vector_store,
        embeddings=embeddings_adapter,
        pdf_processor=pdf_processor,
        verifier=verifier,
        llm=llm,
        top_k=settings.retrieval.top_k,
        rlvr_candidate_service=rlvr_candidate_service,
        rlvr_training_logger=rlvr_training_logger,
    )


# Backward compatibility alias
build_service = create_rag_service

