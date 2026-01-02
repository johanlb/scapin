"""
Figaro - Action Execution Module

Orchestrates action execution with DAG-based dependencies and rollback support.
Named after the clever servant in Beaumarchais' plays who orchestrates complex plans.
"""

from src.figaro.actions.base import Action, ActionResult, ExecutionMode, ValidationResult
from src.figaro.orchestrator import ActionOrchestrator, ExecutionResult

__all__ = [
    "Action",
    "ActionResult",
    "ExecutionMode",
    "ValidationResult",
    "ActionOrchestrator",
    "ExecutionResult"
]

__version__ = "1.0.0"
