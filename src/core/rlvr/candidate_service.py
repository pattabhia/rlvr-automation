"""
RLVR Candidate Service - Multi-candidate generation and selection.

This core service implements the RLVR algorithm:
1. Generate multiple candidate answers (with different seeds/parameters)
2. Score each candidate with a reward function
3. Select the best candidate
4. Log all candidates for DPO training

This is CORE DOMAIN LOGIC - it depends only on ports, never on adapters.
"""

from typing import Dict, List
from datetime import datetime

from src.ports.output import LLMPort, RewardPort
from src.logging import get_logger

logger = get_logger(__name__)


class RLVRCandidateService:
    """
    Core service for RLVR multi-candidate generation and selection.

    This implements the heart of the RLVR algorithm:
    - Generates N candidates per question
    - Scores each with verifiable reward
    - Selects best candidate
    - Returns all for logging
    """

    def __init__(
        self,
        llm: LLMPort,
        reward_function: RewardPort,
        num_candidates: int = 3,
    ):
        """
        Initialize RLVR candidate service.

        Args:
            llm: Language model port for generation
            reward_function: Reward computation port
            num_candidates: Number of candidates to generate per question
        """
        self.llm = llm
        self.reward_function = reward_function
        self.num_candidates = num_candidates

    def generate_and_score_candidates(
        self,
        question: str,
        context: str,
        prompt_template: str,
    ) -> Dict:
        """
        Generate multiple candidates, score them, and select the best.

        Args:
            question: User's question
            context: Retrieved context for answering
            prompt_template: Prompt template (with {context} and {question} placeholders)

        Returns:
            Dictionary with:
            - best_answer: The highest-scoring candidate
            - candidates: List of all candidates with rewards
            - best_index: Index of best candidate
        """
        # Build prompt
        prompt = prompt_template.format(context=context, question=question)

        candidates = []

        logger.info(f"Generating {self.num_candidates} RLVR candidates...")

        # Generate multiple candidates
        # Note: Ollama/OpenAI don't expose seed directly, so we use temperature variation
        temperatures = [0.0, 0.3, 0.7][:self.num_candidates]

        for idx, temp in enumerate(temperatures):
            try:
                # Generate answer
                # Note: We'd need to update LLMPort to accept temperature
                # For now, just generate with default settings
                response = self.llm.invoke(prompt)
                answer = getattr(response, "content", str(response))

                # Compute reward
                reward = self.reward_function.compute_reward(question, answer)

                candidates.append({
                    "answer": answer,
                    "reward": reward,
                    "temperature": temp,
                    "index": idx,
                })

                logger.debug(f"Candidate {idx}: reward={reward:.3f}, answer={answer[:100]}...")

            except Exception as e:
                logger.error(f"Failed to generate candidate {idx}: {e}")
                # Add failed candidate
                candidates.append({
                    "answer": f"[Generation failed: {e}]",
                    "reward": 0.0,
                    "temperature": temp,
                    "index": idx,
                })

        # Select best candidate
        if not candidates:
            logger.warning("No candidates generated!")
            return {
                "best_answer": "I don't have enough information to answer that.",
                "candidates": [],
                "best_index": -1,
            }

        best_idx = max(range(len(candidates)), key=lambda i: candidates[i]["reward"])
        best_candidate = candidates[best_idx]

        logger.info(
            f"RLVR selected candidate {best_idx} with reward={best_candidate['reward']:.3f}"
        )

        return {
            "best_answer": best_candidate["answer"],
            "candidates": candidates,
            "best_index": best_idx,
        }
