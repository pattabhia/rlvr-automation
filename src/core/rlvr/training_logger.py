"""
RLVR Training Logger - JSONL logging for DPO training data.

This service logs all RLVR candidate generations to JSONL format for later
use in Direct Preference Optimization (DPO) training.

Each log entry contains:
- Question and context
- All generated candidates with their rewards
- The chosen best candidate
- Timestamp for tracking

This is CORE DOMAIN LOGIC - it depends only on standard library.
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from src.logging import get_logger

logger = get_logger(__name__)


class RLVRTrainingLogger:
    """
    Core service for logging RLVR training data to JSONL.

    Logs each multi-candidate generation session to a JSONL file,
    capturing all candidates, rewards, and the chosen answer for
    later DPO training.
    """

    def __init__(self, log_path: Path | str = "training_data/rlvr_training.jsonl"):
        """
        Initialize RLVR training logger.

        Args:
            log_path: Path to JSONL log file (created if doesn't exist)
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"RLVR Training Logger initialized: {self.log_path}")

    def log_candidates(
        self,
        question: str,
        context: str,
        candidates: List[Dict],
        best_index: int,
    ) -> None:
        """
        Log a multi-candidate generation session to JSONL.

        Args:
            question: User's question
            context: Retrieved context used for generation
            candidates: List of candidate dictionaries with 'answer', 'reward', etc.
            best_index: Index of the chosen best candidate
        """
        # Create log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "context_snippet": context[:1000],  # First 1000 chars to save space
            "candidates": [
                {
                    "index": c["index"],
                    "answer": c["answer"],
                    "reward": c["reward"],
                    "temperature": c.get("temperature", 0.0),
                }
                for c in candidates
            ],
            "chosen_index": best_index,
            "num_candidates": len(candidates),
        }

        # Append to JSONL file
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            logger.debug(
                f"Logged RLVR training entry: "
                f"question={question[:50]}..., "
                f"num_candidates={len(candidates)}, "
                f"chosen_index={best_index}"
            )

        except Exception as e:
            logger.error(f"Failed to log RLVR training data: {e}")

    def get_training_stats(self) -> Dict:
        """
        Get statistics about logged training data.

        Returns:
            Dictionary with counts, average rewards, etc.
        """
        if not self.log_path.exists():
            return {
                "total_entries": 0,
                "total_candidates": 0,
                "avg_best_reward": 0.0,
            }

        try:
            entries = []
            with self.log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))

            if not entries:
                return {
                    "total_entries": 0,
                    "total_candidates": 0,
                    "avg_best_reward": 0.0,
                }

            total_candidates = sum(e["num_candidates"] for e in entries)
            best_rewards = [
                e["candidates"][e["chosen_index"]]["reward"]
                for e in entries
                if e["candidates"]
            ]
            avg_best_reward = sum(best_rewards) / len(best_rewards) if best_rewards else 0.0

            return {
                "total_entries": len(entries),
                "total_candidates": total_candidates,
                "avg_best_reward": avg_best_reward,
                "avg_candidates_per_entry": total_candidates / len(entries),
            }

        except Exception as e:
            logger.error(f"Failed to compute training stats: {e}")
            return {
                "total_entries": 0,
                "total_candidates": 0,
                "avg_best_reward": 0.0,
            }
