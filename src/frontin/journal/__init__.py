"""
Journal Module

Daily journaling with feedback loop to Sganarelle.
Multi-source support: Email, Teams, Calendar, OmniFocus.
Weekly and monthly reviews with pattern detection.

Workflow:
1. `scapin journal` command
2. JournalGenerator creates draft from day's processing
3. JournalInteractive collects user answers and corrections
4. FeedbackProcessor sends corrections to Sganarelle
5. ReviewGenerator creates weekly/monthly summaries

Example:
    >>> from src.frontin.journal import JournalGenerator, JournalInteractive
    >>> generator = JournalGenerator()
    >>> entry = generator.generate(date.today())
    >>> interactive = JournalInteractive(entry)
    >>> completed_entry = interactive.run()
"""

from src.frontin.journal.feedback import (
    CalibrationAnalysis,
    FeedbackProcessingResult,
    JournalFeedbackProcessor,
    SourceCalibration,
    WeeklyReviewResult,
    process_corrections,
)
from src.frontin.journal.generator import (
    JournalGenerator,
    JournalGeneratorConfig,
)
from src.frontin.journal.interactive import JournalInteractive
from src.frontin.journal.models import (
    CalendarSummary,
    Correction,
    DecisionSummary,
    EmailSummary,
    JournalEntry,
    JournalQuestion,
    JournalStatus,
    OmniFocusSummary,
    QuestionCategory,
    TaskSummary,
    TeamsSummary,
)
from src.frontin.journal.reviews import (
    DetectedPattern,
    MonthlyReview,
    PatternType,
    ReviewGenerator,
    ReviewGeneratorConfig,
    ReviewType,
    WeeklyReview,
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
    # Multi-source models
    "TeamsSummary",
    "CalendarSummary",
    "OmniFocusSummary",
    # Generator
    "JournalGenerator",
    "JournalGeneratorConfig",
    # Interactive
    "JournalInteractive",
    # Feedback
    "JournalFeedbackProcessor",
    "FeedbackProcessingResult",
    "process_corrections",
    # Calibration
    "SourceCalibration",
    "CalibrationAnalysis",
    "WeeklyReviewResult",
    # Reviews
    "ReviewGenerator",
    "ReviewGeneratorConfig",
    "ReviewType",
    "WeeklyReview",
    "MonthlyReview",
    "DetectedPattern",
    "PatternType",
]
