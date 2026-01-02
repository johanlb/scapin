"""
Journal Feedback Processor

Converts journal corrections to Sganarelle UserFeedback and
triggers learning from user input.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.core.events.universal_event import now_utc
from src.jeeves.journal.models import Correction, JournalEntry, JournalQuestion
from src.monitoring.logger import get_logger
from src.sganarelle.types import LearningResult, UserFeedback

logger = get_logger("jeeves.journal.feedback")


# ============================================================================
# STORED FEEDBACK
# ============================================================================


@dataclass
class StoredFeedback:
    """
    Feedback stored for later learning

    When we don't have the original event/working_memory available,
    we store the feedback for batch processing later.
    """
    feedback_id: str
    email_id: str
    correction: Correction
    question_answers: dict[str, str]  # question_id -> answer
    created_at: datetime
    processed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "feedback_id": self.feedback_id,
            "email_id": self.email_id,
            "correction": self.correction.to_dict(),
            "question_answers": self.question_answers,
            "created_at": self.created_at.isoformat(),
            "processed": self.processed,
        }


# ============================================================================
# FEEDBACK RESULT
# ============================================================================


@dataclass
class FeedbackProcessingResult:
    """Result of processing journal feedback"""
    success: bool
    corrections_processed: int
    answers_processed: int
    stored_for_later: int
    learning_results: list[LearningResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ============================================================================
# FEEDBACK PROCESSOR
# ============================================================================


class JournalFeedbackProcessor:
    """
    Processes journal feedback for Sganarelle learning

    Converts corrections and question answers to UserFeedback,
    and triggers learning when possible.

    If the original event data is not available, feedback is stored
    for batch processing later.

    Example:
        >>> processor = JournalFeedbackProcessor()
        >>> result = processor.process(completed_journal)
        >>> print(f"Processed {result.corrections_processed} corrections")
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        learning_engine: Optional[Any] = None,  # Avoid circular import
    ):
        """
        Initialize feedback processor

        Args:
            storage_dir: Directory for storing pending feedback
            learning_engine: Optional LearningEngine for direct learning
        """
        self.storage_dir = storage_dir or Path("data/feedback")
        self.learning_engine = learning_engine

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def process(self, entry: JournalEntry) -> FeedbackProcessingResult:
        """
        Process all feedback from a journal entry

        Args:
            entry: Completed journal entry with corrections and answers

        Returns:
            FeedbackProcessingResult with processing stats
        """
        logger.info(
            f"Processing feedback from journal {entry.journal_date}: "
            f"{len(entry.corrections)} corrections, "
            f"{len(entry.answered_questions)} answers"
        )

        result = FeedbackProcessingResult(
            success=True,
            corrections_processed=0,
            answers_processed=0,
            stored_for_later=0,
        )

        # Process corrections
        for correction in entry.corrections:
            try:
                self._process_correction(correction, result)
            except Exception as e:
                logger.error(f"Failed to process correction: {e}")
                result.errors.append(f"Correction {correction.email_id}: {e}")

        # Process question answers
        for question in entry.answered_questions:
            try:
                self._process_answer(question, result)
            except Exception as e:
                logger.error(f"Failed to process answer: {e}")
                result.errors.append(f"Question {question.question_id}: {e}")

        # Store for batch processing
        self._store_entry_feedback(entry)

        if result.errors:
            result.success = len(result.errors) < len(entry.corrections) + len(entry.answered_questions)

        logger.info(
            f"Feedback processing complete: "
            f"{result.corrections_processed} corrections, "
            f"{result.answers_processed} answers, "
            f"{len(result.errors)} errors"
        )

        return result

    def _process_correction(
        self,
        correction: Correction,
        result: FeedbackProcessingResult,
    ) -> None:
        """Process a single correction"""
        # Convert correction to UserFeedback
        feedback = self._correction_to_feedback(correction)

        # If we have learning engine and can get original data, learn immediately
        if self.learning_engine:
            try:
                learning_result = self._try_immediate_learning(correction, feedback)
                if learning_result:
                    result.learning_results.append(learning_result)
                    result.corrections_processed += 1
                    return
            except Exception as e:
                logger.debug(f"Immediate learning failed, storing: {e}")

        # Store for later
        result.stored_for_later += 1
        result.corrections_processed += 1

    def _process_answer(
        self,
        question: JournalQuestion,
        result: FeedbackProcessingResult,
    ) -> None:
        """Process a single question answer"""
        # Different handling based on question type
        if question.category.value == "new_person" and question.related_entity:
            # Store entity classification
            self._store_entity_classification(
                question.related_entity,
                question.answer or "",
            )

        result.answers_processed += 1

    def _correction_to_feedback(self, correction: Correction) -> UserFeedback:
        """Convert Correction to UserFeedback for Sganarelle"""
        # Build correction string
        correction_parts = []
        if correction.has_action_correction:
            correction_parts.append(
                f"Action: {correction.original_action} -> {correction.corrected_action}"
            )
        if correction.has_category_correction:
            correction_parts.append(
                f"Category: {correction.original_category} -> {correction.corrected_category}"
            )

        correction_str = "; ".join(correction_parts)

        return UserFeedback(
            approval=False,  # Correction means the original was wrong
            rating=2,  # Low rating for incorrect decisions
            comment=correction.reason,
            correction=correction_str,
            action_executed=False,  # We're correcting, so not executed as-is
            time_to_action=0.0,
        )

    def _try_immediate_learning(
        self,
        correction: Correction,
        feedback: UserFeedback,
    ) -> Optional[LearningResult]:
        """Try to learn immediately if we have original event data"""
        # Try to get original event from storage
        event = self._get_stored_event(correction.email_id)
        if not event:
            return None

        # Try to get working memory
        working_memory = self._get_stored_working_memory(correction.email_id)
        if not working_memory:
            return None

        # Learn
        return self.learning_engine.learn(
            event=event,
            working_memory=working_memory,
            actions=[],  # No actions at correction stage
            execution_success=False,  # Correction means it was wrong
            user_feedback=feedback,
        )

    def _get_stored_event(self, email_id: str) -> Optional[Any]:
        """Get stored PerceivedEvent for email ID"""
        event_file = self.storage_dir.parent / "events" / f"{email_id}.json"
        if not event_file.exists():
            return None

        try:
            # We would need to deserialize PerceivedEvent here
            # For now, return None to trigger storage path
            return None
        except Exception:
            return None

    def _get_stored_working_memory(self, email_id: str) -> Optional[Any]:
        """Get stored WorkingMemory for email ID"""
        wm_file = self.storage_dir.parent / "working_memory" / f"{email_id}.json"
        if not wm_file.exists():
            return None

        try:
            # We would need to deserialize WorkingMemory here
            # For now, return None to trigger storage path
            return None
        except Exception:
            return None

    def _store_entity_classification(self, entity: str, classification: str) -> None:
        """Store entity classification for future reference"""
        entity_file = self.storage_dir.parent / "entities.json"

        try:
            if entity_file.exists():
                data = json.loads(entity_file.read_text())
            else:
                data = {"known_emails": [], "classifications": {}}

            # Add to known emails
            if entity.lower() not in [e.lower() for e in data.get("known_emails", [])]:
                data.setdefault("known_emails", []).append(entity)

            # Store classification
            data.setdefault("classifications", {})[entity.lower()] = classification

            entity_file.parent.mkdir(parents=True, exist_ok=True)
            entity_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

            logger.debug(f"Stored entity classification: {entity} -> {classification}")

        except Exception as e:
            logger.warning(f"Failed to store entity classification: {e}")

    def _store_entry_feedback(self, entry: JournalEntry) -> None:
        """Store entry feedback for batch processing"""
        feedback_file = self.storage_dir / f"journal_{entry.journal_date}.json"

        try:
            data = {
                "entry_id": entry.entry_id,
                "journal_date": entry.journal_date.isoformat(),
                "corrections": [c.to_dict() for c in entry.corrections],
                "answers": [
                    {
                        "question_id": q.question_id,
                        "category": q.category.value,
                        "answer": q.answer,
                        "related_email_id": q.related_email_id,
                        "related_entity": q.related_entity,
                    }
                    for q in entry.answered_questions
                ],
                "stored_at": now_utc().isoformat(),
            }

            feedback_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            logger.debug(f"Stored journal feedback: {feedback_file}")

        except Exception as e:
            logger.warning(f"Failed to store journal feedback: {e}")


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================


def process_corrections(entry: JournalEntry) -> FeedbackProcessingResult:
    """
    Convenience function to process corrections from a journal entry

    Args:
        entry: Completed journal entry

    Returns:
        FeedbackProcessingResult with processing stats
    """
    processor = JournalFeedbackProcessor()
    return processor.process(entry)
