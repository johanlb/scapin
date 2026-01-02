"""
Tests for Calendar Actions

Tests the Figaro actions for Calendar operations.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.figaro.actions.calendar import (
    CalendarBlockTimeAction,
    CalendarCreateEventAction,
    CalendarCreateTaskFromEventAction,
    CalendarRespondAction,
)


class TestCalendarCreateEventAction:
    """Tests for CalendarCreateEventAction"""

    def test_basic_creation(self):
        """Test creating a basic event action"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Test Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        assert action.subject == "Test Meeting"
        assert action.action_type == "calendar_create_event"
        assert action.importance == "normal"
        assert action.reminder_minutes == 15

    def test_action_with_all_fields(self):
        """Test action with all optional fields"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Team Sync",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            body="<p>Meeting body</p>",
            location="Conference Room A",
            attendees=["user1@example.com", "user2@example.com"],
            is_online=True,
            importance="high",
            reminder_minutes=30,
            calendar_id="cal_123",
        )
        assert action.is_online is True
        assert action.importance == "high"
        assert len(action.attendees) == 2

    def test_validate_success(self):
        """Test validation passes for valid action"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        result = action.validate()
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_empty_subject(self):
        """Test validation fails for empty subject"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        result = action.validate()
        assert result.valid is False
        assert any("subject" in e for e in result.errors)

    def test_validate_long_subject(self):
        """Test validation fails for too long subject"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="x" * 300,
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        result = action.validate()
        assert result.valid is False
        assert any("255" in e for e in result.errors)

    def test_validate_end_before_start(self):
        """Test validation fails when end is before start"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Meeting",
            start=now + timedelta(hours=2),
            end=now + timedelta(hours=1),  # End before start
        )
        result = action.validate()
        assert result.valid is False
        assert any("end must be after start" in e for e in result.errors)

    def test_validate_invalid_importance(self):
        """Test validation fails for invalid importance"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            importance="invalid",
        )
        result = action.validate()
        assert result.valid is False
        assert any("importance" in e for e in result.errors)

    def test_validate_invalid_attendee_email(self):
        """Test validation fails for invalid attendee email"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            attendees=["valid@example.com", "invalid-email"],
        )
        result = action.validate()
        assert result.valid is False
        assert any("invalid-email" in e for e in result.errors)

    def test_validate_past_event_warning(self):
        """Test warning for event in the past"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Meeting",
            start=now - timedelta(hours=1),  # In the past
            end=now,
        )
        result = action.validate()
        # May or may not be valid, but should have warning
        assert any("past" in w.lower() for w in result.warnings)

    def test_execute_success(self):
        """Test successful execution"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        result = action.execute()
        assert result.success is True
        assert result.output["subject"] == "Meeting"

    def test_supports_undo(self):
        """Test that action supports undo"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateEventAction(
            subject="Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        assert action.supports_undo() is True


class TestCalendarRespondAction:
    """Tests for CalendarRespondAction"""

    def test_basic_creation(self):
        """Test creating a basic respond action"""
        action = CalendarRespondAction(
            event_id="event123",
            response="accept",
        )
        assert action.event_id == "event123"
        assert action.response == "accept"
        assert action.action_type == "calendar_respond"
        assert action.send_response is True

    def test_respond_with_comment(self):
        """Test respond with comment"""
        action = CalendarRespondAction(
            event_id="event123",
            response="decline",
            comment="Sorry, I have a conflict",
            send_response=True,
        )
        assert action.comment == "Sorry, I have a conflict"

    def test_validate_success(self):
        """Test validation passes for valid action"""
        action = CalendarRespondAction(
            event_id="event123",
            response="accept",
        )
        result = action.validate()
        assert result.valid is True

    def test_validate_empty_event_id(self):
        """Test validation fails for empty event_id"""
        action = CalendarRespondAction(
            event_id="",
            response="accept",
        )
        result = action.validate()
        assert result.valid is False
        assert any("event_id" in e for e in result.errors)

    def test_validate_invalid_response(self):
        """Test validation fails for invalid response type"""
        action = CalendarRespondAction(
            event_id="event123",
            response="maybe",  # Invalid
        )
        result = action.validate()
        assert result.valid is False
        assert any("response" in e for e in result.errors)

    def test_validate_all_response_types(self):
        """Test all valid response types pass validation"""
        for response in ["accept", "tentativelyAccept", "decline"]:
            action = CalendarRespondAction(
                event_id="event123",
                response=response,
            )
            result = action.validate()
            assert result.valid is True, f"Response '{response}' should be valid"

    def test_execute_success(self):
        """Test successful execution"""
        action = CalendarRespondAction(
            event_id="event123",
            response="accept",
        )
        result = action.execute()
        assert result.success is True
        assert result.output["response"] == "accept"

    def test_supports_undo(self):
        """Test that action supports undo"""
        action = CalendarRespondAction(
            event_id="event123",
            response="accept",
        )
        assert action.supports_undo() is True


