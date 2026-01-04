"""
Journal API Service

Business logic for journal API endpoints.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from src.jeeves.journal import (
    CalibrationAnalysis,
    JournalEntry,
    JournalFeedbackProcessor,
    JournalGenerator,
    JournalGeneratorConfig,
    ReviewGenerator,
    ReviewGeneratorConfig,
)
from src.jeeves.journal.models import Correction
from src.monitoring.logger import get_logger

logger = get_logger("jeeves.api.services.journal")


class JournalService:
    """
    Service for journal API operations

    Handles journal generation, retrieval, and feedback processing.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        generator_config: Optional[JournalGeneratorConfig] = None,
        review_config: Optional[ReviewGeneratorConfig] = None,
    ):
        """
        Initialize journal service

        Args:
            data_dir: Directory for journal data storage
            generator_config: Configuration for journal generation
            review_config: Configuration for review generation
        """
        self.data_dir = data_dir or Path("data")
        self.generator = JournalGenerator(config=generator_config)
        self.review_generator = ReviewGenerator(config=review_config)
        self.feedback_processor = JournalFeedbackProcessor(
            storage_dir=self.data_dir / "feedback"
        )
        self._journal_cache: dict[date, JournalEntry] = {}

    async def get_journal(self, target_date: date) -> Optional[JournalEntry]:
        """
        Get journal entry for a date

        Args:
            target_date: Date to get journal for

        Returns:
            JournalEntry if exists, None otherwise
        """
        # Check cache
        if target_date in self._journal_cache:
            return self._journal_cache[target_date]

        # Try to load from storage
        entry = self._load_journal(target_date)
        if entry:
            self._journal_cache[target_date] = entry
            return entry

        return None

    async def generate_journal(self, target_date: date) -> JournalEntry:
        """
        Generate journal entry for a date

        Args:
            target_date: Date to generate journal for

        Returns:
            Generated JournalEntry
        """
        logger.info(f"Generating journal for {target_date}")
        entry = self.generator.generate(target_date)
        self._journal_cache[target_date] = entry
        self._save_journal(entry)
        return entry

    async def get_or_generate_journal(self, target_date: date) -> JournalEntry:
        """
        Get existing journal or generate new one

        Args:
            target_date: Date for journal

        Returns:
            JournalEntry (existing or newly generated)
        """
        existing = await self.get_journal(target_date)
        if existing:
            return existing
        return await self.generate_journal(target_date)

    async def list_journals(
        self,
        page: int = 1,
        page_size: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> tuple[list[JournalEntry], int]:
        """
        List journal entries with pagination

        Args:
            page: Page number (1-based)
            page_size: Items per page
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            Tuple of (entries, total_count)
        """
        # List journal files
        journal_dir = self.data_dir / "journals"
        if not journal_dir.exists():
            return [], 0

        entries = []
        for file in sorted(journal_dir.glob("*.json"), reverse=True):
            try:
                entry = self._load_journal_from_file(file)
                if entry:
                    # Apply date filters
                    if start_date and entry.journal_date < start_date:
                        continue
                    if end_date and entry.journal_date > end_date:
                        continue
                    entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to load journal {file}: {e}")

        # Paginate
        total = len(entries)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return entries[start_idx:end_idx], total

    async def answer_question(
        self,
        target_date: date,
        question_id: str,
        answer: str,
    ) -> JournalEntry:
        """
        Answer a journal question

        Args:
            target_date: Date of journal
            question_id: Question to answer
            answer: User's answer

        Returns:
            Updated JournalEntry
        """
        entry = await self.get_or_generate_journal(target_date)
        entry.answer_question(question_id, answer)
        self._save_journal(entry)
        return entry

    async def submit_correction(
        self,
        target_date: date,
        email_id: str,
        corrected_action: Optional[str] = None,
        corrected_category: Optional[str] = None,
        reason: Optional[str] = None,
        confidence_override: Optional[int] = None,
    ) -> JournalEntry:
        """
        Submit a correction for an email decision

        Args:
            target_date: Date of journal
            email_id: Email being corrected
            corrected_action: New action
            corrected_category: New category
            reason: Reason for correction
            confidence_override: Override confidence

        Returns:
            Updated JournalEntry
        """
        entry = await self.get_or_generate_journal(target_date)

        # Find original email
        original_email = next(
            (e for e in entry.emails_processed if e.email_id == email_id),
            None
        )
        if not original_email:
            raise ValueError(f"Email {email_id} not found in journal")

        # Create correction
        correction = Correction(
            email_id=email_id,
            original_action=original_email.action,
            corrected_action=corrected_action,
            original_category=original_email.category,
            corrected_category=corrected_category,
            reason=reason,
            confidence_override=confidence_override,
        )

        entry.add_correction(correction)
        self._save_journal(entry)

        # Process feedback
        self.feedback_processor.record_incorrect_decision("email")

        return entry

    async def complete_journal(self, target_date: date) -> JournalEntry:
        """
        Mark journal as completed

        Args:
            target_date: Date of journal

        Returns:
            Completed JournalEntry
        """
        entry = await self.get_or_generate_journal(target_date)
        entry.complete()
        self._save_journal(entry)

        # Process all feedback
        self.feedback_processor.process(entry)

        return entry

    async def get_weekly_review(self, week_start: date) -> dict:
        """
        Generate weekly review

        Args:
            week_start: First day of the week

        Returns:
            WeeklyReview as dict
        """
        # Collect daily entries
        entries = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            entry = await self.get_journal(day)
            if entry:
                entries.append(entry)

        review = self.review_generator.generate_weekly(week_start, entries)
        return review.to_dict()

    async def get_monthly_review(self, month: date) -> dict:
        """
        Generate monthly review

        Args:
            month: First day of the month

        Returns:
            MonthlyReview as dict
        """
        # Generate weekly reviews for the month
        weekly_reviews = []
        current = month
        while current.month == month.month:
            # Get Monday of this week
            monday = current - timedelta(days=current.weekday())

            # Collect entries for this week
            entries = []
            for i in range(7):
                day = monday + timedelta(days=i)
                if day.month == month.month:
                    entry = await self.get_journal(day)
                    if entry:
                        entries.append(entry)

            if entries:
                weekly = self.review_generator.generate_weekly(monday, entries)
                weekly_reviews.append(weekly)

            current += timedelta(days=7)

        review = self.review_generator.generate_monthly(month, weekly_reviews)
        return review.to_dict()

    async def get_calibration(self) -> CalibrationAnalysis:
        """
        Get current calibration analysis

        Returns:
            CalibrationAnalysis with accuracy data
        """
        return self.feedback_processor.analyze_calibration()

    async def export_journal(
        self,
        target_date: date,
        format: str = "markdown",
        include_questions: bool = True,  # noqa: ARG002
        include_corrections: bool = True,  # noqa: ARG002
    ) -> str:
        """
        Export journal in specified format

        Args:
            target_date: Date of journal
            format: Export format (markdown, json, html)
            include_questions: Include questions in export
            include_corrections: Include corrections in export

        Returns:
            Exported content as string
        """
        entry = await self.get_or_generate_journal(target_date)

        if format == "json":
            return entry.to_json()
        elif format == "markdown":
            return entry.to_markdown()
        elif format == "html":
            # Convert markdown to basic HTML
            md = entry.to_markdown()
            return f"<html><body><pre>{md}</pre></body></html>"
        else:
            raise ValueError(f"Unsupported format: {format}")

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _load_journal(self, target_date: date) -> Optional[JournalEntry]:
        """Load journal from storage"""
        journal_file = self.data_dir / "journals" / f"{target_date}.json"
        return self._load_journal_from_file(journal_file)

    def _load_journal_from_file(self, path: Path) -> Optional[JournalEntry]:
        """Load journal from file"""
        if not path.exists():
            return None

        try:
            import json
            data = json.loads(path.read_text())
            return JournalEntry.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load journal from {path}: {e}")
            return None

    def _save_journal(self, entry: JournalEntry) -> None:
        """Save journal to storage"""
        journal_dir = self.data_dir / "journals"
        journal_dir.mkdir(parents=True, exist_ok=True)

        journal_file = journal_dir / f"{entry.journal_date}.json"

        try:
            import json
            journal_file.write_text(json.dumps(entry.to_dict(), indent=2))
        except Exception as e:
            logger.warning(f"Failed to save journal: {e}")
