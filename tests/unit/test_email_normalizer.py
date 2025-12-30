"""
Tests for Email Normalizer

Tests EmailNormalizer that converts EmailMetadata and EmailContent
into universal PerceivedEvent format.
"""

import pytest
from datetime import datetime
from src.core.events.normalizers import EmailNormalizer
from src.core.events import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
)
from src.core.schemas import EmailMetadata, EmailContent, EmailAttachment
from src.utils import now_utc


class TestEmailNormalizerBasic:
    """Basic EmailNormalizer functionality tests"""

    def test_normalize_simple_email(self):
        """Test normalizing a simple email"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg123@example.com>",
            subject="Test Subject",
            from_address="sender@example.com",
            from_name="Sender Name",
            to_addresses=["recipient@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=1024,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(
            plain_text="This is the email body.",
            html=None,
            attachments=[]
        )

        event = EmailNormalizer.normalize(metadata, content)

        assert isinstance(event, PerceivedEvent)
        assert event.source == EventSource.EMAIL
        assert event.source_id == "1"
        assert event.title == "Test Subject"
        assert event.content == "This is the email body."
        assert event.from_person == "sender@example.com"
        assert "recipient@example.com" in event.to_people
        assert event.perception_confidence == 0.7  # Default

    def test_normalize_with_custom_confidence(self):
        """Test normalizing with custom perception confidence"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Test",
            from_address="test@example.com",
            from_name="Test",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Test", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content, perception_confidence=0.95)

        assert event.perception_confidence == 0.95

    def test_event_id_generation(self):
        """Test event ID is generated consistently"""
        metadata = EmailMetadata(
            id=1,
            message_id="<unique123@example.com>",
            subject="Test",
            from_address="test@example.com",
            from_name="Test",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Test", html=None, attachments=[])

        event1 = EmailNormalizer.normalize(metadata, content)
        event2 = EmailNormalizer.normalize(metadata, content)

        # Same message_id should produce same event_id
        assert event1.event_id == event2.event_id

    def test_event_id_without_message_id(self):
        """Test event ID generation when message_id is None"""
        metadata = EmailMetadata(
            id=42,
            message_id=None,
            subject="Test",
            from_address="test@example.com",
            from_name="Test",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Test", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        # Should still generate an event_id
        assert event.event_id is not None
        assert len(event.event_id) == 16  # 16 character hex


class TestEntityExtraction:
    """Tests for entity extraction from emails"""

    def test_extract_sender_entity(self):
        """Test sender is extracted as person entity"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Test",
            from_address="john@example.com",
            from_name="John Doe",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Test", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        # Find sender entity
        sender_entities = [e for e in event.entities if e.metadata.get("role") == "sender"]
        assert len(sender_entities) == 1
        assert sender_entities[0].value == "john@example.com"
        assert sender_entities[0].type == "person"
        assert sender_entities[0].metadata["name"] == "John Doe"

    def test_extract_recipient_entities(self):
        """Test recipients are extracted as person entities"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Test",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["alice@example.com", "bob@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Test", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        # Find recipient entities
        recipient_entities = [e for e in event.entities if e.metadata.get("role") == "recipient"]
        assert len(recipient_entities) == 2
        recipient_values = [e.value for e in recipient_entities]
        assert "alice@example.com" in recipient_values
        assert "bob@example.com" in recipient_values


class TestEventTypeClassification:
    """Tests for event type classification"""

    def test_classify_action_required(self):
        """Test classification of action-required emails"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Please review this document",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(
            plain_text="Please can you review this?",
            html=None,
            attachments=[]
        )

        event = EmailNormalizer.normalize(metadata, content)

        assert event.event_type == EventType.ACTION_REQUIRED

    def test_classify_information(self):
        """Test classification of informational emails"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="FYI: Project Update",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(
            plain_text="For your information, the project is on track.",
            html=None,
            attachments=[]
        )

        event = EmailNormalizer.normalize(metadata, content)

        assert event.event_type == EventType.INFORMATION

    def test_classify_reply(self):
        """Test classification of reply emails"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Re: Previous discussion",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to="<prev@example.com>"
        )

        content = EmailContent(plain_text="Thanks for the update!", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert event.event_type == EventType.REPLY

    def test_classify_invitation(self):
        """Test classification of invitation emails"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Meeting invitation",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(
            plain_text="You are invited to the meeting next week.",
            html=None,
            attachments=[]
        )

        event = EmailNormalizer.normalize(metadata, content)

        assert event.event_type == EventType.INVITATION


class TestUrgencyDetermination:
    """Tests for urgency level determination"""

    def test_high_urgency_keywords(self):
        """Test high urgency from urgent keywords"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="URGENT: Action needed ASAP",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="This is critical!", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert event.urgency == UrgencyLevel.HIGH

    def test_high_urgency_flagged(self):
        """Test high urgency from flagged status"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Important message",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=["\\Flagged"],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Please review", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert event.urgency == UrgencyLevel.HIGH

    def test_medium_urgency_deadline(self):
        """Test medium urgency from deadline keywords"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Report due next week",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(
            plain_text="The deadline is approaching.",
            html=None,
            attachments=[]
        )

        event = EmailNormalizer.normalize(metadata, content)

        assert event.urgency == UrgencyLevel.MEDIUM

    def test_low_urgency_default(self):
        """Test low urgency as default"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="General update",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Just a friendly update.", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert event.urgency == UrgencyLevel.LOW


class TestTopicExtraction:
    """Tests for topic extraction"""

    def test_extract_subject_as_topic(self):
        """Test subject is extracted as primary topic"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Project Alpha Status Update",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Status update", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert len(event.topics) == 1
        assert event.topics[0] == "Project Alpha Status Update"

    def test_clean_subject_prefixes(self):
        """Test Re:/Fwd: prefixes are removed from topics"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Re: Fwd: Important Discussion",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Discussion", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert len(event.topics) == 1
        # Should have "Fwd: Important Discussion" (only first Re: removed)
        assert "Fwd:" in event.topics[0]
        assert event.topics[0].startswith("Fwd:")


class TestURLExtraction:
    """Tests for URL extraction"""

    def test_extract_urls_from_plain_text(self):
        """Test URLs are extracted from plain text"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Check this link",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(
            plain_text="Please visit https://example.com/page and http://test.com",
            html=None,
            attachments=[]
        )

        event = EmailNormalizer.normalize(metadata, content)

        assert len(event.urls) == 2
        assert "https://example.com/page" in event.urls
        assert "http://test.com" in event.urls

    def test_deduplicate_urls(self):
        """Test duplicate URLs are removed"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Links",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(
            plain_text="Visit https://example.com and also https://example.com again",
            html=None,
            attachments=[]
        )

        event = EmailNormalizer.normalize(metadata, content)

        assert len(event.urls) == 1
        assert "https://example.com" in event.urls


class TestAttachmentHandling:
    """Tests for attachment handling"""

    def test_extract_attachment_types(self):
        """Test attachment file types are extracted"""
        attachments = [
            EmailAttachment(filename="report.pdf", size_bytes=1024, content_type="application/pdf"),
            EmailAttachment(filename="data.xlsx", size_bytes=2048, content_type="application/vnd.ms-excel"),
            EmailAttachment(filename="photo.jpg", size_bytes=512, content_type="image/jpeg"),
        ]

        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Files attached",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=5000,
            has_attachments=True,
            attachments=attachments,
            references=[],
            in_reply_to=None
        )

        content = EmailContent(
            plain_text="See attached files",
            html=None,
            attachments=[a.filename for a in attachments]  # EmailContent wants just filenames
        )

        event = EmailNormalizer.normalize(metadata, content)

        assert event.has_attachments is True
        assert event.attachment_count == 3
        assert "pdf" in event.attachment_types
        assert "xlsx" in event.attachment_types
        assert "jpg" in event.attachment_types


class TestThreadInformation:
    """Tests for thread/conversation information"""

    def test_extract_thread_id_from_in_reply_to(self):
        """Test thread_id extracted from in_reply_to"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg2@example.com>",
            subject="Re: Discussion",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to="<msg1@example.com>"
        )

        content = EmailContent(plain_text="Reply", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert event.thread_id == "<msg1@example.com>"
        assert event.in_reply_to == "<msg1@example.com>"

    def test_extract_thread_id_from_message_id(self):
        """Test thread_id defaults to message_id for new threads"""
        metadata = EmailMetadata(
            id=1,
            message_id="<newthread@example.com>",
            subject="New Discussion",
            from_address="sender@example.com",
            from_name="Sender",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=[],
            folder="INBOX",
            size_bytes=500,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Starting new thread", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert event.thread_id == "<newthread@example.com>"
        assert event.in_reply_to is None


class TestMetadataPreservation:
    """Tests for preserving email-specific metadata"""

    def test_preserve_email_metadata(self):
        """Test email-specific metadata is preserved"""
        metadata = EmailMetadata(
            id=1,
            message_id="<msg@example.com>",
            subject="Test",
            from_address="sender@example.com",
            from_name="Sender Name",
            to_addresses=["me@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            date=now_utc(),
            flags=["\\Seen", "\\Important"],
            folder="Work/Projects",
            size_bytes=12345,
            has_attachments=False,
            attachments=[],
            references=[],
            in_reply_to=None
        )

        content = EmailContent(plain_text="Test", html=None, attachments=[])

        event = EmailNormalizer.normalize(metadata, content)

        assert event.metadata["email_flags"] == ["\\Seen", "\\Important"]
        assert event.metadata["email_folder"] == "Work/Projects"
        assert event.metadata["email_size_bytes"] == 12345
        assert event.metadata["email_message_id"] == "<msg@example.com>"
        assert event.metadata["email_from_name"] == "Sender Name"
