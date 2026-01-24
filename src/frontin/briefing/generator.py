"""
Briefing Generator

Core briefing generation system that aggregates data from multiple sources
(Email, Calendar, Teams) and produces structured briefings.

Uses the existing processors to fetch normalized PerceivedEvents,
then ranks and organizes them for display.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional, Protocol

from src.core.config_manager import BriefingConfig
from src.core.events import EventSource, PerceivedEvent, UrgencyLevel
from src.frontin.briefing.models import (
    AttendeeContext,
    BriefingItem,
    MorningBriefing,
    OrphanQuestionItem,
    PendingRetoucheAction,
    PreMeetingBriefing,
    RetoucheAlertItem,
)
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("frontin.briefing.generator")


class BriefingDataProvider(Protocol):
    """
    Protocol for fetching briefing data from various sources

    Allows abstraction over the actual data sources (processors),
    making the generator testable with mock providers.
    """

    async def get_emails_since(
        self,
        since: datetime,
        limit: int = 50,
    ) -> list[PerceivedEvent]:
        """Get emails received since the given datetime"""
        ...

    async def get_calendar_events(
        self,
        hours_ahead: int,
        include_in_progress: bool = True,
    ) -> list[PerceivedEvent]:
        """Get upcoming calendar events"""
        ...

    async def get_teams_messages(
        self,
        since: datetime,
        limit: int = 50,
    ) -> list[PerceivedEvent]:
        """Get Teams messages since the given datetime"""
        ...

    async def get_emails_with_people(
        self,
        emails: list[str],
        days: int = 7,
    ) -> list[PerceivedEvent]:
        """Get emails involving specific people"""
        ...

    async def get_teams_with_people(
        self,
        emails: list[str],
        days: int = 7,
    ) -> list[PerceivedEvent]:
        """Get Teams messages involving specific people"""
        ...


@dataclass
class DefaultBriefingDataProvider:
    """
    Default data provider using actual processors

    Connects to CalendarProcessor, EmailProcessor, and TeamsProcessor
    to fetch real data from the configured sources.
    """

    _calendar_processor: Any = field(default=None, repr=False)
    _email_processor: Any = field(default=None, repr=False)
    _teams_processor: Any = field(default=None, repr=False)

    async def get_emails_since(
        self,
        since: datetime,
        limit: int = 50,  # noqa: ARG002
    ) -> list[PerceivedEvent]:
        """Get emails received since the given datetime"""
        # TODO: Implement when EmailProcessor supports this query
        # For now, return empty list
        logger.debug(f"get_emails_since({since}, limit={limit}) - not yet implemented")
        return []

    async def get_calendar_events(
        self,
        hours_ahead: int,
        include_in_progress: bool = True,  # noqa: ARG002
    ) -> list[PerceivedEvent]:
        """Get upcoming calendar events using CalendarProcessor"""
        try:
            from src.trivelin.calendar_processor import CalendarProcessor

            if self._calendar_processor is None:
                self._calendar_processor = CalendarProcessor()

            return await self._calendar_processor.get_briefing(hours_ahead=hours_ahead)
        except Exception as e:
            logger.warning(f"Failed to get calendar events: {e}")
            return []

    async def get_teams_messages(
        self,
        since: datetime,
        limit: int = 50,  # noqa: ARG002
    ) -> list[PerceivedEvent]:
        """Get Teams messages since the given datetime"""
        # TODO: Implement when TeamsProcessor supports this query
        # For now, return empty list
        logger.debug(f"get_teams_messages({since}, limit={limit}) - not yet implemented")
        return []

    async def get_emails_with_people(
        self,
        emails: list[str],
        days: int = 7,  # noqa: ARG002
    ) -> list[PerceivedEvent]:
        """Get emails involving specific people"""
        # TODO: Implement when EmailProcessor supports this query
        logger.debug(f"get_emails_with_people({emails}, days={days}) - not yet implemented")
        return []

    async def get_teams_with_people(
        self,
        emails: list[str],
        days: int = 7,  # noqa: ARG002
    ) -> list[PerceivedEvent]:
        """Get Teams messages involving specific people"""
        # TODO: Implement when TeamsProcessor supports this query
        logger.debug(f"get_teams_with_people({emails}, days={days}) - not yet implemented")
        return []


@dataclass
class BriefingGenerator:
    """
    Generates briefings from multiple sources

    Uses data providers to fetch normalized PerceivedEvents from various
    sources (Email, Calendar, Teams), then aggregates and ranks them for display.

    Supports two briefing types:
    - Morning Briefing: Overview of the day ahead
    - Pre-Meeting Briefing: Context for an upcoming meeting

    Usage:
        generator = BriefingGenerator(config=briefing_config)

        # Morning briefing
        morning = await generator.generate_morning_briefing()

        # Pre-meeting briefing
        event = await calendar_processor.get_event(event_id)
        pre_meeting = await generator.generate_pre_meeting_briefing(event)
    """

    config: BriefingConfig
    data_provider: Optional[BriefingDataProvider] = None

    def __post_init__(self) -> None:
        """Initialize default data provider if not provided"""
        if self.data_provider is None:
            self.data_provider = DefaultBriefingDataProvider()

    async def generate_morning_briefing(
        self,
        target_date: Optional[date] = None,
    ) -> MorningBriefing:
        """
        Generate morning briefing for the day

        Aggregates:
        - Calendar events for the next N hours
        - Unread/pending emails from last N hours
        - Unread Teams messages

        Ranks by urgency and temporal proximity.

        Args:
            target_date: Date for the briefing (default: today)

        Returns:
            MorningBriefing with aggregated items
        """
        target_date = target_date or date.today()
        now = now_utc()

        logger.info(f"Generating morning briefing for {target_date}")

        # Fetch data from all enabled sources
        calendar_events: list[PerceivedEvent] = []
        email_events: list[PerceivedEvent] = []
        teams_events: list[PerceivedEvent] = []

        if self.config.include_calendar:
            calendar_events = await self._fetch_calendar(
                hours_ahead=self.config.morning_hours_ahead
            )

        if self.config.include_emails:
            email_events = await self._fetch_emails(
                hours_behind=self.config.morning_hours_behind
            )

        if self.config.include_teams:
            teams_events = await self._fetch_teams(
                hours_behind=self.config.morning_hours_behind
            )

        # Combine all events and extract urgent ones
        all_events = calendar_events + email_events + teams_events
        urgent_items = self._extract_urgent(all_events)

        # Count meetings (events with attendees > 1)
        meetings_count = sum(
            1 for e in calendar_events
            if e.metadata.get("attendee_count", 0) > 1
        )

        # Load orphan strategic questions (v3.2)
        orphan_question_items = self._load_orphan_questions()

        # Load retouche alerts (v3.3 - Phase 6)
        retouche_alert_items = self._load_retouche_alerts()

        # Load pending retouche actions awaiting approval (v3.3 - Lifecycle)
        pending_action_items = self._load_pending_retouche_actions()

        # Build briefing
        briefing = MorningBriefing(
            date=target_date,
            generated_at=now,
            urgent_items=urgent_items[:self.config.max_urgent_items],
            calendar_today=self._to_briefing_items(
                calendar_events[:self.config.max_standard_items]
            ),
            emails_pending=self._to_briefing_items(
                email_events[:self.config.max_standard_items]
            ),
            teams_unread=self._to_briefing_items(
                teams_events[:self.config.max_standard_items]
            ),
            orphan_questions=orphan_question_items,
            retouche_alerts=retouche_alert_items,
            pending_retouche_actions=pending_action_items,
            total_items=len(all_events),
            urgent_count=len(urgent_items),
            meetings_today=meetings_count,
            orphan_questions_count=len(orphan_question_items),
            retouche_alerts_count=len(retouche_alert_items),
            pending_retouche_count=len(pending_action_items),
        )

        # Generate AI summary if enabled
        if self.config.show_confidence and briefing.total_items > 0:
            briefing.ai_summary = self._generate_summary(briefing)

        logger.info(
            f"Morning briefing generated: {briefing.urgent_count} urgent, "
            f"{briefing.total_items} total items, {briefing.retouche_alerts_count} retouche alerts"
        )

        return briefing

    async def generate_pre_meeting_briefing(
        self,
        event: PerceivedEvent,
    ) -> PreMeetingBriefing:
        """
        Generate pre-meeting briefing with context

        Fetches:
        - Attendee information and relationship context
        - Recent emails with attendees
        - Recent Teams messages with attendees
        - AI-generated talking points

        Args:
            event: The calendar event for the meeting

        Returns:
            PreMeetingBriefing with context
        """
        now = now_utc()

        # Parse start time from metadata
        start_str = event.metadata.get("start")
        if start_str:
            start_time = datetime.fromisoformat(start_str)
            # Ensure timezone aware
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
        else:
            start_time = now

        # Allow negative values to indicate meeting in progress
        minutes_until = int((start_time - now).total_seconds() / 60)

        logger.info(
            f"Generating pre-meeting briefing for '{event.title}' "
            f"in {minutes_until} min"
        )

        # Extract attendee emails
        attendee_emails = self._extract_attendee_emails(event)

        # Fetch related communications
        recent_emails: list[PerceivedEvent] = []
        recent_teams: list[PerceivedEvent] = []

        if attendee_emails and self.data_provider:
            recent_emails = await self.data_provider.get_emails_with_people(
                attendee_emails,
                days=self.config.pre_meeting_context_days,
            )
            recent_teams = await self.data_provider.get_teams_with_people(
                attendee_emails,
                days=self.config.pre_meeting_context_days,
            )

        # Build attendee context
        attendees = self._build_attendee_context(
            event,
            recent_emails + recent_teams,
        )

        # Build briefing
        briefing = PreMeetingBriefing(
            event=event,
            generated_at=now,
            minutes_until_start=minutes_until,
            attendees=attendees,
            recent_emails=recent_emails[:5],
            recent_teams=recent_teams[:5],
            meeting_url=event.metadata.get("online_url"),
            location=event.metadata.get("location"),
        )

        # Generate talking points based on available context
        briefing.talking_points = self._generate_talking_points(briefing)

        logger.info(
            f"Pre-meeting briefing generated: {len(attendees)} attendees, "
            f"{len(recent_emails)} related emails"
        )

        return briefing

    async def _fetch_calendar(
        self,
        hours_ahead: int,
    ) -> list[PerceivedEvent]:
        """Fetch calendar events for the specified hours ahead"""
        if self.data_provider is None:
            return []

        try:
            events = await self.data_provider.get_calendar_events(
                hours_ahead=hours_ahead,
                include_in_progress=True,
            )
            logger.debug(f"Fetched {len(events)} calendar events")
            return events
        except Exception as e:
            logger.warning(f"Failed to fetch calendar events: {e}")
            return []

    async def _fetch_emails(
        self,
        hours_behind: int,
    ) -> list[PerceivedEvent]:
        """Fetch emails from the specified hours behind"""
        if self.data_provider is None:
            return []

        try:
            since = now_utc() - timedelta(hours=hours_behind)
            events = await self.data_provider.get_emails_since(
                since=since,
                limit=50,
            )
            logger.debug(f"Fetched {len(events)} emails")
            return events
        except Exception as e:
            logger.warning(f"Failed to fetch emails: {e}")
            return []

    async def _fetch_teams(
        self,
        hours_behind: int,
    ) -> list[PerceivedEvent]:
        """Fetch Teams messages from the specified hours behind"""
        if self.data_provider is None:
            return []

        try:
            since = now_utc() - timedelta(hours=hours_behind)
            events = await self.data_provider.get_teams_messages(
                since=since,
                limit=50,
            )
            logger.debug(f"Fetched {len(events)} Teams messages")
            return events
        except Exception as e:
            logger.warning(f"Failed to fetch Teams messages: {e}")
            return []

    def _load_orphan_questions(self) -> list[OrphanQuestionItem]:
        """
        Load pending orphan strategic questions for the briefing.

        Orphan questions are strategic questions generated during email analysis
        that don't have a target note to attach to.

        Returns:
            List of OrphanQuestionItem for display in the briefing
        """
        try:
            from src.integrations.storage.orphan_questions_storage import (
                get_orphan_questions_storage,
            )

            storage = get_orphan_questions_storage()
            pending = storage.get_pending_questions()

            items = [
                OrphanQuestionItem(
                    question_id=q.question_id,
                    question=q.question,
                    category=q.category,
                    context=q.context,
                    source_valet=q.source_valet,
                    source_email_subject=q.source_email_subject,
                    created_at=q.created_at,
                    intended_target=q.intended_target,
                )
                for q in pending
            ]

            logger.debug(f"Loaded {len(items)} orphan questions for briefing")
            return items

        except Exception as e:
            logger.warning(f"Failed to load orphan questions: {e}")
            return []

    def _load_retouche_alerts(self) -> list[RetoucheAlertItem]:
        """
        Load pending retouche alerts for the briefing.

        Retouche alerts are proactive suggestions from the retouche system:
        - Contacts not contacted in a while
        - Projects without recent activity
        - OmniFocus task suggestions

        Returns:
            List of RetoucheAlertItem for display in the briefing
        """
        try:
            from pathlib import Path

            from src.passepartout.note_manager import NoteManager
            from src.passepartout.note_metadata import NoteMetadataStore

            # Get metadata store
            data_dir = Path("data")
            meta_store = NoteMetadataStore(data_dir / "notes_meta.db")
            note_manager = NoteManager(data_dir / "notes_cache.db")

            alerts: list[RetoucheAlertItem] = []

            # Look for recent retouches with proactive actions
            recent_notes = meta_store.get_recently_retouched(hours=48, limit=100)

            for meta in recent_notes:
                # Check enrichment history for proactive alerts
                for record in meta.enrichment_history[-10:]:  # Last 10 records
                    if not record.applied:
                        continue

                    # Filter for proactive action types
                    if record.action_type in ("suggest_contact", "flag_stale", "create_omnifocus"):
                        # Get note info
                        note = note_manager.get_note(meta.note_id)
                        if note is None:
                            continue

                        alert = RetoucheAlertItem(
                            note_id=meta.note_id,
                            note_title=note.title,
                            note_path=note.path or "",
                            alert_type=record.action_type,
                            message=record.reasoning or record.content or "",
                            confidence=record.confidence,
                            created_at=record.timestamp.isoformat(),
                        )
                        alerts.append(alert)

            # Deduplicate by note_id + alert_type (keep most recent)
            seen = set()
            unique_alerts = []
            for alert in sorted(alerts, key=lambda a: a.created_at or "", reverse=True):
                key = (alert.note_id, alert.alert_type)
                if key not in seen:
                    seen.add(key)
                    unique_alerts.append(alert)

            logger.debug(f"Loaded {len(unique_alerts)} retouche alerts for briefing")
            return unique_alerts[:10]  # Limit to 10 alerts

        except Exception as e:
            logger.warning(f"Failed to load retouche alerts: {e}")
            return []

    def _load_pending_retouche_actions(self) -> list[PendingRetoucheAction]:
        """
        Load pending retouche actions awaiting human approval.

        These are lifecycle actions (FLAG_OBSOLETE, MERGE_INTO, MOVE_TO_FOLDER)
        that require explicit human decision in the Filage before being applied.

        Returns:
            List of PendingRetoucheAction for display in the briefing
        """
        try:
            from pathlib import Path

            from src.passepartout.note_manager import NoteManager
            from src.passepartout.note_metadata import NoteMetadataStore

            # Get metadata store
            data_dir = Path("data")
            meta_store = NoteMetadataStore(data_dir / "notes_meta.db")
            note_manager = NoteManager(data_dir / "notes_cache.db")

            actions: list[PendingRetoucheAction] = []

            # Get notes with pending actions
            notes_with_pending = meta_store.get_notes_with_pending_actions(limit=50)

            for meta in notes_with_pending:
                # Get note info
                note = note_manager.get_note(meta.note_id)
                if note is None:
                    continue

                for action_data in meta.pending_actions:
                    action = PendingRetoucheAction(
                        action_id=action_data.get("id", ""),
                        note_id=meta.note_id,
                        note_title=note.title,
                        note_path=note.path or "",
                        action_type=action_data.get("type", "unknown"),
                        confidence=action_data.get("confidence", 0.0),
                        reasoning=action_data.get("reasoning", ""),
                        target_note_id=action_data.get("target_note_id"),
                        target_note_title=action_data.get("target_note_title"),
                        target_folder=action_data.get("target_folder"),
                        created_at=action_data.get("created_at"),
                    )
                    actions.append(action)

            logger.debug(f"Loaded {len(actions)} pending retouche actions for briefing")
            return actions[:20]  # Limit to 20 actions

        except Exception as e:
            logger.warning(f"Failed to load pending retouche actions: {e}")
            return []

    def _extract_urgent(
        self,
        events: list[PerceivedEvent],
    ) -> list[BriefingItem]:
        """
        Extract and rank urgent items from all events

        An item is urgent if:
        - Has HIGH or CRITICAL urgency level
        - Is a calendar event starting within 3 hours
        - Has explicit urgency markers in content

        Returns items sorted by urgency then temporal proximity.
        """
        urgent_items: list[BriefingItem] = []
        now = now_utc()

        for event in events:
            is_urgent = False
            urgency_score = 0  # Higher = more urgent

            # Check urgency level
            if event.urgency == UrgencyLevel.CRITICAL:
                is_urgent = True
                urgency_score = 100
            elif event.urgency == UrgencyLevel.HIGH:
                is_urgent = True
                urgency_score = 80

            # Calendar events in next 3 hours are urgent
            if event.source == EventSource.CALENDAR:
                start_str = event.metadata.get("start")
                if start_str:
                    try:
                        start_dt = datetime.fromisoformat(start_str)
                        if start_dt.tzinfo is None:
                            start_dt = start_dt.replace(tzinfo=timezone.utc)
                        hours_until = (start_dt - now).total_seconds() / 3600

                        if 0 <= hours_until <= 3:
                            is_urgent = True
                            # More urgent the closer it is
                            urgency_score = max(urgency_score, 90 - int(hours_until * 20))
                    except (ValueError, TypeError):
                        pass

            if is_urgent:
                item = BriefingItem(
                    event=event,
                    priority_rank=urgency_score,  # Will be reranked below
                    time_context=self._format_time_context(event),
                    confidence=event.perception_confidence,
                )
                urgent_items.append(item)

        # Sort by urgency score (highest first) then rerank
        urgent_items.sort(key=lambda x: -x.priority_rank)

        # Reassign priority_rank to sequential order
        return [
            BriefingItem(
                event=item.event,
                priority_rank=i + 1,
                time_context=item.time_context,
                action_summary=item.action_summary,
                confidence=item.confidence,
            )
            for i, item in enumerate(urgent_items)
        ]

    def _to_briefing_item(
        self,
        event: PerceivedEvent,
        rank: int,
    ) -> BriefingItem:
        """Convert a PerceivedEvent to a BriefingItem"""
        return BriefingItem(
            event=event,
            priority_rank=rank,
            time_context=self._format_time_context(event),
            confidence=event.perception_confidence,
        )

    def _to_briefing_items(
        self,
        events: list[PerceivedEvent],
    ) -> list[BriefingItem]:
        """Convert a list of events to briefing items"""
        return [
            self._to_briefing_item(event, i + 1)
            for i, event in enumerate(events)
        ]

    def _format_time_context(self, event: PerceivedEvent) -> str:
        """
        Format human-readable time context for an event

        For calendar events: time until start (or "In progress")
        For emails/teams: time since received
        """
        now = now_utc()

        if event.source == EventSource.CALENDAR:
            start_str = event.metadata.get("start")
            if start_str:
                try:
                    start_dt = datetime.fromisoformat(start_str)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)

                    delta = start_dt - now
                    hours = delta.total_seconds() / 3600

                    if hours < -0.5:
                        return "In progress"
                    elif hours < 0:
                        return "Starting now"
                    elif hours < 1:
                        mins = max(1, int(hours * 60))
                        return f"In {mins} min"
                    elif hours < 24:
                        return start_dt.strftime("%H:%M")
                    else:
                        return start_dt.strftime("%a %H:%M")
                except (ValueError, TypeError):
                    pass
            return "Scheduled"

        # For emails/teams - time since received
        received = event.received_at
        if received.tzinfo is None:
            received = received.replace(tzinfo=timezone.utc)

        delta = now - received
        hours = delta.total_seconds() / 3600

        if hours < 0.5:
            return "Just now"
        elif hours < 1:
            return f"{int(hours * 60)} min ago"
        elif hours < 24:
            return f"{int(hours)}h ago"
        else:
            return received.strftime("%a %H:%M")

    def _extract_attendee_emails(self, event: PerceivedEvent) -> list[str]:
        """Extract attendee email addresses from a calendar event"""
        attendees = event.metadata.get("attendees", [])
        emails: list[str] = []

        for att in attendees:
            if isinstance(att, dict):
                email = att.get("email")
                if email:
                    emails.append(email)
            elif isinstance(att, str) and "@" in att:
                emails.append(att)

        return emails

    def _build_attendee_context(
        self,
        event: PerceivedEvent,
        related_events: list[PerceivedEvent],
    ) -> list[AttendeeContext]:
        """
        Build attendee context from event metadata and related communications

        Counts interactions with each attendee and generates relationship hints.
        """
        attendees: list[AttendeeContext] = []
        attendee_data = event.metadata.get("attendees", [])
        organizer_email = event.metadata.get("organizer_email", "")

        # Count interactions per email
        interaction_counts: dict[str, int] = {}
        last_interactions: dict[str, datetime] = {}

        for rel_event in related_events:
            from_email = self._extract_email_from_person(rel_event.from_person)
            if from_email:
                interaction_counts[from_email] = interaction_counts.get(from_email, 0) + 1
                existing = last_interactions.get(from_email)
                if existing is None or rel_event.received_at > existing:
                    last_interactions[from_email] = rel_event.received_at

        for att in attendee_data:
            if isinstance(att, dict):
                name = att.get("name", "Unknown")
                email = att.get("email", "")
            else:
                continue

            is_organizer = email.lower() == organizer_email.lower() if organizer_email else False
            email_key = email.lower()  # Normalize for lookup (keys are lowercase)
            count = interaction_counts.get(email_key, 0)
            last_interaction = last_interactions.get(email_key)

            # Generate relationship hint
            hint: Optional[str] = None
            if count >= 10:
                hint = "Frequent contact"
            elif count >= 3:
                hint = "Regular contact"
            elif count == 0:
                hint = "New contact"

            attendees.append(AttendeeContext(
                name=name,
                email=email,
                is_organizer=is_organizer,
                last_interaction=last_interaction,
                interaction_count=count,
                relationship_hint=hint,
            ))

        # Sort: organizer first, then by interaction count
        attendees.sort(
            key=lambda a: (not a.is_organizer, -a.interaction_count)
        )

        return attendees

    def _extract_email_from_person(self, person: str) -> Optional[str]:
        """Extract email address from a person string like 'Name <email@example.com>'"""
        if not person:
            return None

        # Handle "Name <email@example.com>" format
        if "<" in person and ">" in person:
            start = person.index("<") + 1
            end = person.index(">")
            if start < end:  # Ensure valid brackets
                email = person[start:end].strip().lower()
                if "@" in email:  # Validate it's actually an email
                    return email

        # Handle plain email format
        if "@" in person:
            # Extract just the email part if mixed with other text
            parts = person.split()
            for part in parts:
                if "@" in part:
                    return part.strip("<>").lower()

        return None

    def _generate_summary(self, briefing: MorningBriefing) -> str:
        """
        Generate an AI summary for the morning briefing

        For now, returns a structured summary. In the future, this could
        use the ReasoningEngine for a more intelligent summary.
        """
        parts: list[str] = []

        if briefing.urgent_count > 0:
            parts.append(f"{briefing.urgent_count} urgent items need attention")

        if briefing.meetings_today > 0:
            parts.append(f"{briefing.meetings_today} meetings scheduled today")

        email_count = len(briefing.emails_pending)
        teams_count = len(briefing.teams_unread)

        if email_count > 0 or teams_count > 0:
            comm_parts: list[str] = []
            if email_count > 0:
                comm_parts.append(f"{email_count} emails")
            if teams_count > 0:
                comm_parts.append(f"{teams_count} Teams messages")
            parts.append(f"Communications pending: {', '.join(comm_parts)}")

        if not parts:
            return "No significant items for today."

        return ". ".join(parts) + "."

    def _generate_talking_points(
        self,
        briefing: PreMeetingBriefing,
    ) -> list[str]:
        """
        Generate talking points for a pre-meeting briefing

        Based on available context (recent communications, attendees, etc.)
        """
        points: list[str] = []

        # Add context about recent communications
        if briefing.recent_emails:
            points.append(
                f"Review {len(briefing.recent_emails)} recent email(s) with attendees"
            )

        if briefing.recent_teams:
            points.append(
                f"Check {len(briefing.recent_teams)} recent Teams message(s) with attendees"
            )

        # Add note about new contacts
        new_contacts = [a for a in briefing.attendees if a.relationship_hint == "New contact"]
        if new_contacts:
            names = [a.name for a in new_contacts[:2]]
            if len(new_contacts) > 2:
                points.append(
                    f"Meeting new contacts: {', '.join(names)} and {len(new_contacts) - 2} others"
                )
            else:
                points.append(f"Meeting new contacts: {', '.join(names)}")

        # Add preparation reminder if meeting starts soon
        if briefing.minutes_until_start <= 5:
            points.append("Meeting starts very soon - prepare now!")
        elif briefing.minutes_until_start <= 15:
            points.append("Final preparation time before meeting")

        return points
