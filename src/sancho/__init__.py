"""
Sancho - Reasoning Module

The wisdom and reasoning component of Scapin's cognitive architecture.

Named after Sancho Panza from Don Quixote - the wise, pragmatic companion
who provides grounded reasoning and sound judgment.

Sancho performs iterative multi-pass reasoning to achieve high-confidence
decisions through:
- Initial quick analysis
- Context enrichment from knowledge base
- Deep multi-step reasoning
- Cross-provider validation
- User clarification when needed
"""

from src.sancho.reasoning_engine import ReasoningEngine, ReasoningResult

__all__ = [
    "ReasoningEngine",
    "ReasoningResult",
]
