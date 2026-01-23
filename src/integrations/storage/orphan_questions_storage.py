"""
Orphan Questions Storage

Stores strategic questions that have no target note (orphaned questions).
These questions appear in the morning briefing for user attention.

Architecture:
    - Single JSON file for all orphan questions
    - Path: data/orphan_questions.json
    - Thread-safe operations
"""

import json
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.monitoring.logger import get_logger
from src.utils import get_data_dir

logger = get_logger("orphan_questions_storage")


@dataclass
class OrphanQuestion:
    """A strategic question without a target note"""

    question_id: str
    question: str
    category: str  # decision, processus, organisation, structure_pkm
    context: str
    source_valet: str  # grimaud, bazin, planchet, mousqueton
    source_email_subject: str
    source_item_id: str  # Queue item ID that generated this question
    created_at: str  # ISO timestamp
    intended_target: Optional[str] = None  # Note that was intended but not found
    resolved: bool = False
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None


class OrphanQuestionsStorage:
    """
    JSON-based storage for orphan strategic questions.

    Orphan questions are strategic questions generated during email analysis
    that don't have a target note to attach to.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize orphan questions storage.

        Args:
            storage_path: Path to storage file (default: data/orphan_questions.json)
        """
        self.storage_path = (
            Path(storage_path)
            if storage_path
            else get_data_dir() / "orphan_questions.json"
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self._lock = threading.Lock()

        # Ensure file exists
        if not self.storage_path.exists():
            self._save_questions([])

        logger.info(
            "OrphanQuestionsStorage initialized",
            extra={"storage_path": str(self.storage_path)},
        )

    def _load_questions(self) -> list[dict[str, Any]]:
        """Load questions from storage file."""
        try:
            with self.storage_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_questions(self, questions: list[dict[str, Any]]) -> None:
        """Save questions to storage file."""
        with self.storage_path.open("w", encoding="utf-8") as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

    def add_question(
        self,
        question: str,
        category: str,
        context: str,
        source_valet: str,
        source_email_subject: str,
        source_item_id: str,
        intended_target: Optional[str] = None,
    ) -> OrphanQuestion:
        """
        Add an orphan question to storage.

        Args:
            question: The question text
            category: Question category
            context: Context explaining the question
            source_valet: Which valet generated the question
            source_email_subject: Subject of the source email
            source_item_id: ID of the queue item
            intended_target: Note ID that was intended but not found

        Returns:
            The created OrphanQuestion
        """
        question_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        orphan = OrphanQuestion(
            question_id=question_id,
            question=question,
            category=category,
            context=context,
            source_valet=source_valet,
            source_email_subject=source_email_subject,
            source_item_id=source_item_id,
            created_at=now,
            intended_target=intended_target,
        )

        with self._lock:
            questions = self._load_questions()
            questions.append(asdict(orphan))
            self._save_questions(questions)

        logger.info(
            "Added orphan question",
            extra={
                "question_id": question_id,
                "question": question[:50],
                "category": category,
            },
        )

        return orphan

    def get_pending_questions(self) -> list[OrphanQuestion]:
        """Get all unresolved orphan questions."""
        with self._lock:
            questions = self._load_questions()

        pending = [
            OrphanQuestion(**q)
            for q in questions
            if not q.get("resolved", False)
        ]

        return pending

    def get_all_questions(self) -> list[OrphanQuestion]:
        """Get all orphan questions (including resolved)."""
        with self._lock:
            questions = self._load_questions()

        return [OrphanQuestion(**q) for q in questions]

    def resolve_question(
        self,
        question_id: str,
        resolution: str = "",
    ) -> bool:
        """
        Mark an orphan question as resolved.

        Args:
            question_id: ID of the question to resolve
            resolution: Optional resolution text

        Returns:
            True if question was found and resolved
        """
        with self._lock:
            questions = self._load_questions()

            for q in questions:
                if q.get("question_id") == question_id:
                    q["resolved"] = True
                    q["resolved_at"] = datetime.now(timezone.utc).isoformat()
                    q["resolution"] = resolution
                    self._save_questions(questions)

                    logger.info(
                        "Resolved orphan question",
                        extra={"question_id": question_id},
                    )
                    return True

        logger.warning(
            "Orphan question not found for resolution",
            extra={"question_id": question_id},
        )
        return False

    def delete_question(self, question_id: str) -> bool:
        """
        Delete an orphan question.

        Args:
            question_id: ID of the question to delete

        Returns:
            True if question was found and deleted
        """
        with self._lock:
            questions = self._load_questions()
            original_count = len(questions)
            questions = [q for q in questions if q.get("question_id") != question_id]

            if len(questions) < original_count:
                self._save_questions(questions)
                logger.info(
                    "Deleted orphan question",
                    extra={"question_id": question_id},
                )
                return True

        return False

    def clear_resolved(self) -> int:
        """
        Remove all resolved questions from storage.

        Returns:
            Number of questions removed
        """
        with self._lock:
            questions = self._load_questions()
            original_count = len(questions)
            questions = [q for q in questions if not q.get("resolved", False)]
            removed_count = original_count - len(questions)

            if removed_count > 0:
                self._save_questions(questions)
                logger.info(
                    f"Cleared {removed_count} resolved orphan questions",
                )

        return removed_count


# Singleton instance
_instance: Optional[OrphanQuestionsStorage] = None
_instance_lock = threading.Lock()


def get_orphan_questions_storage() -> OrphanQuestionsStorage:
    """Get singleton instance of OrphanQuestionsStorage."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = OrphanQuestionsStorage()
    return _instance
