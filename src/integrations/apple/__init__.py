"""
Apple Integrations Module

Provides integrations with Apple applications on macOS:
- OmniFocus for task management
- Apple Notes for note synchronization
"""

from src.integrations.apple.omnifocus_client import OmniFocusClient
from src.integrations.apple.omnifocus_models import (
    OmniFocusDailyStats,
    OmniFocusProject,
    OmniFocusTask,
    ProjectStatus,
    TaskStatus,
)
from src.integrations.apple.omnifocus_normalizer import OmniFocusNormalizer

__all__ = [
    "OmniFocusClient",
    "OmniFocusTask",
    "OmniFocusProject",
    "OmniFocusDailyStats",
    "TaskStatus",
    "ProjectStatus",
    "OmniFocusNormalizer",
]
