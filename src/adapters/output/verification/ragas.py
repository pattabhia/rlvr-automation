"""RAGAS Verification Adapter - RAG evaluation using RAGAS framework."""

from typing import Dict, List

from src.config import settings
from src.logging import get_logger
from src.ports.output import VerificationPort

logger = get_logger(__name__)

try:
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness
    from datasets import Dataset
    from langchain_ollama import ChatOllama
    from langchain_openai import ChatOpenAI
    RAGAS_AVAILABLE = True
except Exception as e:  # pragma: no cover - optional dependency handling
    logger.warning("RAGAS dependencies not available: %s", e)
    evaluate = None  # type: ignore
    answer_relevancy = None  # type: ignore
    faithfulness = None  # type: ignore
    Dataset = None  # type: ignore
    ChatOllama = None  # type: ignore
    ChatOpenAI = None  # type: ignore
    RAGAS_AVAILABLE = False


class RagasAdapter(VerificationPort):
    """
    RAGAS (RAG Assessment) verification adapter.

    Evaluates RAG answers using:
    - Faithfulness: Is the answer grounded in the context?
    - Relevancy: Does the answer address the question?

    Supports three backends:
    1. 'heuristic' - Fast, free, rule-based (default for Streamlit Cloud)
    2. 'ollama' - Local LLM evaluation (requires Ollama)
    3. 'openai' - Cloud LLM evaluation (requires OpenAI API key)

    Configure via RAGAS_LLM_BACKEND environment variable.
    """

    def verify(self, question: str, answer: str, contexts: List[str]) -> Dict:
        """
        Verify answer quality using RAGAS or heuristic fallback.

        Args:
            question: The user's question
            answer: The generated answer
            contexts: List of context strings used to generate the answer

        Returns:
            Dictionary with:
            - faithfulness: Score for factual accuracy (0-1)
            - relevancy: Score for answer relevance (0-1)
            - overall_score: Average of faithfulness and relevancy
            - confidence: "high" or "low"
            - issues: List of identified issues
        """
        backend = settings.verification.ragas_llm_backend.lower()

        # If heuristic mode, skip RAGAS entirely
        if backend == "heuristic":
            logger.info("Using heuristic verification (RAGAS_LLM_BACKEND=heuristic)")
            faith, relevancy = self._heuristic_verification(answer, contexts)
        elif RAGAS_AVAILABLE and evaluate and Dataset:
            try:
                # Create LLM based on configuration
                llm = self._create_ragas_llm(backend)
                logger.info("Running RAGAS verification with %s", backend)

                data = {
                    "question": [question],
                    "answer": [answer],
                    "contexts": [contexts],
                }
                dataset = Dataset.from_dict(data)

                # Run RAGAS with configured LLM
                results = evaluate(
                    dataset,
                    metrics=[faithfulness, answer_relevancy],
                    llm=llm
                )

                scores = results.to_pandas().iloc[0]
                faith = float(scores.get("faithfulness", 0.0))
                relevancy = float(scores.get("answer_relevancy", 0.0))

                logger.info("RAGAS scores: faithfulness=%.3f, relevancy=%.3f", faith, relevancy)

            except Exception as e:
                logger.warning("RAGAS evaluation failed: %s, using heuristic fallback", e)
                # Fall back to heuristic
                faith, relevancy = self._heuristic_verification(answer, contexts)
        else:
            logger.info("RAGAS not available, using heuristic verification")
            faith, relevancy = self._heuristic_verification(answer, contexts)

        overall = (faith + relevancy) / 2 if (faith or relevancy) else 0.0
        confidence = (
            "high"
            if faith >= settings.verification.faithfulness_threshold
            and relevancy >= settings.verification.relevancy_threshold
            else "low"
        )
        return {
            "faithfulness": faith,
            "relevancy": relevancy,
            "overall_score": overall,
            "confidence": confidence,
            "issues": [] if confidence == "high" else ["Low verification confidence"],
        }

    def _create_ragas_llm(self, backend: str):
        """Create LLM for RAGAS evaluation based on backend configuration."""
        if backend == "openai":
            if not settings.llm.openai.api_key:
                raise ValueError("RAGAS_LLM_BACKEND=openai but OPENAI_API_KEY not set")
            logger.info("Creating OpenAI LLM for RAGAS: %s", settings.llm.openai.model)
            return ChatOpenAI(
                model=settings.llm.openai.model,
                api_key=settings.llm.openai.api_key,
                temperature=0
            )
        elif backend == "ollama":
            logger.info("Creating Ollama LLM for RAGAS: %s", settings.llm.ollama.model)
            return ChatOllama(
                base_url=settings.llm.ollama.base_url,
                model=settings.llm.ollama.model,
                temperature=0
            )
        else:
            raise ValueError(
                f"Unknown RAGAS_LLM_BACKEND: {backend}. "
                f"Use 'ollama', 'openai', or 'heuristic'"
            )

    def _heuristic_verification(self, answer: str, contexts: List[str]) -> tuple[float, float]:
        """
        Simple heuristic verification when RAGAS is unavailable.

        Uses basic text analysis:
        - Faithfulness: Based on word overlap between answer and context
        - Relevancy: Based on answer length and "don't know" detection

        Fast and free, but less accurate than RAGAS with LLM.
        """
        # Check if answer is substantial
        answer_lower = answer.lower()
        has_substantial_answer = len(answer) > 20 and "don't know" not in answer_lower

        # Check context overlap
        context_text = " ".join(contexts).lower()
        answer_words = set(answer_lower.split())
        context_words = set(context_text.split())

        if answer_words:
            overlap_ratio = len(answer_words & context_words) / len(answer_words)
        else:
            overlap_ratio = 0.0

        # Simple heuristic scores
        faithfulness = 0.85 if overlap_ratio > 0.3 else 0.50
        relevancy = 0.85 if has_substantial_answer else 0.30

        logger.debug("Heuristic scores: faithfulness=%.3f, relevancy=%.3f", faithfulness, relevancy)

        return faithfulness, relevancy
