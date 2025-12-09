"""Reward Port - Interface for RLVR reward computation."""

from typing import Protocol


class RewardPort(Protocol):
    """
    Port for reward computation in RLVR.

    Reward functions compute numeric scores (0.0 to 1.0) that measure
    how well an answer matches verifiable ground truth.
    """

    def compute_reward(self, question: str, answer: str) -> float:
        """
        Compute reward for an answer.

        Args:
            question: The user's question
            answer: The generated answer to evaluate

        Returns:
            Reward score between 0.0 (completely wrong) and 1.0 (perfect)
        """
        ...
