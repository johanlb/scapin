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
from src.frontin.journal.models import (
    CalendarSummary,
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
from src.monitoring.logger import get_logger

logger = get_logger("frontin.journal.generator")


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

    # Multi-source methods (optional - return empty if not implemented)
    def get_teams_messages(self, target_date: date) -> list[dict[str, Any]]:
        """Get Teams messages processed on the target date"""
        ...

    def get_calendar_events(self, target_date: date) -> list[dict[str, Any]]:
        """Get Calendar events on the target date"""
        ...

    def get_omnifocus_items(self, target_date: date) -> list[dict[str, Any]]:
        """Get OmniFocus task activity on the target date"""
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

    # Multi-source methods (return empty - use specific providers)
    def get_teams_messages(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use TeamsHistoryProvider"""
        return []

    def get_calendar_events(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use CalendarHistoryProvider"""
        return []

    def get_omnifocus_items(self, _target_date: date) -> list[dict[str, Any]]:
        """Not implemented - use OmniFocusHistoryProvider"""
        return []


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

    # Pattern-based questions (from weekly reviews)
    ask_pattern_confirmation: bool = True

    # Preference learning questions
    ask_preference_learning: bool = True

    # Calibration check questions (when accuracy drops)
    ask_calibration_check: bool = True
    calibration_accuracy_threshold: float = 0.85  # Ask if below 85%

    # Priority review questions (for overdue/flagged items)
    ask_priority_review: bool = True
    priority_overdue_days: int = 3  # Ask about items overdue > 3 days


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

        # Fetch processing history (email)
        raw_emails = self.history_provider.get_processed_emails(target_date)
        raw_tasks = self.history_provider.get_created_tasks(target_date)
        raw_decisions = self.history_provider.get_decisions(target_date)
        known_entities = self.history_provider.get_known_entities()

        # Fetch multi-source data
        raw_teams = self._safe_get(
            lambda: self.history_provider.get_teams_messages(target_date)
        )
        raw_calendar = self._safe_get(
            lambda: self.history_provider.get_calendar_events(target_date)
        )
        raw_omnifocus = self._safe_get(
            lambda: self.history_provider.get_omnifocus_items(target_date)
        )

        # Convert to model objects
        emails = self._convert_emails(raw_emails)
        tasks = self._convert_tasks(raw_tasks)
        decisions = self._convert_decisions(raw_decisions)
        teams_messages = self._convert_teams_messages(raw_teams)
        calendar_events = self._convert_calendar_events(raw_calendar)
        omnifocus_items = self._convert_omnifocus_items(raw_omnifocus)

        # Generate questions (now with multi-source context)
        questions = self._generate_questions(
            emails=emails,
            known_entities=known_entities,
            teams_messages=teams_messages,
            calendar_events=calendar_events,
            omnifocus_items=omnifocus_items,
        )

        # Create journal entry
        entry = JournalEntry(
            journal_date=target_date,
            created_at=now_utc(),
            emails_processed=emails,
            tasks_created=tasks,
            decisions=decisions,
            questions=questions,
            status=JournalStatus.DRAFT,
            teams_messages=teams_messages,
            calendar_events=calendar_events,
            omnifocus_items=omnifocus_items,
        )

        logger.info(
            f"Journal generated: {len(emails)} emails, {len(teams_messages)} teams, "
            f"{len(calendar_events)} calendar, {len(omnifocus_items)} omnifocus, "
            f"{len(questions)} questions"
        )

        return entry

    def _safe_get(self, func: callable) -> list[dict[str, Any]]:
        """Safely call a provider method, returning empty list on error"""
        try:
            return func()
        except (AttributeError, NotImplementedError):
            return []
        except Exception as e:
            logger.debug(f"Provider method failed: {e}")
            return []

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

    def _convert_teams_messages(self, raw_messages: list[dict[str, Any]]) -> list[TeamsSummary]:
        """Convert raw Teams message data to TeamsSummary objects"""
        summaries = []
        for raw in raw_messages:
            try:
                # Parse timestamp
                processed_at = raw.get("processed_at")
                if isinstance(processed_at, str):
                    processed_at = datetime.fromisoformat(processed_at)
                elif processed_at is None:
                    processed_at = now_utc()

                summary = TeamsSummary(
                    message_id=raw.get("message_id", str(uuid.uuid4())),
                    chat_name=raw.get("chat_name", "(unknown chat)"),
                    sender=raw.get("sender", "unknown"),
                    preview=raw.get("preview", ""),
                    action=raw.get("action", "read"),
                    confidence=raw.get("confidence", 0),
                    processed_at=processed_at,
                )
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to convert Teams message: {e}")
                continue

        return summaries

    def _convert_calendar_events(self, raw_events: list[dict[str, Any]]) -> list[CalendarSummary]:
        """Convert raw Calendar event data to CalendarSummary objects"""
        summaries = []
        for raw in raw_events:
            try:
                # Parse timestamps
                start_time = raw.get("start_time")
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                elif start_time is None:
                    start_time = now_utc()

                end_time = raw.get("end_time")
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time)
                elif end_time is None:
                    end_time = start_time

                processed_at = raw.get("processed_at")
                if isinstance(processed_at, str):
                    processed_at = datetime.fromisoformat(processed_at)
                elif processed_at is None:
                    processed_at = now_utc()

                summary = CalendarSummary(
                    event_id=raw.get("event_id", str(uuid.uuid4())),
                    title=raw.get("title", "(no title)"),
                    start_time=start_time,
                    end_time=end_time,
                    action=raw.get("action", "attended"),
                    attendees=raw.get("attendees", []),
                    location=raw.get("location"),
                    is_online=raw.get("is_online", False),
                    notes=raw.get("notes"),
                    response_status=raw.get("response_status"),
                    processed_at=processed_at,
                )
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to convert Calendar event: {e}")
                continue

        return summaries

    def _convert_omnifocus_items(self, raw_items: list[dict[str, Any]]) -> list[OmniFocusSummary]:
        """Convert raw OmniFocus item data to OmniFocusSummary objects"""
        summaries = []
        for raw in raw_items:
            try:
                # Parse timestamps
                completed_at = raw.get("completed_at")
                if isinstance(completed_at, str):
                    completed_at = datetime.fromisoformat(completed_at)

                due_date = raw.get("due_date")
                if isinstance(due_date, str):
                    # Handle both date and datetime strings
                    try:
                        due_date = datetime.fromisoformat(due_date)
                    except ValueError:
                        due_date = datetime.fromisoformat(due_date + "T00:00:00")

                processed_at = raw.get("processed_at")
                if isinstance(processed_at, str):
                    processed_at = datetime.fromisoformat(processed_at)
                elif processed_at is None:
                    processed_at = now_utc()

                summary = OmniFocusSummary(
                    task_id=raw.get("task_id", str(uuid.uuid4())),
                    title=raw.get("title", "(untitled)"),
                    project=raw.get("project"),
                    status=raw.get("status", "unknown"),
                    tags=raw.get("tags", []),
                    completed_at=completed_at,
                    due_date=due_date,
                    flagged=raw.get("flagged", False),
                    estimated_minutes=raw.get("estimated_minutes"),
                    processed_at=processed_at,
                )
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to convert OmniFocus item: {e}")
                continue

        return summaries

    def _generate_questions(
        self,
        emails: list[EmailSummary],
        known_entities: set[str],
        teams_messages: Optional[list[TeamsSummary]] = None,
        calendar_events: Optional[list[CalendarSummary]] = None,
        omnifocus_items: Optional[list[OmniFocusSummary]] = None,
    ) -> list[JournalQuestion]:
        """
        Generate questions based on processing results

        Questions are generated for:
        1. Low-confidence decisions (need verification)
        2. New senders (need classification)
        3. Action verification for automated decisions
        4. Pattern confirmation (from detected patterns)
        5. Preference learning (recurring behaviors)
        6. Calibration check (when accuracy drops)
        7. Priority review (overdue/flagged items)
        """
        questions: list[JournalQuestion] = []
        teams_messages = teams_messages or []
        calendar_events = calendar_events or []
        omnifocus_items = omnifocus_items or []

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

        # 4. Pattern confirmation questions
        if self.config.ask_pattern_confirmation:
            pattern_questions = self._generate_pattern_questions(
                emails, teams_messages, omnifocus_items
            )
            questions.extend(pattern_questions[:2])  # Limit to 2

        # 5. Preference learning questions
        if self.config.ask_preference_learning:
            preference_questions = self._generate_preference_questions(
                calendar_events, omnifocus_items
            )
            questions.extend(preference_questions[:2])  # Limit to 2

        # 6. Calibration check questions
        if self.config.ask_calibration_check:
            calibration_questions = self._generate_calibration_questions(emails)
            questions.extend(calibration_questions[:1])  # Limit to 1

        # 7. Priority review questions
        if self.config.ask_priority_review:
            priority_questions = self._generate_priority_questions(omnifocus_items)
            questions.extend(priority_questions[:2])  # Limit to 2

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

    # =========================================================================
    # NEW QUESTION TYPES (Pattern, Preference, Calibration, Priority)
    # =========================================================================

    def _generate_pattern_questions(
        self,
        emails: list[EmailSummary],
        teams_messages: list[TeamsSummary],
        omnifocus_items: list[OmniFocusSummary],
    ) -> list[JournalQuestion]:
        """
        Generate pattern confirmation questions

        Detects patterns like:
        - High-volume sender always archived
        - Tasks from certain projects always deferred
        - Recurring category actions
        """
        questions = []

        # Pattern: High-volume sender with consistent action
        sender_actions: dict[str, dict[str, int]] = {}
        for email in emails:
            sender = email.from_address
            action = email.action
            if sender not in sender_actions:
                sender_actions[sender] = {}
            sender_actions[sender][action] = sender_actions[sender].get(action, 0) + 1

        for sender, actions in sender_actions.items():
            total = sum(actions.values())
            if total >= 3:  # At least 3 emails from this sender
                dominant_action = max(actions, key=actions.get)
                if actions[dominant_action] / total >= 0.8:  # 80%+ same action
                    questions.append(JournalQuestion(
                        question_id=str(uuid.uuid4()),
                        category=QuestionCategory.PATTERN_CONFIRM,
                        question_text=(
                            f"Scapin remarque que les emails de {sender} sont souvent "
                            f"'{dominant_action}' ({actions[dominant_action]}/{total}). "
                            "Faut-il appliquer cette regle automatiquement ?"
                        ),
                        context="Pattern detecte. Automatiser cette action reduirait le temps de traitement.",
                        options=(
                            "Oui, toujours appliquer",
                            "Oui, avec confirmation",
                            "Non, je decide au cas par cas",
                        ),
                        related_entity=sender,
                        priority=4,
                    ))

        # Pattern: Teams chat with high activity
        chat_activity: dict[str, int] = {}
        for msg in teams_messages:
            chat_activity[msg.chat_name] = chat_activity.get(msg.chat_name, 0) + 1

        for chat_name, count in chat_activity.items():
            if count >= 5:  # At least 5 messages in this chat
                questions.append(JournalQuestion(
                    question_id=str(uuid.uuid4()),
                    category=QuestionCategory.PATTERN_CONFIRM,
                    question_text=(
                        f"La conversation Teams '{chat_name}' a eu {count} messages aujourd'hui. "
                        "Faut-il suivre cette conversation de plus pres ?"
                    ),
                    context="Chat actif. Scapin peut prioriser les notifications de ce chat.",
                    options=(
                        "Oui, notifications prioritaires",
                        "Non, importance normale",
                        "Ignorer ce chat",
                    ),
                    related_entity=chat_name,
                    priority=5,
                ))

        # Pattern: OmniFocus project with many completions
        project_stats: dict[str, int] = {}
        for item in omnifocus_items:
            if item.status == "completed" and item.project:
                project_stats[item.project] = project_stats.get(item.project, 0) + 1

        for project, count in project_stats.items():
            if count >= 5:  # At least 5 completions from this project
                questions.append(JournalQuestion(
                    question_id=str(uuid.uuid4()),
                    category=QuestionCategory.PATTERN_CONFIRM,
                    question_text=(
                        f"Le projet '{project}' a eu {count} taches completees aujourd'hui. "
                        "Est-ce un projet prioritaire a suivre de pres ?"
                    ),
                    context="Beaucoup d'activite sur ce projet. Scapin peut le prioriser.",
                    options=(
                        "Oui, priorite haute",
                        "Priorite normale",
                        "Baisser la priorite",
                    ),
                    related_entity=project,
                    priority=5,
                ))

        return questions

    def _generate_preference_questions(
        self,
        calendar_events: list[CalendarSummary],
        omnifocus_items: list[OmniFocusSummary],
    ) -> list[JournalQuestion]:
        """
        Generate preference learning questions

        Learns preferences about:
        - Meeting preparation time
        - Task scheduling preferences
        - Focus time blocks
        """
        questions = []

        # Preference: Meeting preparation needs
        meetings_with_many_attendees = [
            e for e in calendar_events
            if len(e.attendees) >= 3 and e.action == "attended"
        ]
        if meetings_with_many_attendees:
            meeting = meetings_with_many_attendees[0]
            questions.append(JournalQuestion(
                question_id=str(uuid.uuid4()),
                category=QuestionCategory.PREFERENCE_LEARN,
                question_text=(
                    f"Avant la reunion '{meeting.title}' ({len(meeting.attendees)} participants), "
                    "combien de temps de preparation preferez-vous ?"
                ),
                context="Scapin peut vous envoyer un rappel avec contexte avant les reunions.",
                options=(
                    "5 minutes",
                    "15 minutes",
                    "30 minutes",
                    "Pas de rappel necessaire",
                ),
                related_entity=meeting.event_id,
                priority=5,
            ))

        # Preference: Task estimation accuracy
        estimated_tasks = [
            t for t in omnifocus_items
            if t.estimated_minutes and t.status == "completed"
        ]
        if len(estimated_tasks) >= 3:
            questions.append(JournalQuestion(
                question_id=str(uuid.uuid4()),
                category=QuestionCategory.PREFERENCE_LEARN,
                question_text=(
                    f"Vous avez complete {len(estimated_tasks)} taches estimees aujourd'hui. "
                    "Vos estimations de temps sont-elles generalement precises ?"
                ),
                context="Aide Scapin a mieux planifier votre charge de travail.",
                options=(
                    "Oui, generalement precises",
                    "Souvent sous-estimees",
                    "Souvent sur-estimees",
                    "Tres variables",
                ),
                priority=6,
            ))

        return questions

    def _generate_calibration_questions(
        self,
        emails: list[EmailSummary],
    ) -> list[JournalQuestion]:
        """
        Generate calibration check questions

        Asks about accuracy when:
        - Average confidence is low
        - Many different actions were taken
        """
        questions = []

        if not emails:
            return questions

        # Check average confidence
        avg_confidence = sum(e.confidence for e in emails) / len(emails)
        if avg_confidence < self.config.calibration_accuracy_threshold * 100:
            questions.append(JournalQuestion(
                question_id=str(uuid.uuid4()),
                category=QuestionCategory.CALIBRATION_CHECK,
                question_text=(
                    f"La confiance moyenne des decisions aujourd'hui etait de "
                    f"{avg_confidence:.0f}%. Voulez-vous revoir les seuils d'automatisation ?"
                ),
                context=(
                    f"Seuil actuel: {self.config.low_confidence_threshold}%. "
                    "Ajuster les seuils peut ameliorer la precision."
                ),
                options=(
                    "Augmenter le seuil (plus prudent)",
                    "Diminuer le seuil (plus automatise)",
                    "Garder tel quel",
                ),
                priority=3,
            ))

        # Check action diversity (many different actions = uncertainty)
        action_counts = {}
        for email in emails:
            action_counts[email.action] = action_counts.get(email.action, 0) + 1

        if len(action_counts) >= 4 and len(emails) >= 10:
            actions_summary = ", ".join(
                f"{action}({count})" for action, count in sorted(
                    action_counts.items(), key=lambda x: -x[1]
                )[:4]
            )
            questions.append(JournalQuestion(
                question_id=str(uuid.uuid4()),
                category=QuestionCategory.CALIBRATION_CHECK,
                question_text=(
                    f"Beaucoup d'actions differentes aujourd'hui: {actions_summary}. "
                    "Y a-t-il une action que Scapin devrait prioriser ?"
                ),
                context="Aide Scapin a mieux comprendre vos priorites.",
                options=(
                    "Focus sur les taches",
                    "Focus sur l'archivage",
                    "Focus sur la lecture",
                    "Equilibrer les actions",
                ),
                priority=4,
            ))

        return questions

    def _generate_priority_questions(
        self,
        omnifocus_items: list[OmniFocusSummary],
    ) -> list[JournalQuestion]:
        """
        Generate priority review questions

        Asks about:
        - Overdue tasks
        - Flagged but not worked on
        - Long-standing tasks
        """
        questions = []
        now = now_utc()

        # Find overdue items
        overdue_items = [
            item for item in omnifocus_items
            if item.status == "overdue" or (
                item.due_date and
                item.due_date < now and
                item.status not in ("completed", "dropped")
            )
        ]

        # Question for overdue items
        if overdue_items:
            oldest = min(overdue_items, key=lambda x: x.due_date or now)
            days_overdue = (now - oldest.due_date).days if oldest.due_date else 0

            if days_overdue >= self.config.priority_overdue_days:
                questions.append(JournalQuestion(
                    question_id=str(uuid.uuid4()),
                    category=QuestionCategory.PRIORITY_REVIEW,
                    question_text=(
                        f"La tache '{oldest.title[:50]}' est en retard de {days_overdue} jours. "
                        "Que voulez-vous faire ?"
                    ),
                    context=f"Projet: {oldest.project or 'Aucun'}. Total taches en retard: {len(overdue_items)}.",
                    options=(
                        "Reporter a demain",
                        "Reporter a la semaine prochaine",
                        "Annuler cette tache",
                        "La faire maintenant (priorite haute)",
                    ),
                    related_entity=oldest.task_id,
                    priority=2,  # High priority
                ))

        # Question for flagged items not completed
        flagged_pending = [
            item for item in omnifocus_items
            if item.flagged and item.status not in ("completed", "dropped")
        ]

        if len(flagged_pending) >= 3:
            questions.append(JournalQuestion(
                question_id=str(uuid.uuid4()),
                category=QuestionCategory.PRIORITY_REVIEW,
                question_text=(
                    f"Vous avez {len(flagged_pending)} taches marquees importantes en attente. "
                    "Voulez-vous revoir leurs priorites ?"
                ),
                context="Les taches marquees sont censees etre prioritaires.",
                options=(
                    "Oui, ouvrir OmniFocus",
                    "Lister dans le journal",
                    "Non, je m'en occupe",
                ),
                priority=3,
            ))

        return questions