class TestCalendarCreateTaskFromEventAction:
    """Tests for CalendarCreateTaskFromEventAction"""

    def test_basic_creation(self):
        """Test creating a basic task action"""
        action = CalendarCreateTaskFromEventAction(
            event_id="event123",
            event_subject="Team Meeting",
        )
        assert action.event_id == "event123"
        assert action.event_subject == "Team Meeting"
        assert action.action_type == "calendar_create_task"

    def test_with_custom_title(self):
        """Test with custom task title"""
        action = CalendarCreateTaskFromEventAction(
            event_id="event123",
            event_subject="Team Meeting",
            task_title="Prepare for Team Meeting",
        )
        assert action.task_title == "Prepare for Team Meeting"

    def test_with_all_fields(self):
        """Test with all optional fields"""
        now = datetime.now(timezone.utc)
        action = CalendarCreateTaskFromEventAction(
            event_id="event123",
            event_subject="Review Meeting",
            task_title="Prepare review materials",
            task_note="Gather all reports",
            due_date=now + timedelta(days=1),
            project_name="Project X",
            tags=["meeting", "review"],
        )
        assert action.project_name == "Project X"
        assert len(action.tags) == 2

    def test_validate_success(self):
        """Test validation passes"""
        action = CalendarCreateTaskFromEventAction(
            event_id="event123",
            event_subject="Meeting",
        )
        result = action.validate()
        assert result.valid is True

    def test_validate_empty_event_id(self):
        """Test validation fails for empty event_id"""
        action = CalendarCreateTaskFromEventAction(
            event_id="",
            event_subject="Meeting",
        )
        result = action.validate()
        assert result.valid is False

    def test_validate_no_subject_or_title(self):
        """Test validation fails with neither subject nor title"""
        action = CalendarCreateTaskFromEventAction(
            event_id="event123",
            event_subject="",
            task_title=None,
        )
        result = action.validate()
        assert result.valid is False

    def test_execute_uses_event_subject_as_title(self):
        """Test that event subject is used if no custom title"""
        action = CalendarCreateTaskFromEventAction(
            event_id="event123",
            event_subject="Important Meeting",
        )
        result = action.execute()
        assert result.success is True
        assert "Important Meeting" in result.output["task_title"]

    def test_execute_uses_custom_title(self):
        """Test that custom title is used when provided"""
        action = CalendarCreateTaskFromEventAction(
            event_id="event123",
            event_subject="Meeting",
            task_title="Custom Task Title",
        )
        result = action.execute()
        assert result.success is True
        assert result.output["task_title"] == "Custom Task Title"


class TestCalendarBlockTimeAction:
    """Tests for CalendarBlockTimeAction"""

    def test_basic_creation(self):
        """Test creating a basic block time action"""
        action = CalendarBlockTimeAction(
            title="Focus Time",
            duration_minutes=60,
        )
        assert action.title == "Focus Time"
        assert action.duration_minutes == 60
        assert action.action_type == "calendar_block_time"
        assert action.show_as == "busy"

    def test_with_all_fields(self):
        """Test with all optional fields"""
        now = datetime.now(timezone.utc)
        action = CalendarBlockTimeAction(
            title="Deep Work",
            duration_minutes=120,
            preferred_start=now + timedelta(hours=2),
            preferred_end=now + timedelta(hours=6),
            show_as="tentative",
            categories=["focus", "work"],
        )
        assert action.duration_minutes == 120
        assert action.show_as == "tentative"
        assert len(action.categories) == 2

    def test_validate_success(self):
        """Test validation passes"""
        action = CalendarBlockTimeAction(
            title="Focus Time",
            duration_minutes=60,
        )
        result = action.validate()
        assert result.valid is True

    def test_validate_empty_title(self):
        """Test validation fails for empty title"""
        action = CalendarBlockTimeAction(
            title="",
            duration_minutes=60,
        )
        result = action.validate()
        assert result.valid is False

    def test_validate_duration_too_short(self):
        """Test validation fails for duration < 15 minutes"""
        action = CalendarBlockTimeAction(
            title="Focus",
            duration_minutes=10,
        )
        result = action.validate()
        assert result.valid is False
        assert any("15" in e for e in result.errors)

    def test_validate_duration_too_long_warning(self):
        """Test warning for very long duration"""
        action = CalendarBlockTimeAction(
            title="Focus",
            duration_minutes=600,  # 10 hours
        )
        result = action.validate()
        # Should still be valid but with warning
        assert any("8 hours" in w for w in result.warnings)

    def test_validate_invalid_show_as(self):
        """Test validation fails for invalid show_as"""
        action = CalendarBlockTimeAction(
            title="Focus",
            duration_minutes=60,
            show_as="invalid",
        )
        result = action.validate()
        assert result.valid is False

    def test_validate_start_after_end(self):
        """Test validation fails when preferred_start >= preferred_end"""
        now = datetime.now(timezone.utc)
        action = CalendarBlockTimeAction(
            title="Focus",
            duration_minutes=60,
            preferred_start=now + timedelta(hours=3),
            preferred_end=now + timedelta(hours=1),
        )
        result = action.validate()
        assert result.valid is False

    def test_execute_success(self):
        """Test successful execution"""
        action = CalendarBlockTimeAction(
            title="Focus Time",
            duration_minutes=60,
        )
        result = action.execute()
        assert result.success is True
        assert result.output["title"] == "Focus Time"
        assert result.output["duration_minutes"] == 60

    def test_supports_undo(self):
        """Test that action supports undo"""
        action = CalendarBlockTimeAction(
            title="Focus",
            duration_minutes=60,
        )
        assert action.supports_undo() is True
