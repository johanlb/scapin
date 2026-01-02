"""
Memory Module

Central memory systems for the cognitive architecture:
- Working Memory: Short-term understanding and reasoning state
- Continuity Detector: Detects conversation threads and context continuity
"""

from src.core.memory.continuity_detector import (
    ContinuityDetector,
    ContinuityScore,
)
from src.core.memory.working_memory import (
    ContextItem,
    Hypothesis,
    MemoryState,
    ReasoningPass,
    WorkingMemory,
)

__all__ = [
    "WorkingMemory",
    "MemoryState",
    "Hypothesis",
    "ReasoningPass",
    "ContextItem",
    "ContinuityDetector",
    "ContinuityScore",
]
