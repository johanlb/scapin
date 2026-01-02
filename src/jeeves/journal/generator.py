"""
Journal Generator

Generates daily journal entries from processing history.
Retrieves emails processed, tasks created, and identifies
questions to ask the user based on confidence levels.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional, Protocol

from src.core.events.universal_event import now_utc
from src.jeeves.journal.models import (
    DecisionSummary,
    EmailSummary,
    JournalEntry,
    JournalQuestion,
    JournalStatus,
    QuestionCategory,
    TaskSummary,
)
from src.monitoring.logger import get_logger

logger = get_logger("jeeves.journal.generator")


# ============================================================================
# DATA PROVIDER PROTOCOL
# ============================================================================


class ProcessingHistoryProvider(Protocol):
    """
    Protocol for providing processing history data

    Implementations can fetch from:
    - State manager (in-memory)
    - Database (SQLite/Postgres)
    - Log files
    - JSON files
    """

    def get_processed_emails(self, target_date: date) -> list[dict[str, Any]]:
        """Get emails processed on the target date"""
        ...

    def get_created_tasks(self, target_date: date) -> list[dict[str, Any]]:
        """Get tasks created on the target date"""
        ...

    def get_decisions(self, target_date: date) -> list[dict[str, Any]]:
        """Get automated decisions on the target date"""
        ...

    def get_known_entities(self) -> set[str]:
        """Get set of known entity identifiers (emails, names)"""
        ...


# ============================================================================
# DEFAULT DATA PROVIDER (JSON FILE)
# ============================================================================


@dataclass
class JsonFileHistoryProvider:
    """
    Provides processing history from JSON log files

    Reads from daily processing logs stored in data directory.
    Format: data/logs/processing_YYYY-MM-DD.json
    """
    data_dir: Path = field(default_factory=lambda: Path("data"))

    def get_processed_emails(self, target_date: date) -> list[dict[str, Any]]:
        """Get emails processed on the target date"""
        log_file = self._get_log_file(target_date)
        if not log_file.exists():
            logger.debug(f"No processing log found for {target_date}")
            return []

        try:
            data = json.loads(log_file.read_text())
            return data.get("emails", [])
        except Exception as e:
            logger.warning(f"Failed to read processing log: {e}")
            return []

    def get_created_tasks(self, target_date: date) -> list[dict[str, Any]]:
        """Get tasks created on the target date"""
        log_file = self._get_log_file(target_date)
        if not log_file.exists():
            return []

        try:
            data = json.loads(log_file.read_text())
            return data.get("tasks", [])
        except Exception as e:
            logger.warning(f"Failed to read tasks: {e}")
            return []

    def get_decisions(self, target_date: date) -> list[dict[str, Any]]:
        """Get decisions on the target date"""
        log_file = self._get_log_file(target_date)
        if not log_file.exists():
            return []

        try:
            data = json.loads(log_file.read_text())
            return data.get("decisions", [])
        except Exception as e:
            logger.warning(f"Failed to read decisions: {e}")
            return []

    def get_known_entities(self) -> set[str]:
        """Get set of known entities from entity cache"""
        entity_file = self.data_dir / "entities.json"
        if not entity_file.exists():
            return set()

        try:
            data = json.loads(entity_file.read_text())
            # Normalize to lowercase for case-insensitive comparison
            return {email.lower() for email in data.get("known_emails", [])}
        except Exception as e:
            logger.warning(f"Failed to read entities: {e}")
            return set()

    def _get_log_file(self, target_date: date) -> Path:
        """Get path to processing log file for date"""
        return self.data_dir / "logs" / f"processing_{target_date.isoformat()}.json"


# ============================================================================
# JOURNAL GENERATOR
# ============================================================================


@dataclass
class JournalGeneratorConfig:
    """Configuration for journal generation"""
    # Confidence threshold for "low confidence" questions
    low_confidence_threshold: int = 80

    # Maximum questions to generate
    max_questions: int = 10

    # Include questions for new senders
    ask_about_new_senders: bool = True

    # Include action verification questions
    ask_action_verification: bool = True

    # Minimum confidence to ask verification
    verification_confidence_max: int = 90


class JournalGenerator:
    """
    Generates daily journal entries

    Collects processing history for the day, identifies areas
    needing user input, and creates questions to improve
    future decisions.

    Example:
        >>> generator = JournalGenerator()
        >>> entry = generator.generate(date.today())
        >>> print(f"Generated journal with {len(entry.questions)} questions")
    """

    def __init__(
        self,
        history_provider: Optional[ProcessingHistoryProvider] = None,
        config: Optional[JournalGeneratorConfig] = None,
    ):
        """
        Initialize journal generator

        Args:
            history_provider: Provider for processing history data
            config: Generator configuration
        """
        self.history_provider = history_provider or JsonFileHistoryProvider()
        self.config = config or JournalGeneratorConfig()

    def generate(self, target_date: date) -> JournalEntry:
        """
        Generate journal entry for the target date

        Args:
            target_date: Date to generate journal for

        Returns:
            JournalEntry with day's summary and questions
        """
        logger.info(f"Generating journal for {target_date}")

        # Fetch processing history
        raw_emails = self.history_provider.get_processed_emails(target_date)
        raw_tasks = self.history_provider.get_created_tasks(target_date)
        raw_decisions = self.history_provider.get_decisions(target_date)
        known_entities = self.history_provider.get_known_entities()

        # Convert to model objects
        emails = self._convert_emails(raw_emails)
        tasks = self._convert_tasks(raw_tasks)
        decisions = self._convert_decisions(raw_decisions)

        # Generate questions
        questions = self._generate_questions(emails, known_entities)

        # Create journal entry
        entry = JournalEntry(
            journal_date=target_date,
            created_at=now_utc(),
            emails_processed=emails,
            tasks_created=tasks,
            decisions=decisions,
            questions=questions,
            status=JournalStatus.DRAFT,
        )

        logger.info(
            f"Journal generated: {len(emails)} emails, {len(tasks)} tasks, {len(questions)} questions"
        )

        return entry

    def _convert_emails(self, raw_emails: list[dict[str, Any]]) -> list[EmailSummary]:
        """Convert raw email data to EmailSummary objects"""
        summaries = []
        for raw in raw_emails:
            try:
                # Parse timestamp
                processed_at = raw.get("processed_at")
                if isinstance(processed_at, str):
                    processed_at = datetime.fromisoformat(processed_at)
                elif processed_at is None:
                    processed_at = now_utc()

                summary = EmailSummary(
                    email_id=raw.get("email_id", raw.get("id", str(uuid.uuid4()))),
                    from_address=raw.get("from_address", raw.get("from", "unknown")),
                    from_name=raw.get("from_name"),
                    subject=raw.get("subject", "(no subject)"),
                    action=raw.get("action", "unknown"),
                    category=raw.get("category", "other"),
                    confidence=raw.get("confidence", 0),
                    reasoning=raw.get("reasoning"),
                    processed_at=processed_at,
                )
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to convert email: {e}")
                continue

        return summaries

    def _convert_tasks(self, raw_tasks: list[dict[str, Any]]) -> list[TaskSummary]:
        """Convert raw task data to TaskSummary objects"""
        summaries = []
        for raw in raw_tasks:
            try:
                # Parse dates
                created_at = raw.get("created_at")
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                elif created_at is None:
                    created_at = now_utc()

                due_date = raw.get("due_date")
                if isinstance(due_date, str):
                    due_date = date.fromisoformat(due_date)

                summary = TaskSummary(
                    task_id=raw.get("task_id", str(uuid.uuid4())),
                    title=raw.get("title", "(untitled)"),
                    source_email_id=raw.get("source_email_id"),
                    project=raw.get("project"),
                    due_date=due_date,
                    created_at=created_at,
                )
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to convert task: {e}")
                continue

        return summaries

    def _convert_decisions(self, raw_decisions: list[dict[str, Any]]) -> list[DecisionSummary]:
        """Convert raw decision data to DecisionSummary objects"""
        summaries = []
        for raw in raw_decisions:
            try:
                # Parse timestamp
                timestamp = raw.get("timestamp")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                elif timestamp is None:
                    timestamp = now_utc()

                summary = DecisionSummary(
                    decision_id=raw.get("decision_id", str(uuid.uuid4())),
                    email_id=raw.get("email_id", "unknown"),
                    decision_type=raw.get("decision_type", raw.get("type", "unknown")),
                    confidence=raw.get("confidence", 0),
                    automated=raw.get("automated", False),
                    success=raw.get("success"),
                    error=raw.get("error"),
                    timestamp=timestamp,
                )
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to convert decision: {e}")
                continue

        return summaries

    def _generate_questions(
        self,
        emails: list[EmailSummary],
        known_entities: set[str],
    ) -> list[JournalQuestion]:
        """
        Generate questions based on processing results

        Questions are generated for:
        1. Low-confidence decisions (need verification)
        2. New senders (need classification)
        3. Action verification for automated decisions
        """
        questions: list[JournalQuestion] = []

        # 1. Questions for low-confidence decisions
        low_confidence_emails = [
            e for e in emails
            if e.confidence < self.config.low_confidence_threshold
        ]

        for email in low_confidence_emails[:5]:  # Limit to 5
            question = self._create_low_confidence_question(email)
            questions.append(question)

        # 2. Questions for new senders
        if self.config.ask_about_new_senders:
            new_senders = self._find_new_senders(emails, known_entities)
            for sender, email in new_senders[:3]:  # Limit to 3
                question = self._create_new_sender_question(sender, email)
                questions.append(question)

        # 3. Action verification questions
        if self.config.ask_action_verification:
            verification_candidates = [
                e for e in emails
                if self.config.low_confidence_threshold <= e.confidence < self.config.verification_confidence_max
            ]
            for email in verification_candidates[:2]:  # Limit to 2
                question = self._create_verification_question(email)
                questions.append(question)

        # Sort by priority and limit
        questions.sort(key=lambda q: q.priority)
        return questions[:self.config.max_questions]

    def _create_low_confidence_question(self, email: EmailSummary) -> JournalQuestion:
        """Create question for low-confidence decision"""
        return JournalQuestion(
            question_id=str(uuid.uuid4()),
            category=QuestionCategory.LOW_CONFIDENCE,
            question_text=f"L'email \"{email.subject[:50]}\" de {email.from_address} a ete analyse comme \"{email.action}\" avec {email.confidence}% de confiance. Est-ce correct ?",
            context=f"Confiance basse ({email.confidence}%). Verification importante pour ameliorer les futures decisions.",
            options=("Correct", "Devrait etre archive", "Devrait creer une tache", "Devrait etre supprime", "Autre"),
            related_email_id=email.email_id,
            priority=1,  # High priority
        )

    def _create_new_sender_question(self, sender: str, email: EmailSummary) -> JournalQuestion:
        """Create question for new sender"""
        return JournalQuestion(
            question_id=str(uuid.uuid4()),
            category=QuestionCategory.NEW_PERSON,
            question_text=f"Nouveau contact detecte : {sender}. Qui est cette personne ?",
            context="Premier email recu de cette adresse. Aide Scapin a mieux categoriser les futurs emails.",
            options=("Collegue travail", "Client/Partenaire", "Personnel", "Newsletter/Marketing", "Autre"),
            related_email_id=email.email_id,
            related_entity=sender,
            priority=2,
        )

    def _create_verification_question(self, email: EmailSummary) -> JournalQuestion:
        """Create verification question for medium-confidence decision"""
        return JournalQuestion(
            question_id=str(uuid.uuid4()),
            category=QuestionCategory.ACTION_VERIFY,
            question_text=f"L'email de {email.from_address} a ete {email.action}. Etait-ce la bonne action ?",
            context=f"Confiance moyenne ({email.confidence}%). Quick verification.",
            options=("Oui, correct", "Non, incorrect"),
            related_email_id=email.email_id,
            priority=3,
        )

    def _find_new_senders(
        self,
        emails: list[EmailSummary],
        known_entities: set[str],
    ) -> list[tuple[str, EmailSummary]]:
        """Find senders that are not in known entities"""
        new_senders = []
        seen = set()

        for email in emails:
            sender = email.from_address.lower()
            if sender not in known_entities and sender not in seen:
                new_senders.append((email.from_address, email))
                seen.add(sender)

        return new_senders
