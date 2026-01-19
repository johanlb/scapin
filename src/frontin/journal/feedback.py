"""
Journal Feedback Processor

Converts journal corrections to Sganarelle UserFeedback and
triggers learning from user input.

Enhanced calibration features:
- Per-source accuracy tracking (Email/Teams/Calendar)
- Pattern learning from weekly reviews
- Automatic confidence threshold adjustment
- Batch processing for reviews
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from src.core.events.universal_event import now_utc
from src.frontin.journal.models import Correction, JournalEntry, JournalQuestion
from src.monitoring.logger import get_logger
from src.sganarelle.types import LearningResult, UserFeedback

if TYPE_CHECKING:
    from src.frontin.journal.reviews import DetectedPattern, WeeklyReview

logger = get_logger("frontin.journal.feedback")


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
# SOURCE CALIBRATION
# ============================================================================


@dataclass
class SourceCalibration:
    """
    Calibration data per source (Email, Teams, Calendar, OmniFocus)

    Tracks accuracy and confidence for automatic threshold adjustment.
    """
    source: str
    total_items: int = 0
    correct_decisions: int = 0
    incorrect_decisions: int = 0
    average_confidence: float = 0.0
    last_updated: datetime = field(default_factory=now_utc)

    @property
    def accuracy(self) -> float:
        """Calculate accuracy rate"""
        total = self.correct_decisions + self.incorrect_decisions
        return self.correct_decisions / total if total > 0 else 0.0

    @property
    def correction_rate(self) -> float:
        """Calculate correction rate (how often decisions are corrected)"""
        return 1.0 - self.accuracy

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "source": self.source,
            "total_items": self.total_items,
            "correct_decisions": self.correct_decisions,
            "incorrect_decisions": self.incorrect_decisions,
            "average_confidence": self.average_confidence,
            "accuracy": self.accuracy,
            "correction_rate": self.correction_rate,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class CalibrationAnalysis:
    """
    Analysis of calibration data for threshold adjustment

    Used to determine if confidence thresholds should be adjusted.
    """
    source_calibrations: dict[str, SourceCalibration] = field(default_factory=dict)
    overall_accuracy: float = 0.0
    recommended_threshold_adjustment: int = 0  # +/- percentage points
    patterns_learned: int = 0
    confidence_adjustments: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "source_calibrations": {
                k: v.to_dict() for k, v in self.source_calibrations.items()
            },
            "overall_accuracy": self.overall_accuracy,
            "recommended_threshold_adjustment": self.recommended_threshold_adjustment,
            "patterns_learned": self.patterns_learned,
            "confidence_adjustments": self.confidence_adjustments,
        }


@dataclass
class WeeklyReviewResult:
    """Result of processing a weekly review"""
    success: bool
    patterns_processed: int
    calibrations_updated: int
    threshold_adjustments: dict[str, int] = field(default_factory=dict)
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

    # =========================================================================
    # CALIBRATION METHODS
    # =========================================================================

    def process_weekly_review(self, review: "WeeklyReview") -> WeeklyReviewResult:
        """
        Process weekly review for calibration learning

        Analyzes patterns from the week and updates calibration data.

        Args:
            review: Weekly review with detected patterns

        Returns:
            WeeklyReviewResult with processing stats
        """
        logger.info(
            f"Processing weekly review {review.week_start} to {review.week_end}: "
            f"{len(review.patterns_detected)} patterns"
        )

        result = WeeklyReviewResult(
            success=True,
            patterns_processed=0,
            calibrations_updated=0,
        )

        # Process patterns
        for pattern in review.patterns_detected:
            try:
                self._learn_from_pattern(pattern)
                result.patterns_processed += 1
            except Exception as e:
                logger.error(f"Failed to process pattern: {e}")
                result.errors.append(f"Pattern {pattern.pattern_type}: {e}")

        # Update calibrations from daily entries
        for entry in review.daily_entries:
            try:
                self._update_source_calibrations(entry)
                result.calibrations_updated += 1
            except Exception as e:
                logger.debug(f"Failed to update calibration: {e}")

        # Calculate threshold adjustments
        analysis = self.analyze_calibration()
        if analysis.recommended_threshold_adjustment != 0:
            result.threshold_adjustments["global"] = analysis.recommended_threshold_adjustment

        # Store weekly calibration
        self._store_weekly_calibration(review, result)

        if result.errors:
            result.success = result.patterns_processed > 0

        logger.info(
            f"Weekly review processed: {result.patterns_processed} patterns, "
            f"{result.calibrations_updated} calibrations updated"
        )

        return result

    def calibrate_by_source(
        self,
        source: str,
        corrections: list[Correction],
    ) -> SourceCalibration:
        """
        Calculate calibration for a specific source

        Args:
            source: Source name (email, teams, calendar, omnifocus)
            corrections: List of corrections from that source

        Returns:
            SourceCalibration with accuracy stats
        """
        calibration = self._load_source_calibration(source)

        # Count corrections as incorrect decisions
        for _correction in corrections:
            calibration.incorrect_decisions += 1
            calibration.total_items += 1

        calibration.last_updated = now_utc()

        # Store updated calibration
        self._store_source_calibration(calibration)

        logger.debug(
            f"Source calibration {source}: accuracy={calibration.accuracy:.2%}, "
            f"total={calibration.total_items}"
        )

        return calibration

    def update_confidence_thresholds(
        self,
        analysis: CalibrationAnalysis,
    ) -> dict[str, int]:
        """
        Update confidence thresholds based on calibration analysis

        Args:
            analysis: CalibrationAnalysis with accuracy data

        Returns:
            Dict of threshold adjustments by source
        """
        adjustments = {}

        for source, calibration in analysis.source_calibrations.items():
            adjustment = self._calculate_threshold_adjustment(calibration)
            if adjustment != 0:
                adjustments[source] = adjustment

        # Store threshold adjustments
        if adjustments:
            self._store_threshold_adjustments(adjustments)
            logger.info(f"Threshold adjustments: {adjustments}")

        return adjustments

    def analyze_calibration(self) -> CalibrationAnalysis:
        """
        Analyze overall calibration across all sources

        Returns:
            CalibrationAnalysis with recommendations
        """
        sources = ["email", "teams", "calendar", "omnifocus"]
        source_calibrations = {}
        total_correct = 0
        total_incorrect = 0

        for source in sources:
            calibration = self._load_source_calibration(source)
            if calibration.total_items > 0:
                source_calibrations[source] = calibration
                total_correct += calibration.correct_decisions
                total_incorrect += calibration.incorrect_decisions

        total = total_correct + total_incorrect
        overall_accuracy = total_correct / total if total > 0 else 0.0

        # Calculate recommended adjustment
        recommended_adjustment = 0
        if overall_accuracy < 0.80:  # Below 80% accuracy
            recommended_adjustment = 5  # Increase threshold by 5%
        elif overall_accuracy > 0.95:  # Above 95% accuracy
            recommended_adjustment = -5  # Decrease threshold by 5%

        return CalibrationAnalysis(
            source_calibrations=source_calibrations,
            overall_accuracy=overall_accuracy,
            recommended_threshold_adjustment=recommended_adjustment,
        )

    def record_correct_decision(self, source: str) -> None:
        """Record a correct decision for calibration"""
        calibration = self._load_source_calibration(source)
        calibration.correct_decisions += 1
        calibration.total_items += 1
        calibration.last_updated = now_utc()
        self._store_source_calibration(calibration)

    def record_incorrect_decision(self, source: str) -> None:
        """Record an incorrect decision for calibration"""
        calibration = self._load_source_calibration(source)
        calibration.incorrect_decisions += 1
        calibration.total_items += 1
        calibration.last_updated = now_utc()
        self._store_source_calibration(calibration)

    # =========================================================================
    # PRIVATE CALIBRATION HELPERS
    # =========================================================================

    def _learn_from_pattern(self, pattern: "DetectedPattern") -> None:
        """Learn from a detected pattern"""
        pattern_file = self.storage_dir / "patterns.json"

        try:
            if pattern_file.exists():
                patterns = json.loads(pattern_file.read_text())
            else:
                patterns = {"patterns": [], "learned_at": []}

            # Store pattern
            patterns["patterns"].append({
                "type": pattern.pattern_type.value,
                "description": pattern.description,
                "frequency": pattern.frequency,
                "confidence": pattern.confidence,
                "examples": pattern.examples[:5],  # Limit examples
            })
            patterns["learned_at"].append(now_utc().isoformat())

            pattern_file.write_text(json.dumps(patterns, indent=2, ensure_ascii=False))
            logger.debug(f"Learned pattern: {pattern.pattern_type.value}")

        except Exception as e:
            logger.warning(f"Failed to store pattern: {e}")

    def _update_source_calibrations(self, entry: JournalEntry) -> None:
        """Update source calibrations from journal entry"""
        # Count email items
        if entry.emails_processed:
            email_cal = self._load_source_calibration("email")
            email_cal.total_items += len(entry.emails_processed)

            # Count corrections as incorrect
            email_corrections = [
                c for c in entry.corrections
                if c.email_id.startswith("email_") or "@" in c.email_id
            ]
            email_cal.incorrect_decisions += len(email_corrections)
            email_cal.correct_decisions += len(entry.emails_processed) - len(email_corrections)

            # Update confidence
            if entry.emails_processed:
                avg_conf = sum(e.confidence for e in entry.emails_processed) / len(entry.emails_processed)
                email_cal.average_confidence = (
                    email_cal.average_confidence * 0.9 + avg_conf * 0.1
                )

            email_cal.last_updated = now_utc()
            self._store_source_calibration(email_cal)

        # Count teams items
        if entry.teams_messages:
            teams_cal = self._load_source_calibration("teams")
            teams_cal.total_items += len(entry.teams_messages)
            teams_cal.last_updated = now_utc()
            self._store_source_calibration(teams_cal)

        # Count calendar items
        if entry.calendar_events:
            calendar_cal = self._load_source_calibration("calendar")
            calendar_cal.total_items += len(entry.calendar_events)
            calendar_cal.last_updated = now_utc()
            self._store_source_calibration(calendar_cal)

        # Count omnifocus items
        if entry.omnifocus_items:
            omnifocus_cal = self._load_source_calibration("omnifocus")
            omnifocus_cal.total_items += len(entry.omnifocus_items)
            omnifocus_cal.last_updated = now_utc()
            self._store_source_calibration(omnifocus_cal)

    def _load_source_calibration(self, source: str) -> SourceCalibration:
        """Load calibration data for a source"""
        cal_file = self.storage_dir / "calibration" / f"{source}.json"

        if cal_file.exists():
            try:
                data = json.loads(cal_file.read_text())
                return SourceCalibration(
                    source=data.get("source", source),
                    total_items=data.get("total_items", 0),
                    correct_decisions=data.get("correct_decisions", 0),
                    incorrect_decisions=data.get("incorrect_decisions", 0),
                    average_confidence=data.get("average_confidence", 0.0),
                    last_updated=datetime.fromisoformat(data["last_updated"])
                    if "last_updated" in data else now_utc(),
                )
            except Exception as e:
                logger.debug(f"Failed to load calibration for {source}: {e}")

        return SourceCalibration(source=source)

    def _store_source_calibration(self, calibration: SourceCalibration) -> None:
        """Store calibration data for a source"""
        cal_dir = self.storage_dir / "calibration"
        cal_dir.mkdir(parents=True, exist_ok=True)
        cal_file = cal_dir / f"{calibration.source}.json"

        try:
            cal_file.write_text(json.dumps(calibration.to_dict(), indent=2))
        except Exception as e:
            logger.warning(f"Failed to store calibration for {calibration.source}: {e}")

    def _calculate_threshold_adjustment(self, calibration: SourceCalibration) -> int:
        """Calculate threshold adjustment for a source"""
        if calibration.total_items < 10:
            return 0  # Not enough data

        if calibration.accuracy < 0.70:
            return 10  # Increase threshold significantly
        elif calibration.accuracy < 0.80:
            return 5  # Increase threshold
        elif calibration.accuracy > 0.95:
            return -5  # Decrease threshold
        return 0

    def _store_threshold_adjustments(self, adjustments: dict[str, int]) -> None:
        """Store threshold adjustments"""
        adj_file = self.storage_dir / "threshold_adjustments.json"

        try:
            data = json.loads(adj_file.read_text()) if adj_file.exists() else {"history": []}

            data["current"] = adjustments
            data["updated_at"] = now_utc().isoformat()
            data["history"].append({
                "adjustments": adjustments,
                "applied_at": now_utc().isoformat(),
            })

            # Keep only last 10 adjustments
            data["history"] = data["history"][-10:]

            adj_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to store threshold adjustments: {e}")

    def _store_weekly_calibration(
        self,
        review: "WeeklyReview",
        result: WeeklyReviewResult,
    ) -> None:
        """Store weekly calibration summary"""
        weekly_file = self.storage_dir / "weekly" / f"{review.week_start}.json"
        weekly_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = {
                "week_start": review.week_start.isoformat(),
                "week_end": review.week_end.isoformat(),
                "patterns_processed": result.patterns_processed,
                "calibrations_updated": result.calibrations_updated,
                "threshold_adjustments": result.threshold_adjustments,
                "productivity_score": review.productivity_score,
                "stored_at": now_utc().isoformat(),
            }
            weekly_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to store weekly calibration: {e}")


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
