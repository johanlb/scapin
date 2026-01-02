"""
Unit tests for Pydantic schemas
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.core.schemas import (
    ConversationContext,
    ConversationMessage,
    DecisionRecord,
    EmailAction,
    EmailAnalysis,
    EmailCategory,
    EmailContent,
    EmailMetadata,
    FSRSCard,
    FSRSReview,
    HealthCheck,
    KnowledgeEntry,
    KnowledgeQuery,
    ProcessedEmail,
    ProcessingMode,
    ReviewGrade,
    ServiceStatus,
    SystemHealth,
)


class TestEnums:
    """Test enum values"""

    def test_email_action_values(self):
        """Test EmailAction enum"""
        assert EmailAction.DELETE == "delete"
        assert EmailAction.ARCHIVE == "archive"
        assert EmailAction.REFERENCE == "reference"
        assert EmailAction.KEEP == "keep"
        assert EmailAction.TASK == "task"

    def test_email_category_values(self):
        """Test EmailCategory enum"""
        assert EmailCategory.PERSONAL == "personal"
        assert EmailCategory.WORK == "work"
        assert EmailCategory.FINANCE == "finance"

    def test_review_grade_values(self):
        """Test ReviewGrade enum"""
        assert ReviewGrade.AGAIN == "again"
        assert ReviewGrade.HARD == "hard"
        assert ReviewGrade.GOOD == "good"
        assert ReviewGrade.EASY == "easy"

    def test_processing_mode_values(self):
        """Test ProcessingMode enum"""
        assert ProcessingMode.AUTO == "auto"
        assert ProcessingMode.LEARNING == "learning"
        assert ProcessingMode.REVIEW == "review"


class TestEmailMetadata:
    """Test EmailMetadata schema"""

    def test_valid_email_metadata(self):
        """Test creating valid EmailMetadata"""
        metadata = EmailMetadata(
            id=12345,
            folder="INBOX",
            from_address="test@example.com",
            from_name="Test User",
            subject="Test Email",
            date=datetime.now(),
        )

        assert metadata.id == 12345
        assert metadata.folder == "INBOX"
        assert metadata.from_address == "test@example.com"
        assert metadata.subject == "Test Email"

    def test_email_metadata_subject_validation(self):
        """Test subject cannot be empty"""
        with pytest.raises(ValidationError):
            EmailMetadata(
                id=123,
                from_address="test@example.com",
                subject="   ",  # Empty after stripping
                date=datetime.now(),
            )

    def test_email_metadata_defaults(self):
        """Test default values"""
        metadata = EmailMetadata(
            id=123,
            from_address="test@example.com",
            subject="Test",
            date=datetime.now(),
        )

        assert metadata.folder == "INBOX"
        assert metadata.has_attachments is False
        assert metadata.flags == []

    def test_email_metadata_invalid_email(self):
        """Test invalid email address"""
        with pytest.raises(ValidationError):
            EmailMetadata(
                id=123,
                from_address="not-an-email",  # Invalid email
                subject="Test",
                date=datetime.now(),
            )


class TestEmailContent:
    """Test EmailContent schema"""

    def test_valid_email_content(self):
        """Test creating valid EmailContent"""
        content = EmailContent(
            plain_text="This is the email body",
            preview="This is the email body",
        )

        assert content.plain_text == "This is the email body"
        assert content.preview == "This is the email body"

    def test_email_content_preview_max_length(self):
        """Test preview is truncated to 500 chars"""
        long_text = "a" * 1000

        # Should not raise, max_length is enforced
        content = EmailContent(preview=long_text[:500])
        assert len(content.preview) == 500


class TestEmailAnalysis:
    """Test EmailAnalysis schema"""

    def test_valid_email_analysis(self):
        """Test creating valid EmailAnalysis"""
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.WORK,
            destination="Archive/2024",
            confidence=95,
            reasoning="This is work-related and should be archived",
        )

        assert analysis.action == EmailAction.ARCHIVE
        assert analysis.confidence == 95
        assert analysis.destination == "Archive/2024"

    def test_confidence_range_validation(self):
        """Test confidence must be 0-100"""
        # Too high - should raise ValidationError
        with pytest.raises(ValidationError):
            EmailAnalysis(
                action=EmailAction.DELETE,
                category=EmailCategory.SPAM,
                confidence=150,  # Out of range
                reasoning="Spam email",
            )

        # Too low - should raise ValidationError
        with pytest.raises(ValidationError):
            EmailAnalysis(
                action=EmailAction.KEEP,
                category=EmailCategory.OTHER,
                confidence=-10,  # Out of range
                reasoning="Unknown category, needs review",
            )

    def test_reasoning_min_length(self):
        """Test reasoning must be at least 10 chars"""
        with pytest.raises(ValidationError):
            EmailAnalysis(
                action=EmailAction.DELETE,
                category=EmailCategory.SPAM,
                confidence=100,
                reasoning="Short",  # Too short
            )


class TestProcessedEmail:
    """Test ProcessedEmail schema"""

    def test_valid_processed_email(self):
        """Test creating valid ProcessedEmail"""
        metadata = EmailMetadata(
            id=123,
            from_address="test@example.com",
            subject="Test",
            date=datetime.now(),
        )
        content = EmailContent(preview="Preview text")

        email = ProcessedEmail(metadata=metadata, content=content)

        assert email.metadata.id == 123
        assert email.content.preview == "Preview text"
        assert email.analysis is None
        assert email.is_correction is False


class TestDecisionRecord:
    """Test DecisionRecord schema"""

    def test_valid_decision_record(self):
        """Test creating valid DecisionRecord"""
        metadata = EmailMetadata(
            id=123,
            from_address="test@example.com",
            subject="Test",
            date=datetime.now(),
        )

        decision = DecisionRecord(
            id="decision-123",
            email_metadata=metadata,
            user_action=EmailAction.ARCHIVE,
            user_destination="Archive/2024",
            processing_mode=ProcessingMode.AUTO,
        )

        assert decision.id == "decision-123"
        assert decision.user_action == EmailAction.ARCHIVE
        assert decision.reviewed is False
        assert decision.is_correction is False


class TestKnowledgeEntry:
    """Test KnowledgeEntry schema"""

    def test_valid_knowledge_entry(self):
        """Test creating valid KnowledgeEntry"""
        entry = KnowledgeEntry(
            id="entry-123",
            title="Test Knowledge",
            content="# Test\n\nThis is markdown content",
            category="notes",
        )

        assert entry.id == "entry-123"
        assert entry.title == "Test Knowledge"
        assert entry.git_tracked is False
        assert entry.tags == []

    def test_knowledge_entry_with_tags(self):
        """Test KnowledgeEntry with tags"""
        entry = KnowledgeEntry(
            id="entry-456",
            title="Tagged Entry",
            content="Content",
            category="reference",
            tags=["python", "testing", "pydantic"],
        )

        assert len(entry.tags) == 3
        assert "python" in entry.tags


class TestKnowledgeQuery:
    """Test KnowledgeQuery schema"""

    def test_valid_knowledge_query(self):
        """Test creating valid KnowledgeQuery"""
        query = KnowledgeQuery(
            query="python testing",
            category="notes",
            limit=20,
        )

        assert query.query == "python testing"
        assert query.limit == 20
        assert query.include_content is True

    def test_knowledge_query_defaults(self):
        """Test default values"""
        query = KnowledgeQuery(query="test")

        assert query.limit == 10
        assert query.tags == []
        assert query.include_content is True


class TestFSRSCard:
    """Test FSRSCard schema"""

    def test_valid_fsrs_card(self):
        """Test creating valid FSRSCard"""
        card = FSRSCard(
            id="card-123",
            knowledge_entry_id="entry-456",
            question="What is Pydantic?",
            answer="A data validation library for Python",
        )

        assert card.id == "card-123"
        assert card.stability == 1.0
        assert card.difficulty == 5.0
        assert card.reps == 0
        assert card.state == "new"

    def test_fsrs_card_with_review_data(self):
        """Test FSRSCard with review history"""
        card = FSRSCard(
            id="card-789",
            knowledge_entry_id="entry-123",
            question="Question?",
            answer="Answer",
            stability=10.5,
            difficulty=3.2,
            reps=5,
            lapses=1,
            state="review",
        )

        assert card.reps == 5
        assert card.lapses == 1
        assert card.stability == 10.5


class TestFSRSReview:
    """Test FSRSReview schema"""

    def test_valid_fsrs_review(self):
        """Test creating valid FSRSReview"""
        review = FSRSReview(
            card_id="card-123",
            grade=ReviewGrade.GOOD,
            elapsed_days=5,
            scheduled_days=10,
            new_stability=12.5,
            new_difficulty=4.0,
        )

        assert review.card_id == "card-123"
        assert review.grade == ReviewGrade.GOOD
        assert review.elapsed_days == 5


class TestConversationContext:
    """Test ConversationContext schema"""

    def test_valid_conversation_context(self):
        """Test creating valid ConversationContext"""
        msg1 = ConversationMessage(role="user", content="Hello")
        msg2 = ConversationMessage(role="assistant", content="Hi there")

        context = ConversationContext(
            thread_id="thread-123",
            email_ids=["msg-1", "msg-2"],
            messages=[msg1, msg2],
        )

        assert context.thread_id == "thread-123"
        assert len(context.messages) == 2
        assert context.summary is None


class TestHealthCheck:
    """Test HealthCheck schema"""

    def test_valid_health_check(self):
        """Test creating valid HealthCheck"""
        check = HealthCheck(
            service="imap",
            status=ServiceStatus.HEALTHY,
            message="IMAP connection successful",
            response_time_ms=150.5,
        )

        assert check.service == "imap"
        assert check.status == ServiceStatus.HEALTHY
        assert check.response_time_ms == 150.5

    def test_health_check_with_details(self):
        """Test HealthCheck with details"""
        check = HealthCheck(
            service="ai",
            status=ServiceStatus.DEGRADED,
            message="High latency",
            details={"latency": 5000, "model": "claude-opus-4"},
        )

        assert check.details["latency"] == 5000


class TestSystemHealth:
    """Test SystemHealth schema"""

    def test_system_health_all_healthy(self):
        """Test SystemHealth when all services healthy"""
        checks = [
            HealthCheck(
                service="imap",
                status=ServiceStatus.HEALTHY,
                message="OK",
            ),
            HealthCheck(
                service="ai",
                status=ServiceStatus.HEALTHY,
                message="OK",
            ),
        ]

        health = SystemHealth(overall_status=ServiceStatus.HEALTHY, checks=checks)

        assert health.is_healthy is True
        assert len(health.unhealthy_services) == 0

    def test_system_health_with_unhealthy(self):
        """Test SystemHealth with unhealthy services"""
        checks = [
            HealthCheck(
                service="imap",
                status=ServiceStatus.HEALTHY,
                message="OK",
            ),
            HealthCheck(
                service="ai",
                status=ServiceStatus.UNHEALTHY,
                message="Connection failed",
            ),
        ]

        health = SystemHealth(overall_status=ServiceStatus.UNHEALTHY, checks=checks)

        assert health.is_healthy is False
        assert "ai" in health.unhealthy_services
        assert len(health.unhealthy_services) == 1
