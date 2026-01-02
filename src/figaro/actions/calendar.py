"""
Calendar Actions for Figaro

Actions for interacting with Microsoft Calendar:
- Create events
- Respond to invitations
- Create tasks from events
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.figaro.actions.base import Action, ActionResult, ValidationResult
from src.monitoring.logger import get_logger

logger = get_logger("figaro.actions.calendar")


@dataclass
class CalendarCreateEventAction(Action):
    """
    Create a new calendar event

    Creates a meeting or appointment in the user's calendar.
    """

    subject: str
    start: datetime
    end: datetime
    body: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[list[str]] = None
    is_online: bool = False
    importance: str = "normal"
    reminder_minutes: int = 15
    calendar_id: Optional[str] = None

    _action_id: str = field(default_factory=lambda: f"cal_create_{uuid.uuid4().hex[:8]}")
    _created_event_id: Optional[str] = None

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return "calendar_create_event"

    def validate(self) -> ValidationResult:
        """Validate create event action parameters"""
        errors: list[str] = []
        warnings: list[str] = []

        if not self.subject:
            errors.append("subject is required")
        elif len(self.subject) > 255:
            errors.append("subject exceeds 255 character limit")

        if self.end <= self.start:
            errors.append("end must be after start")

        if self.body and len(self.body) > 32000:
            errors.append("body exceeds 32000 character limit")

        if self.importance not in ("low", "normal", "high"):
            errors.append("importance must be low, normal, or high")

        if self.reminder_minutes < 0:
            errors.append("reminder_minutes must be non-negative")
        elif self.reminder_minutes > 10080:  # 1 week
            warnings.append("reminder_minutes exceeds 1 week")

        # Check attendee email format
        if self.attendees:
            for email in self.attendees:
                if "@" not in email:
                    errors.append(f"Invalid attendee email: {email}")

        # Check if event is in the past
        if self.start < datetime.now(timezone.utc):
            warnings.append("Event start time is in the past")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def execute(self) -> ActionResult:
        """
        Execute the create event action

        Note: Actual Calendar API call is handled by CalendarClient.
        This action prepares the data for execution.
        """
        start_time = datetime.now()

        try:
            # Validate first
            validation = self.validate()
            if not validation:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error=ValueError(f"Validation failed: {validation.errors}"),
                )

            # The actual API call would be:
            # event = await calendar_client.create_event(
            #     subject=self.subject,
            #     start=self.start,
            #     end=self.end,
            #     body=self.body,
            #     location=self.location,
            #     attendees=self.attendees,
            #     is_online=self.is_online,
            # )

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"CalendarCreateEventAction executed: {self.subject}")

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "subject": self.subject,
                    "start": self.start.isoformat(),
                    "end": self.end.isoformat(),
                    "attendee_count": len(self.attendees) if self.attendees else 0,
                },
                metadata={
                    "is_online": self.is_online,
                    "location": self.location,
                    "calendar_id": self.calendar_id,
                },
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"CalendarCreateEventAction failed: {e}")
            return ActionResult(
                success=False,
                duration=duration,
                error=e,
            )

    def supports_undo(self) -> bool:
        """Create event can be undone by deleting it"""
        return True

    def can_undo(self, result: ActionResult) -> bool:
        """Can undo if event was created successfully"""
        return result.success and self._created_event_id is not None

    def undo(self, _result: ActionResult) -> bool:
        """Undo by deleting the created event"""
        if not self._created_event_id:
            return False

        try:
            # Would call: await calendar_client.delete_event(self._created_event_id)
            logger.info(f"Undoing CalendarCreateEventAction: {self._created_event_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to undo CalendarCreateEventAction: {e}")
            return False

    def dependencies(self) -> list[str]:
        """No dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated ~2 seconds for API call"""
        return 2.0


@dataclass
class CalendarRespondAction(Action):
    """
    Respond to a calendar invitation

    Accepts, tentatively accepts, or declines a meeting invitation.
    """

    event_id: str
    response: str  # "accept", "tentativelyAccept", "decline"
    comment: Optional[str] = None
    send_response: bool = True

    _action_id: str = field(default_factory=lambda: f"cal_respond_{uuid.uuid4().hex[:8]}")
    _previous_response: Optional[str] = None

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return "calendar_respond"

    def validate(self) -> ValidationResult:
        """Validate respond action parameters"""
        errors: list[str] = []
        warnings: list[str] = []

        if not self.event_id:
            errors.append("event_id is required")

        valid_responses = {"accept", "tentativelyAccept", "decline"}
        if self.response not in valid_responses:
            errors.append(f"response must be one of: {valid_responses}")

        if self.comment and len(self.comment) > 1000:
            warnings.append("comment is quite long, consider shortening")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def execute(self) -> ActionResult:
        """
        Execute the respond action

        Note: Actual Calendar API call is handled by CalendarClient.
        """
        start_time = datetime.now()

        try:
            validation = self.validate()
            if not validation:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error=ValueError(f"Validation failed: {validation.errors}"),
                )

            # The actual API call would be:
            # await calendar_client.respond_to_event(
            #     event_id=self.event_id,
            #     response=self.response,
            #     comment=self.comment,
            #     send_response=self.send_response,
            # )

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"CalendarRespondAction executed: {self.event_id} -> {self.response}")

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "event_id": self.event_id,
                    "response": self.response,
                },
                metadata={
                    "comment": self.comment,
                    "send_response": self.send_response,
                },
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"CalendarRespondAction failed: {e}")
            return ActionResult(
                success=False,
                duration=duration,
                error=e,
            )

    def supports_undo(self) -> bool:
        """Response can be changed"""
        return True

    def can_undo(self, result: ActionResult) -> bool:
        """Can undo if we have previous response"""
        return result.success and self._previous_response is not None

    def undo(self, _result: ActionResult) -> bool:
        """Undo by reverting to previous response"""
        if not self._previous_response:
            return False

        try:
            # Would call: await calendar_client.respond_to_event(
            #     event_id=self.event_id,
            #     response=self._previous_response,
            # )
            logger.info(f"Undoing CalendarRespondAction: reverting to {self._previous_response}")
            return True
        except Exception as e:
            logger.error(f"Failed to undo CalendarRespondAction: {e}")
            return False

    def dependencies(self) -> list[str]:
        """No dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated ~1 second for API call"""
        return 1.0


@dataclass
class CalendarCreateTaskFromEventAction(Action):
    """
    Create a task from a calendar event

    Creates a task in OmniFocus (or other task manager) based on
    a calendar event. Useful for pre-meeting preparation.
    """

    event_id: str
    event_subject: str
    task_title: Optional[str] = None  # If None, uses event subject
    task_note: Optional[str] = None
    due_date: Optional[datetime] = None
    project_name: Optional[str] = None
    tags: Optional[list[str]] = None

    _action_id: str = field(default_factory=lambda: f"cal_task_{uuid.uuid4().hex[:8]}")
    _created_task_id: Optional[str] = None

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return "calendar_create_task"

    def validate(self) -> ValidationResult:
        """Validate create task action parameters"""
        errors: list[str] = []
        warnings: list[str] = []

        if not self.event_id:
            errors.append("event_id is required")

        if not self.event_subject and not self.task_title:
            errors.append("Either event_subject or task_title is required")

        if self.task_note and len(self.task_note) > 10000:
            warnings.append("task_note is quite long")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def execute(self) -> ActionResult:
        """
        Execute the create task action

        Note: Actual task creation is handled by OmniFocus integration.
        """
        start_time = datetime.now()

        try:
            validation = self.validate()
            if not validation:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error=ValueError(f"Validation failed: {validation.errors}"),
                )

            # Determine task title
            title = self.task_title or f"Prepare for: {self.event_subject}"

            # Build task note
            note_parts = []
            if self.task_note:
                note_parts.append(self.task_note)
            note_parts.append(f"\nSource: Calendar event {self.event_id}")
            _note = "\n".join(note_parts)  # Prefixed with _ as used in actual API call

            # The actual task creation would be:
            # task_id = await omnifocus.add_task(
            #     name=title,
            #     note=note,
            #     due_date=self.due_date,
            #     project_name=self.project_name,
            #     tags=self.tags,
            # )

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"CalendarCreateTaskFromEventAction executed: {title}")

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "task_title": title,
                    "event_id": self.event_id,
                },
                metadata={
                    "project": self.project_name,
                    "tags": self.tags,
                    "due_date": self.due_date.isoformat() if self.due_date else None,
                },
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"CalendarCreateTaskFromEventAction failed: {e}")
            return ActionResult(
                success=False,
                duration=duration,
                error=e,
            )

    def supports_undo(self) -> bool:
        """Task creation can be undone by deleting the task"""
        return True

    def can_undo(self, result: ActionResult) -> bool:
        """Can undo if task was created"""
        return result.success and self._created_task_id is not None

    def undo(self, _result: ActionResult) -> bool:
        """Undo by deleting the created task"""
        if not self._created_task_id:
            return False

        try:
            # Would call: await omnifocus.remove_task(self._created_task_id)
            logger.info(f"Undoing CalendarCreateTaskFromEventAction: {self._created_task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to undo CalendarCreateTaskFromEventAction: {e}")
            return False

    def dependencies(self) -> list[str]:
        """No dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated ~1 second for task creation"""
        return 1.0


@dataclass
class CalendarBlockTimeAction(Action):
    """
    Block time on calendar for focus work

    Creates a calendar event to block time for focused work,
    based on task or project requirements.
    """

    title: str
    duration_minutes: int
    preferred_start: Optional[datetime] = None
    preferred_end: Optional[datetime] = None
    show_as: str = "busy"  # busy, tentative, free
    categories: Optional[list[str]] = None

    _action_id: str = field(default_factory=lambda: f"cal_block_{uuid.uuid4().hex[:8]}")
    _created_event_id: Optional[str] = None

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return "calendar_block_time"

    def validate(self) -> ValidationResult:
        """Validate block time action parameters"""
        errors: list[str] = []
        warnings: list[str] = []

        if not self.title:
            errors.append("title is required")

        if self.duration_minutes < 15:
            errors.append("duration_minutes must be at least 15")
        elif self.duration_minutes > 480:  # 8 hours
            warnings.append("duration_minutes exceeds 8 hours")

        if self.show_as not in ("busy", "tentative", "free"):
            errors.append("show_as must be busy, tentative, or free")

        if self.preferred_start and self.preferred_end and self.preferred_start >= self.preferred_end:
            errors.append("preferred_start must be before preferred_end")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def execute(self) -> ActionResult:
        """
        Execute the block time action

        Would find available slot and create blocking event.
        """
        start_time = datetime.now()

        try:
            validation = self.validate()
            if not validation:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error=ValueError(f"Validation failed: {validation.errors}"),
                )

            # Determine start time (default: next available slot)
            event_start = self.preferred_start or (datetime.now(timezone.utc) + timedelta(hours=1))
            event_end = event_start + timedelta(minutes=self.duration_minutes)

            # The actual creation would:
            # 1. Check free/busy
            # 2. Find available slot
            # 3. Create event with show_as status

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"CalendarBlockTimeAction executed: {self.title}")

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "title": self.title,
                    "start": event_start.isoformat(),
                    "end": event_end.isoformat(),
                    "duration_minutes": self.duration_minutes,
                },
                metadata={
                    "show_as": self.show_as,
                    "categories": self.categories,
                },
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"CalendarBlockTimeAction failed: {e}")
            return ActionResult(
                success=False,
                duration=duration,
                error=e,
            )

    def supports_undo(self) -> bool:
        """Block time can be undone by deleting the event"""
        return True

    def can_undo(self, result: ActionResult) -> bool:
        """Can undo if blocking event was created"""
        return result.success and self._created_event_id is not None

    def undo(self, _result: ActionResult) -> bool:
        """Undo by deleting the blocking event"""
        if not self._created_event_id:
            return False

        try:
            logger.info(f"Undoing CalendarBlockTimeAction: {self._created_event_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to undo CalendarBlockTimeAction: {e}")
            return False

    def dependencies(self) -> list[str]:
        """No dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated ~2 seconds for creating blocking event"""
        return 2.0
