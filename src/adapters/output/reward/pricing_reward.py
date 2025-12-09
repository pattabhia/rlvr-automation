"""
Pricing Reward Adapter - RLVR reward computation for pricing questions.

This adapter implements the reward function described in the RLVR feedback document.
It computes a numeric reward (0.0 to 1.0) based on price range overlap with ground truth.
"""

import re
from typing import Optional, Tuple

from src.config.ground_truth import TAJ_PRICE_TRUTH
from src.config.ground_truth.taj_hotels_pricing import TAJ_HOTEL_ALIASES
from src.logging import get_logger
from src.ports.output.reward import RewardPort

logger = get_logger(__name__)


class PricingRewardAdapter(RewardPort):
    """
    Pricing reward adapter for Taj Hotels use case.

    Computes reward based on:
    1. Identifying which hotel is mentioned
    2. Extracting price range from answer
    3. Computing overlap with ground truth price range
    4. Returning IoU (Intersection over Union) score
    """

    def __init__(self):
        self.price_truth = TAJ_PRICE_TRUTH
        self.hotel_aliases = TAJ_HOTEL_ALIASES

    def compute_reward(self, question: str, answer: str) -> float:
        """
        Compute pricing reward for an answer.

        Args:
            question: User's question (used to identify hotel)
            answer: Generated answer containing price information

        Returns:
            Reward score between 0.0 and 1.0
        """
        # Step 1: Identify which hotel is being asked about
        hotel_key = self._normalize_hotel_name(question + " " + answer)
        if hotel_key is None:
            logger.debug("No hotel identified in question/answer")
            return 0.0

        # Step 2: Get ground truth for this hotel
        truth = self.price_truth[hotel_key]

        # Step 3: Extract predicted price range from answer
        pred_range = self._extract_price_range(answer)
        if pred_range is None:
            logger.debug(f"Could not extract price range from answer: {answer[:100]}")
            return 0.0

        # Step 4: Compute overlap reward
        reward = self._range_overlap_reward(pred_range, (truth["min"], truth["max"]))

        logger.info(
            f"RLVR Reward: hotel={hotel_key}, "
            f"predicted={pred_range}, "
            f"truth=({truth['min']}, {truth['max']}), "
            f"reward={reward:.3f}"
        )

        return reward

    def _normalize_hotel_name(self, text: str) -> Optional[str]:
        """
        Extract hotel name from text.

        Args:
            text: Question + answer text

        Returns:
            Normalized hotel key from TAJ_PRICE_TRUTH, or None if not found
        """
        text_lower = text.lower()

        # Try aliases first (more specific)
        for alias, canonical in self.hotel_aliases.items():
            if alias in text_lower:
                return canonical

        # Try exact keys
        for key in self.price_truth.keys():
            if key in text_lower:
                return key

        return None

    def _extract_price_range(self, answer: str) -> Optional[Tuple[int, int]]:
        """
        Extract price range from answer text.

        Looks for patterns like:
        - ₹24,000 – ₹65,000
        - Rs 24000 to Rs 65000
        - 24,000 - 65,000

        Args:
            answer: Answer text containing price information

        Returns:
            Tuple of (min_price, max_price) or None if not found
        """
        # Pattern to match Indian currency numbers
        # Handles: ₹24,000 or 24000 or Rs 24,000
        nums = re.findall(r'[₹Rs.\s]*([\d,]+)', answer)

        if len(nums) < 2:
            return None

        # Parse numbers (remove commas)
        vals = []
        for n in nums:
            try:
                val = int(n.replace(",", ""))
                # Filter reasonable hotel prices (1000 to 500000)
                if 1000 <= val <= 500000:
                    vals.append(val)
            except ValueError:
                continue

        if len(vals) < 2:
            return None

        # Return min and max
        return min(vals), max(vals)

    def _range_overlap_reward(
        self,
        pred_range: Optional[Tuple[int, int]],
        truth_range: Tuple[int, int]
    ) -> float:
        """
        Compute IoU (Intersection over Union) reward for price ranges.

        Args:
            pred_range: Predicted (min, max) price range
            truth_range: Ground truth (min, max) price range

        Returns:
            IoU score between 0.0 and 1.0
        """
        if pred_range is None:
            return 0.0

        pmin, pmax = pred_range
        tmin, tmax = truth_range

        # Compute intersection
        overlap_min = max(pmin, tmin)
        overlap_max = min(pmax, tmax)

        if overlap_min >= overlap_max:
            # No overlap
            return 0.0

        # Compute IoU (Intersection over Union)
        overlap = overlap_max - overlap_min
        union = max(pmax, tmax) - min(pmin, tmin)

        if union <= 0:
            return 0.0

        iou = overlap / union

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, iou))
