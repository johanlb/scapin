"""
Teams Message Normalizer

Converts Teams messages to the universal PerceivedEvent format
for processing by the cognitive pipeline.

Follows the same pattern as EmailNormalizer.
"""

import re
from dataclasses import dataclass

from src.core.events.universal_event import (
    Entity,
    EventSource,
    EventType,
    PerceivedEvent,
    UrgencyLevel,
)
from src.integrations.microsoft.models import (
    TeamsChatType,
    TeamsMessage,
    TeamsMessageImportance,
)
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("integrations.microsoft.teams_normalizer")


@dataclass
class TeamsNormalizer:
    """
    Normalizes Teams messages to PerceivedEvent

    Converts TeamsMessage dataclass to the universal event format
    used by the cognitive pipeline. Follows the same pattern as
    EmailNormalizer for consistency.

    Usage:
        normalizer = TeamsNormalizer()
        event = normalizer.normalize(message)
    """

    def normalize(self, message: TeamsMessage) -> PerceivedEvent:
        """
        Convert a Teams message to a PerceivedEvent

        Args:
            message: TeamsMessage to normalize

        Returns:
            PerceivedEvent ready for cognitive processing
        """
        logger.debug(f"Normalizing Teams message {message.message_id}")

        # Determine event type based on message characteristics
        event_type = self._determine_event_type(message)

        # Determine urgency based on importance and mentions
        urgency = self._determine_urgency(message)

        # Extract entities from message
        entities = self._extract_entities(message)

        # Extract topics and keywords
        topics, keywords = self._extract_topics_and_keywords(message)

        # Build title (truncated content for display)
        title = self._build_title(message)

        # Get participants
        from_person = message.sender.display_name
        if message.sender.email:
            from_person = f"{message.sender.display_name} <{message.sender.email}>"

        # Get chat topic if available
        chat_topic = message.chat.topic if message.chat else None

        # Build the PerceivedEvent
        event = PerceivedEvent(
            # Identity
            event_id=f"teams-{message.message_id}",
            source=EventSource.TEAMS,
            source_id=message.message_id,
            # Timing
            occurred_at=message.created_at,
            received_at=message.created_at,
            perceived_at=now_utc(),
            # Content
            title=title,
            content=message.content_plain,
            # Classification
            event_type=event_type,
            urgency=urgency,
            # Extracted info
            entities=entities,
            topics=topics,
            keywords=keywords,
            # Participants
            from_person=from_person,
            to_people=[],  # Teams doesn't have explicit recipients in chats
            cc_people=[],
            # Context
            thread_id=message.chat_id,
            references=[],
            in_reply_to=message.reply_to_id,
            # Attachments
            has_attachments=len(message.attachments) > 0,
            attachment_count=len(message.attachments),
            attachment_types=list(message.attachments),
            urls=self._extract_urls(message.content),
            # Metadata
            metadata={
                "message_id": message.message_id,
                "chat_id": message.chat_id,
                "sender_id": message.sender.user_id,
                "sender_name": message.sender.display_name,
                "sender_email": message.sender.email,
                "importance": message.importance.value,
                "chat_type": message.chat.chat_type.value if message.chat else None,
                "chat_topic": chat_topic,
                "mentions": list(message.mentions),
                "is_reply": message.is_reply,
            },
            # Quality
            perception_confidence=0.8,  # Base confidence for Teams messages
            needs_clarification=False,
            clarification_questions=[],
        )

        logger.debug(f"Normalized message to event {event.event_id} (type={event_type.value})")
        return event

    def _determine_event_type(self, message: TeamsMessage) -> EventType:
        """
        Determine the event type based on message characteristics

        Uses heuristics based on:
        - Message importance
        - Presence of mentions
        - Chat type
        - Content patterns
        """
        # Urgent messages are action required
        if message.importance == TeamsMessageImportance.URGENT:
            return EventType.ACTION_REQUIRED

        # High importance is also likely action needed
        if message.importance == TeamsMessageImportance.HIGH:
            return EventType.ACTION_REQUIRED

        # If user is mentioned, likely needs attention
        if message.mentions:
            return EventType.REQUEST

        # Replies are... replies
        if message.is_reply:
            return EventType.REPLY

        # Meeting chats might be status updates
        if message.chat and message.chat.chat_type == TeamsChatType.MEETING:
            return EventType.INFORMATION

        # Default to information
        return EventType.INFORMATION

    def _determine_urgency(self, message: TeamsMessage) -> UrgencyLevel:
        """
        Determine urgency based on message importance and context
        """
        if message.importance == TeamsMessageImportance.URGENT:
            return UrgencyLevel.CRITICAL

        if message.importance == TeamsMessageImportance.HIGH:
            return UrgencyLevel.HIGH

        # If mentioned, it's at least medium priority
        if message.mentions:
            return UrgencyLevel.MEDIUM

        return UrgencyLevel.LOW

    def _extract_entities(self, message: TeamsMessage) -> list[Entity]:
        """
        Extract entities from the message

        Extracts:
        - Sender as person entity
        - Mentioned users as person entities
        """
        entities: list[Entity] = []

        # Sender
        entities.append(Entity(
            type="person",
            value=message.sender.display_name,
            confidence=0.95,
            metadata={
                "user_id": message.sender.user_id,
                "email": message.sender.email,
                "role": "sender",
            },
        ))

        # Mentioned users (we only have IDs, not names)
        for user_id in message.mentions:
            entities.append(Entity(
                type="person",
                value=user_id,  # Would be resolved to name if available
                confidence=0.90,
                metadata={
                    "user_id": user_id,
                    "role": "mentioned",
                },
            ))

        # Chat topic as project/topic if available
        if message.chat and message.chat.topic:
            entities.append(Entity(
                type="topic",
                value=message.chat.topic,
                confidence=0.85,
                metadata={
                    "chat_id": message.chat.chat_id,
                    "source": "chat_topic",
                },
            ))

        return entities

    def _extract_topics_and_keywords(
        self,
        message: TeamsMessage,
    ) -> tuple[list[str], list[str]]:
        """
        Extract topics and keywords from message content

        For now, uses simple heuristics. Could be enhanced with NLP.
        """
        topics: list[str] = []
        keywords: list[str] = []

        # Use chat topic as a topic
        if message.chat and message.chat.topic:
            topics.append(message.chat.topic)

        # Simple keyword extraction (words that appear frequently or are important)
        # This is a placeholder - real implementation would use NLP
        content = message.content_plain.lower()
        important_words = ["urgent", "important", "deadline", "meeting", "review"]
        for word in important_words:
            if word in content:
                keywords.append(word)

        return topics, keywords

    def _build_title(self, message: TeamsMessage) -> str:
        """
        Build a title from the message content

        Uses first line or truncated content.
        """
        content = message.content_plain.strip()

        if not content:
            return "(empty message)"

        # Use first line
        first_line = content.split("\n")[0].strip()

        # Truncate if too long
        max_len = 100
        if len(first_line) > max_len:
            return first_line[:max_len - 3] + "..."

        return first_line

    def _extract_urls(self, html_content: str) -> list[str]:
        """
        Extract URLs from HTML content

        Simple regex extraction. Could be enhanced.
        """
        if not html_content:
            return []

        # Find href attributes
        href_pattern = r'href=["\']([^"\']+)["\']'
        urls = re.findall(href_pattern, html_content)

        # Also find plain URLs
        url_pattern = r'https?://[^\s<>"\']+(?=[<"\'\s]|$)'
        plain_urls = re.findall(url_pattern, html_content)

        # Combine and dedupe
        all_urls = list(set(urls + plain_urls))

        return all_urls
