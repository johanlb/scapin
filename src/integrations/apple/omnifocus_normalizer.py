"""
OmniFocus Event Normalizer

Converts OmniFocus tasks to the universal PerceivedEvent format
for processing by the cognitive pipeline.

Follows the same pattern as CalendarNormalizer and TeamsNormalizer.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.events.universal_event import (
    Entity,
    EventSource,
    EventType,
    PerceivedEvent,
    UrgencyLevel,
)
from src.integrations.apple.omnifocus_models import (
    OmniFocusTask,
    TaskStatus,
)
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("integrations.apple.omnifocus_normalizer")


@dataclass
class OmniFocusNormalizer:
    """
    Normalizes OmniFocus tasks to PerceivedEvent

    Converts OmniFocusTask dataclass to the universal event format
    used by the cognitive pipeline. Follows the same pattern as
    CalendarNormalizer for consistency.

    Key differences from other normalizers:
    - Source is TASK
    - Urgency is based on due date proximity and flagged status
    - Event type focuses on action_required vs reminder distinction
    - Extracts project and tags as entities

    Usage:
        normalizer = OmniFocusNormalizer()
        event = normalizer.normalize(task)
    """

    def normalize(self, task: OmniFocusTask) -> PerceivedEvent:
        """
        Convert an OmniFocus task to a PerceivedEvent

        Args:
            task: OmniFocusTask to normalize

        Returns:
            PerceivedEvent ready for cognitive processing
        """
        logger.debug(f"Normalizing OmniFocus task {task.task_id}")

        # Determine event type based on characteristics
        event_type = self._determine_event_type(task)

        # Determine urgency based on due date and status
        urgency = self._determine_urgency(task)

        # Extract entities from task
        entities = self._extract_entities(task)

        # Extract topics and keywords
        topics, keywords = self._extract_topics_and_keywords(task)

        # Build title
        title = self._build_title(task)

        # Build content summary
        content = self._build_content(task)

        # Timing
        current_time = now_utc()
        occurred_at = task.created_at or current_time

        # Build the PerceivedEvent
        perceived_event = PerceivedEvent(
            # Identity
            event_id=f"omnifocus-{task.task_id}",
            source=EventSource.TASK,
            source_id=task.task_id,
            # Timing
            occurred_at=occurred_at,
            received_at=current_time,
            perceived_at=current_time,
            # Content
            title=title,
            content=content,
            # Classification
            event_type=event_type,
            urgency=urgency,
            # Extracted info
            entities=entities,
            topics=topics,
            keywords=keywords,
            # Participants - tasks are personal, no from/to
            from_person=None,
            to_people=[],
            cc_people=[],
            # Context
            thread_id=task.project_id or task.task_id,
            references=[],
            in_reply_to=None,
            # Attachments - OmniFocus tasks don't have attachments in this model
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            # Metadata
            metadata={
                "task_id": task.task_id,
                "status": task.status.value,
                "project_id": task.project_id,
                "project_name": task.project_name,
                "tags": list(task.tags),
                "flagged": task.flagged,
                "estimated_minutes": task.estimated_minutes,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "defer_date": task.defer_date.isoformat() if task.defer_date else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "modified_at": task.modified_at.isoformat() if task.modified_at else None,
            },
            # Quality
            perception_confidence=0.95,  # High confidence for structured task data
            needs_clarification=False,
            clarification_questions=[],
        )

        logger.debug(f"Normalized task to {perceived_event.event_id} (type={event_type.value})")
        return perceived_event

    def _determine_event_type(self, task: OmniFocusTask) -> EventType:
        """
        Determine the event type based on task characteristics

        Uses heuristics based on:
        - Task status (completed, active, dropped)
        - Flagged status
        - Due date presence
        """
        # Completed tasks are informational
        if task.status == TaskStatus.COMPLETED:
            return EventType.STATUS_UPDATE

        # Dropped tasks are informational
        if task.status == TaskStatus.DROPPED:
            return EventType.INFORMATION

        # On hold tasks are reminders
        if task.status == TaskStatus.ON_HOLD:
            return EventType.REMINDER

        # Has due date = deadline-driven
        if task.due_date:
            now = datetime.now(timezone.utc)
            if task.due_date < now:
                # Overdue - critical action required
                return EventType.ACTION_REQUIRED
            time_until = (task.due_date - now).total_seconds() / 3600
            if time_until < 24:  # Due within 24 hours
                return EventType.DEADLINE
            return EventType.ACTION_REQUIRED

        # Flagged tasks are high-priority actions
        if task.flagged:
            return EventType.ACTION_REQUIRED

        # Default: reminder for active tasks
        return EventType.REMINDER

    def _determine_urgency(self, task: OmniFocusTask) -> UrgencyLevel:
        """
        Determine urgency based on due date and flagged status

        Priority:
        1. Completed/dropped tasks have no urgency
        2. Overdue tasks are critical
        3. Flagged tasks are at least high
        4. Due date proximity determines the rest
        """
        # Completed or dropped = no urgency
        if task.status in (TaskStatus.COMPLETED, TaskStatus.DROPPED):
            return UrgencyLevel.NONE

        # On hold = low urgency
        if task.status == TaskStatus.ON_HOLD:
            return UrgencyLevel.LOW

        now = datetime.now(timezone.utc)

        # Overdue = critical
        if task.due_date and task.due_date < now:
            return UrgencyLevel.CRITICAL

        # Flagged = at least high
        if task.flagged:
            if task.due_date:
                time_until = (task.due_date - now).total_seconds() / 3600
                if time_until < 24:
                    return UrgencyLevel.CRITICAL
            return UrgencyLevel.HIGH

        # Based on due date proximity
        if task.due_date:
            time_until = (task.due_date - now).total_seconds() / 3600

            if time_until < 4:  # Within 4 hours
                return UrgencyLevel.CRITICAL
            if time_until < 24:  # Within 24 hours
                return UrgencyLevel.HIGH
            if time_until < 72:  # Within 3 days
                return UrgencyLevel.MEDIUM
            return UrgencyLevel.LOW

        # No due date = low urgency
        return UrgencyLevel.LOW

    def _extract_entities(self, task: OmniFocusTask) -> list[Entity]:
        """
        Extract entities from the task

        Extracts:
        - Project as organization entity
        - Tags as topic entities
        - Due date as datetime entity
        """
        entities: list[Entity] = []

        # Project
        if task.project_name:
            entities.append(Entity(
                type="project",
                value=task.project_name,
                confidence=0.95,
                metadata={
                    "project_id": task.project_id,
                    "source": "omnifocus",
                },
            ))

        # Tags as topics
        for tag in task.tags:
            entities.append(Entity(
                type="topic",
                value=tag,
                confidence=0.90,
                metadata={"source": "omnifocus_tag"},
            ))

        # Due date
        if task.due_date:
            entities.append(Entity(
                type="datetime",
                value=task.due_date.isoformat(),
                confidence=0.99,
                metadata={
                    "type": "due_date",
                    "is_overdue": task.due_date < datetime.now(timezone.utc),
                },
            ))

        # Defer date
        if task.defer_date:
            entities.append(Entity(
                type="datetime",
                value=task.defer_date.isoformat(),
                confidence=0.99,
                metadata={"type": "defer_date"},
            ))

        return entities

    def _extract_topics_and_keywords(
        self,
        task: OmniFocusTask,
    ) -> tuple[list[str], list[str]]:
        """
        Extract topics and keywords from task content

        Uses tags as topics and extracts keywords from name/note.
        """
        # Tags are topics
        topics = list(task.tags)

        # Project as topic if exists
        if task.project_name and task.project_name not in topics:
            topics.append(task.project_name)

        # Simple keyword extraction from name and note
        keywords: list[str] = []
        content = task.name.lower()
        if task.note:
            content += " " + task.note.lower()

        important_words = [
            "urgent", "important", "deadline", "asap", "critical",
            "review", "approve", "fix", "bug", "error",
            "meeting", "call", "email", "reply", "follow-up",
            "submit", "send", "prepare", "finish", "complete",
            "waiting", "blocked", "depends", "after",
        ]

        for word in important_words:
            if word in content:
                keywords.append(word)

        # Flagged indicator
        if task.flagged:
            keywords.append("flagged")

        return topics, keywords

    def _build_title(self, task: OmniFocusTask) -> str:
        """
        Build a title from the task

        Includes status/flag prefix for easy scanning.
        """
        prefixes = []

        # Status prefix
        if task.status == TaskStatus.COMPLETED:
            prefixes.append("✓")
        elif task.status == TaskStatus.DROPPED:
            prefixes.append("✗")
        elif task.status == TaskStatus.ON_HOLD:
            prefixes.append("⏸")
        elif task.flagged:
            prefixes.append("⚑")

        # Due date indicator
        if task.due_date:
            now = datetime.now(timezone.utc)
            if task.due_date < now:
                prefixes.append("⚠ OVERDUE")
            else:
                time_until = (task.due_date - now).total_seconds() / 3600
                if time_until < 24:
                    prefixes.append(f"📅 {task.due_date.strftime('%H:%M')}")
                else:
                    prefixes.append(f"📅 {task.due_date.strftime('%m/%d')}")

        prefix = " ".join(prefixes)
        if prefix:
            return f"[{prefix}] {task.name}"
        return task.name

    def _build_content(self, task: OmniFocusTask) -> str:
        """
        Build content summary for the task

        Combines key information into readable text.
        """
        parts: list[str] = []

        # Task name
        parts.append(task.name)

        # Status
        status_display = {
            TaskStatus.ACTIVE: "Active",
            TaskStatus.COMPLETED: "Completed",
            TaskStatus.DROPPED: "Dropped",
            TaskStatus.ON_HOLD: "On Hold",
        }
        parts.append(f"Status: {status_display.get(task.status, task.status.value)}")

        # Project
        if task.project_name:
            parts.append(f"Project: {task.project_name}")

        # Tags
        if task.tags:
            parts.append(f"Tags: {', '.join(task.tags)}")

        # Due date
        if task.due_date:
            now = datetime.now(timezone.utc)
            if task.due_date < now:
                overdue_hours = (now - task.due_date).total_seconds() / 3600
                parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d %H:%M')} (OVERDUE by {overdue_hours:.0f}h)")
            else:
                parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}")

        # Defer date
        if task.defer_date:
            parts.append(f"Defer until: {task.defer_date.strftime('%Y-%m-%d %H:%M')}")

        # Estimated time
        if task.estimated_minutes:
            if task.estimated_minutes >= 60:
                hours = task.estimated_minutes / 60
                parts.append(f"Estimated: {hours:.1f}h")
            else:
                parts.append(f"Estimated: {task.estimated_minutes}min")

        # Flagged
        if task.flagged:
            parts.append("⚑ Flagged")

        # Note
        if task.note:
            parts.append("")
            parts.append(task.note)

        return "\n".join(parts)
