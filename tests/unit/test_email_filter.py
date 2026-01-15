"""
Tests for EmailFilter — Pre-filtering marketing and transactional emails

Tests cover:
- Marketing email detection (newsletters, promotions)
- Transactional email detection (invoices, confirmations)
- Edge cases and conservative behavior
"""

from unittest.mock import MagicMock

import pytest

from src.trivelin.email_filter import (
    EmailFilter,
    FilterDecision,
    FilterResult,
    get_email_filter,
)


@pytest.fixture
def email_filter():
    """Create a fresh EmailFilter for each test"""
    return EmailFilter()


def create_mock_event(
    sender_email: str = "test@example.com",
    sender_name: str = "Test Sender",
    subject: str = "Test Subject",
    content: str = "Test content",
):
    """Helper to create mock email events"""
    # Create mock sender
    sender = MagicMock()
    sender.email = sender_email
    sender.name = sender_name

    # Create mock event
    event = MagicMock()
    event.sender = sender
    event.title = subject
    event.content = content

    return event


class TestFilterResult:
    """Tests for FilterResult enum"""

    def test_values(self):
        """Test all filter result values exist"""
        assert FilterResult.SKIP.value == "skip"
        assert FilterResult.PROCESS_LIGHT.value == "process_light"
        assert FilterResult.PROCESS_FULL.value == "process_full"


class TestEmailFilterInit:
    """Tests for EmailFilter initialization"""

    def test_default_init(self):
        """Test default initialization"""
        filter = EmailFilter()
        assert len(filter.skip_sender_patterns) > 0
        assert len(filter.transactional_patterns) > 0
        assert filter.strict_mode is False

    def test_custom_patterns(self):
        """Test with custom patterns"""
        filter = EmailFilter(
            skip_sender_patterns=["custom-spam@"],
            transactional_patterns=["custom-invoice@"],
        )
        assert "custom-spam@" in filter.skip_sender_patterns
        assert "custom-invoice@" in filter.transactional_patterns

    def test_strict_mode(self):
        """Test strict mode flag"""
        filter = EmailFilter(strict_mode=True)
        assert filter.strict_mode is True


