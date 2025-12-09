"""Verification Port - Interface for answer verification adapters."""

from typing import Dict, List, Protocol


class VerificationPort(Protocol):
    """Port for verification implementations (RAGAS, custom metrics, etc.)."""

    def verify(self, question: str, answer: str, contexts: List[str]) -> Dict:
        """
        Verify the quality of an answer given the question and contexts.

        Args:
            question: The user's question
            answer: The generated answer
            contexts: List of context strings used to generate the answer

        Returns:
            Dictionary containing verification metrics:
            - faithfulness: Score for factual accuracy (0-1)
            - relevancy: Score for answer relevance (0-1)
            - overall_score: Combined score (0-1)
            - confidence: "high" or "low"
            - issues: List of identified issues
        """
        ...
