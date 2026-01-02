"""
Journal Module

Daily journaling with feedback loop to Sganarelle.

Workflow:
1. `scapin journal` command
2. JournalGenerator creates draft from day's processing
3. JournalInteractive collects user answers and corrections
4. FeedbackProcessor sends corrections to Sganarelle

Example:
    >>> from src.jeeves.journal import JournalGenerator, JournalInteractive
    >>> generator = JournalGenerator()
    >>> entry = generator.generate(date.today())
    >>> interactive = JournalInteractive(entry)
    >>> completed_entry = interactive.run()
"""

from src.jeeves.journal.feedback import (
    FeedbackProcessingResult,
    JournalFeedbackProcessor,
    process_corrections,
)
from src.jeeves.journal.generator import (
    JournalGenerator,
    JournalGeneratorConfig,
)
from src.jeeves.journal.interactive import JournalInteractive
from src.jeeves.journal.models import (
    Correction,
    DecisionSummary,
    EmailSummary,
    JournalEntry,
    JournalQuestion,
    JournalStatus,
    QuestionCategory,
    TaskSummary,
)

__all__ = [
    # Models
    "JournalEntry",
    "JournalQuestion",
    "JournalStatus",
    "QuestionCategory",
    "EmailSummary",
    "TaskSummary",
    "DecisionSummary",
    "Correction",
    # Generator
    "JournalGenerator",
    "JournalGeneratorConfig",
    # Interactive
    "JournalInteractive",
    # Feedback
    "JournalFeedbackProcessor",
    "FeedbackProcessingResult",
    "process_corrections",
]
