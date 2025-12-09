"""
Analytics module for RLVR metrics and visualizations.

Analyzes training data to provide insights on:
- Training progress
- Score distributions
- Performance trends
- Quality metrics
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

import pandas as pd


class RLVRAnalytics:
    """Analyze RLVR training data and compute metrics."""

    def __init__(self, log_dir: str = "training_data"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

    def load_interactions(self) -> List[Dict]:
        """Load all training interactions from JSONL files."""
        interactions = []
        for log_file in self.log_dir.glob("*.jsonl"):
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    try:
                        interactions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return interactions

    def get_basic_stats(self) -> Dict:
        """Get basic statistics about training data."""
        interactions = self.load_interactions()

        if not interactions:
            return {
                "total_interactions": 0,
                "average_score": 0.0,
                "high_quality_count": 0,
                "medium_quality_count": 0,
                "low_quality_count": 0,
                "progress_percentage": 0.0,
                "target_interactions": 500,
            }

        scores = [i["verification"]["overall_score"] for i in interactions]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Quality thresholds
        high_quality = sum(1 for s in scores if s >= 0.8)
        medium_quality = sum(1 for s in scores if 0.5 <= s < 0.8)
        low_quality = sum(1 for s in scores if s < 0.5)

        target = 500
        progress = min(100.0, (len(interactions) / target) * 100)

        return {
            "total_interactions": len(interactions),
            "average_score": avg_score,
            "high_quality_count": high_quality,
            "medium_quality_count": medium_quality,
            "low_quality_count": low_quality,
            "high_quality_percentage": (high_quality / len(scores) * 100) if scores else 0,
            "medium_quality_percentage": (medium_quality / len(scores) * 100) if scores else 0,
            "low_quality_percentage": (low_quality / len(scores) * 100) if scores else 0,
            "progress_percentage": progress,
            "target_interactions": target,
            "remaining_interactions": max(0, target - len(interactions)),
        }

    def get_score_distribution(self) -> Tuple[List[float], List[float]]:
        """Get score distribution for histogram."""
        interactions = self.load_interactions()

        if not interactions:
            return [], []

        scores = [i["verification"]["overall_score"] for i in interactions]

        # Create bins
        bins = [i/10 for i in range(0, 11)]  # 0.0, 0.1, ..., 1.0

        return scores, bins

    def get_timeline_data(self) -> pd.DataFrame:
        """Get interaction timeline data for trend charts."""
        interactions = self.load_interactions()

        if not interactions:
            return pd.DataFrame(columns=["date", "score", "count"])

        # Parse timestamps and group by date
        data = []
        for interaction in interactions:
            timestamp = interaction.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date = dt.date()
                score = interaction["verification"]["overall_score"]
                data.append({"date": date, "score": score})
            except (ValueError, KeyError):
                continue

        if not data:
            return pd.DataFrame(columns=["date", "score", "count"])

        df = pd.DataFrame(data)

        # Group by date
        daily_stats = df.groupby("date").agg({
            "score": ["mean", "count"]
        }).reset_index()

        daily_stats.columns = ["date", "avg_score", "count"]

        return daily_stats

    def get_score_trend(self) -> Tuple[List[int], List[float]]:
        """Get score trend over interactions (moving average)."""
        interactions = self.load_interactions()

        if not interactions:
            return [], []

        # Sort by timestamp
        sorted_interactions = sorted(
            interactions,
            key=lambda x: x.get("timestamp", "")
        )

        scores = [i["verification"]["overall_score"] for i in sorted_interactions]

        # Calculate moving average (window of 10)
        window = 10
        moving_avg = []
        indices = []

        for i in range(len(scores)):
            if i < window:
                # Use all available data points
                avg = sum(scores[:i+1]) / (i+1)
            else:
                # Use window
                avg = sum(scores[i-window+1:i+1]) / window
            moving_avg.append(avg)
            indices.append(i + 1)

        return indices, moving_avg

    def get_quality_breakdown(self) -> Dict[str, int]:
        """Get breakdown of answer quality."""
        stats = self.get_basic_stats()

        return {
            "High Quality (≥0.8)": stats["high_quality_count"],
            "Medium Quality (0.5-0.8)": stats["medium_quality_count"],
            "Low Quality (<0.5)": stats["low_quality_count"],
        }

    def get_recent_questions(self, limit: int = 10) -> List[Dict]:
        """Get most recent questions with scores."""
        interactions = self.load_interactions()

        if not interactions:
            return []

        # Sort by timestamp descending
        sorted_interactions = sorted(
            interactions,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )

        recent = []
        for interaction in sorted_interactions[:limit]:
            recent.append({
                "question": interaction.get("question", "")[:100],
                "score": interaction["verification"]["overall_score"],
                "confidence": interaction["verification"].get("confidence", "unknown"),
                "timestamp": interaction.get("timestamp", ""),
            })

        return recent

    def get_phase_status(self) -> Dict:
        """Get RLVR phase completion status."""
        stats = self.get_basic_stats()
        total = stats["total_interactions"]

        # Phase 4 requires 500+ interactions
        phase_4_ready = total >= 500

        return {
            "phase_1_retrieval": {"complete": True, "status": "✅ Complete"},
            "phase_2_llm": {"complete": True, "status": "✅ Complete"},
            "phase_3_verification": {"complete": True, "status": "✅ Complete"},
            "phase_4_rl": {
                "complete": phase_4_ready,
                "status": "✅ Ready for Training" if phase_4_ready else f"⏳ Collecting Data ({total}/500)",
                "progress": min(100, (total / 500) * 100),
            },
        }

    def estimate_rl_readiness(self) -> Dict:
        """Estimate readiness for RL training."""
        stats = self.get_basic_stats()
        total = stats["total_interactions"]

        if total < 100:
            readiness = "Early Stage"
            recommendation = "Keep collecting data. Need 500+ interactions."
            color = "red"
        elif total < 300:
            readiness = "Developing"
            recommendation = "Good progress. Continue to collect diverse questions."
            color = "orange"
        elif total < 500:
            readiness = "Almost Ready"
            recommendation = f"Close to target! {500 - total} more interactions needed."
            color = "yellow"
        else:
            readiness = "Ready for Training"
            recommendation = "Sufficient data collected! You can start Phase 4 (RL training)."
            color = "green"

        return {
            "readiness": readiness,
            "recommendation": recommendation,
            "color": color,
            "total_interactions": total,
            "target": 500,
        }
