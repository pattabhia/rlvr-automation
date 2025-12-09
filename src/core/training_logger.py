"""
Training data logger for RLVR

Logs all Q&A interactions with verification scores for future RL fine-tuning.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from src.logging import get_logger

logger = get_logger(__name__)


class TrainingDataLogger:
    """Log Q&A pairs with verification scores for future RL training."""

    def __init__(self, log_dir: str = "training_data", enabled: bool = True):
        self.enabled = enabled
        if not enabled:
            logger.info("Training data logging is DISABLED")
            return

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        logger.info("Training data logging enabled, directory: %s", self.log_dir)

    def log_interaction(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        verification_scores: Dict,
        sources: List,
    ) -> None:
        """Log a single Q&A interaction with verification scores."""
        if not self.enabled:
            return

        try:
            # Prepare data
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "verification": verification_scores,
                "sources": [
                    {
                        "page": getattr(s, "metadata", {}).get("page", "?"),
                        "source": getattr(s, "metadata", {}).get("source", "unknown"),
                        "content_preview": getattr(s, "page_content", "")[:200],
                    }
                    for s in sources
                ],
            }

            # Log to monthly JSONL file (one JSON object per line)
            log_file = self.log_dir / f"training_data_{datetime.now().strftime('%Y%m')}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

            logger.debug(
                "Logged interaction: score=%.3f, question=%s",
                verification_scores.get("overall_score", 0),
                question[:50],
            )

        except Exception as e:
            logger.error("Failed to log training data: %s", e)

    def get_stats(self) -> Dict:
        """Get statistics about logged training data."""
        if not self.enabled:
            return {"enabled": False}

        total_interactions = 0
        score_sum = 0.0
        high_score_count = 0

        for log_file in self.log_dir.glob("*.jsonl"):
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    total_interactions += 1
                    score = data["verification"]["overall_score"]
                    score_sum += score
                    if score >= 0.8:
                        high_score_count += 1

        avg_score = score_sum / total_interactions if total_interactions > 0 else 0

        return {
            "enabled": True,
            "total_interactions": total_interactions,
            "average_score": avg_score,
            "high_quality_count": high_score_count,
            "high_quality_percentage": (high_score_count / total_interactions * 100) if total_interactions > 0 else 0,
        }
