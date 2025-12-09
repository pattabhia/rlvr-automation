"""
RLVR (Reinforcement Learning with Verifiable Rewards) Core Logic

This package contains the core domain logic for RLVR training:
- Multi-candidate answer generation
- Reward-based candidate selection
- Training data logging for DPO
"""

from .candidate_service import RLVRCandidateService
from .training_logger import RLVRTrainingLogger

__all__ = [
    "RLVRCandidateService",
    "RLVRTrainingLogger",
]