class TestSkipDetection:
    """Tests for marketing email detection (SKIP result)"""

    def test_noreply_sender(self, email_filter):
        """Test noreply@ sender is skipped"""
        event = create_mock_event(sender_email="noreply@company.com")
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.SKIP
        assert len(decision.patterns_matched) >= 1

    def test_newsletter_sender(self, email_filter):
        """Test newsletter@ sender is skipped"""
        event = create_mock_event(sender_email="newsletter@shop.com")
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.SKIP

    def test_mailchimp_sender(self, email_filter):
        """Test mailchimp.com sender is skipped"""
        event = create_mock_event(sender_email="sender@mailchimp.com")
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.SKIP

    def test_linkedin_sender(self, email_filter):
        """Test linkedin.com notifications are skipped"""
        event = create_mock_event(sender_email="notifications@linkedin.com")
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.SKIP

    def test_unsubscribe_subject(self, email_filter):
        """Test email with unsubscribe in subject is skipped"""
        event = create_mock_event(
            sender_email="test@company.com",
            subject="Weekly newsletter - click to unsubscribe",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.SKIP

    def test_promotion_subject(self, email_filter):
        """Test promotional subject is skipped"""
        event = create_mock_event(
            sender_email="test@shop.com",
            subject="50% OFF - Offre exclusive pour vous!",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.SKIP

    def test_multiple_patterns_high_confidence(self, email_filter):
        """Test multiple patterns give high confidence skip"""
        event = create_mock_event(
            sender_email="newsletter@mailchimp.com",
            subject="Weekly digest - unsubscribe here",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.SKIP
        assert decision.confidence >= 0.90
        assert len(decision.patterns_matched) >= 2


class TestTransactionalDetection:
    """Tests for transactional email detection (PROCESS_LIGHT result)"""

    def test_invoice_sender(self, email_filter):
        """Test invoice@ sender is processed lightly"""
        event = create_mock_event(sender_email="invoice@company.com")
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_LIGHT

    def test_order_confirmation_sender(self, email_filter):
        """Test order@ sender is processed lightly"""
        event = create_mock_event(sender_email="order@shop.com")
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_LIGHT

    def test_facture_subject(self, email_filter):
        """Test facture in subject triggers light processing"""
        event = create_mock_event(
            sender_email="contact@supplier.fr",
            subject="Votre facture #12345",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_LIGHT

    def test_confirmation_subject(self, email_filter):
        """Test order confirmation in subject"""
        event = create_mock_event(
            sender_email="service@amazon.fr",
            subject="Confirmation de commande N°123456",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_LIGHT

    def test_shipping_notification(self, email_filter):
        """Test shipping notifications are processed lightly"""
        event = create_mock_event(
            sender_email="tracking@chronopost.fr",
            subject="Votre colis est en livraison",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_LIGHT


class TestFullProcessing:
    """Tests for regular emails (PROCESS_FULL result)"""

    def test_regular_email(self, email_filter):
        """Test regular email gets full processing"""
        event = create_mock_event(
            sender_email="colleague@company.com",
            subject="Re: Meeting tomorrow",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_FULL
        assert decision.confidence == 1.0
        assert len(decision.patterns_matched) == 0

    def test_personal_email(self, email_filter):
        """Test personal email gets full processing"""
        event = create_mock_event(
            sender_email="friend@gmail.com",
            subject="Dinner plans",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_FULL

    def test_business_email(self, email_filter):
        """Test business email gets full processing"""
        event = create_mock_event(
            sender_email="client@bigcorp.com",
            subject="Contract renewal proposal",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_FULL


class TestEdgeCases:
    """Tests for edge cases and conservative behavior"""

    def test_noreply_with_invoice_subject(self, email_filter):
        """Test noreply sender with invoice subject -> NOT skipped (conservative)"""
        event = create_mock_event(
            sender_email="noreply@supplier.com",
            subject="Votre facture #12345",
        )
        decision = email_filter.should_process(event)

        # Should NOT skip because it's transactional
        assert decision.result in [FilterResult.PROCESS_LIGHT, FilterResult.PROCESS_FULL]

    def test_empty_sender(self, email_filter):
        """Test handling of empty sender"""
        event = create_mock_event(
            sender_email="",
            subject="Test subject",
        )
        decision = email_filter.should_process(event)

        # Should default to full processing when uncertain
        assert decision.result == FilterResult.PROCESS_FULL

    def test_none_sender(self, email_filter):
        """Test handling of None sender"""
        # Create mock event with no sender
        event = MagicMock()
        event.sender = None
        event.title = "Test subject"
        event.content = "Test content"

        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.PROCESS_FULL

    def test_case_insensitivity(self, email_filter):
        """Test patterns are case-insensitive"""
        event = create_mock_event(
            sender_email="NEWSLETTER@COMPANY.COM",
            subject="UNSUBSCRIBE FROM OUR LIST",
        )
        decision = email_filter.should_process(event)

        assert decision.result == FilterResult.SKIP


class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_email_filter_returns_same_instance(self):
        """Test singleton returns same instance"""
        filter1 = get_email_filter()
        filter2 = get_email_filter()

        assert filter1 is filter2


class TestFilterDecision:
    """Tests for FilterDecision dataclass"""

    def test_creation(self):
        """Test FilterDecision creation"""
        decision = FilterDecision(
            result=FilterResult.SKIP,
            reason="Test reason",
            confidence=0.95,
            patterns_matched=["pattern1", "pattern2"],
        )

        assert decision.result == FilterResult.SKIP
        assert decision.reason == "Test reason"
        assert decision.confidence == 0.95
        assert len(decision.patterns_matched) == 2
