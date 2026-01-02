"""
Email Processing Components

Modular components for email validation, preparation, analysis, and execution.
"""

from src.core.processors.action_executor import ActionExecutor, ExecutionResult
from src.core.processors.content_preparator import ContentPreparator
from src.core.processors.email_analyzer import EmailAnalyzer
from src.core.processors.email_validator import EmailValidator

__all__ = [
    "EmailValidator",
    "ContentPreparator",
    "EmailAnalyzer",
    "ActionExecutor",
    "ExecutionResult",
]
