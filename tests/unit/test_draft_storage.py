"""
Tests for Draft Storage System

Tests DraftReply dataclass, DraftStorage CRUD operations,
and PrepareEmailReplyAction.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.figaro.actions.email import PrepareEmailReplyAction, create_email_reply_draft
from src.integrations.storage.draft_storage import (
    DraftReply,
    DraftStatus,
    DraftStorage,
    ReplyFormat,
)


class TestDraftReply:
    """Tests for DraftReply dataclass"""

    def test_create_minimal_draft(self):
        """Should create draft with minimal required fields"""
        draft = DraftReply(
            draft_id="test-123",
            email_id=456,
            account_email="test@example.com",
        )

        assert draft.draft_id == "test-123"
        assert draft.email_id == 456
        assert draft.account_email == "test@example.com"
        assert draft.status == DraftStatus.DRAFT
        assert draft.subject == ""
        assert draft.body == ""
        assert draft.to_addresses == []

    def test_create_full_draft(self):
        """Should create draft with all fields"""
        now = datetime.now(timezone.utc)

        draft = DraftReply(
            draft_id="test-456",
            email_id=789,
            account_email="user@example.com",
            message_id="<msg123@example.com>",
            subject="Re: Hello",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc@example.com"],
            body="This is my reply",
            body_format=ReplyFormat.HTML,
            ai_generated=True,
            ai_confidence=0.85,
            ai_reasoning="Generated professional reply",
            original_subject="Hello",
            original_from="sender@example.com",
            original_date=now,
            status=DraftStatus.DRAFT,
        )

        assert draft.subject == "Re: Hello"
        assert draft.to_addresses == ["recipient@example.com"]
        assert draft.cc_addresses == ["cc@example.com"]
        assert draft.body == "This is my reply"
        assert draft.body_format == ReplyFormat.HTML
        assert draft.ai_confidence == 0.85
        assert draft.original_from == "sender@example.com"

    def test_to_dict_serialization(self):
        """Should serialize to dictionary correctly"""
        draft = DraftReply(
            draft_id="test-789",
            email_id=123,
            account_email="test@example.com",
            subject="Test Subject",
            body="Test Body",
        )

        data = draft.to_dict()

        assert data["draft_id"] == "test-789"
        assert data["email_id"] == 123
        assert data["account_email"] == "test@example.com"
        assert data["subject"] == "Test Subject"
        assert data["body"] == "Test Body"
        assert data["status"] == "draft"
        assert data["body_format"] == "plain_text"
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict_deserialization(self):
        """Should deserialize from dictionary correctly"""
        data = {
            "draft_id": "test-abc",
            "email_id": 999,
            "account_email": "user@test.com",
            "subject": "Re: Test",
            "body": "Test content",
            "to_addresses": ["to@test.com"],
            "cc_addresses": [],
            "bcc_addresses": [],
            "body_format": "plain_text",
            "status": "draft",
            "ai_generated": True,
            "ai_confidence": 0.9,
            "ai_reasoning": "Test reasoning",
            "original_subject": "Test",
            "original_from": "from@test.com",
            "user_edited": False,
            "edit_history": [],
            "created_at": "2026-01-07T10:00:00+00:00",
            "updated_at": "2026-01-07T10:00:00+00:00",
        }

        draft = DraftReply.from_dict(data)

        assert draft.draft_id == "test-abc"
        assert draft.email_id == 999
        assert draft.subject == "Re: Test"
        assert draft.to_addresses == ["to@test.com"]
        assert draft.ai_confidence == 0.9

    def test_roundtrip_serialization(self):
        """Should survive serialization roundtrip"""
        original = DraftReply(
            draft_id="roundtrip-test",
            email_id=555,
            account_email="test@example.com",
            subject="Re: Roundtrip",
            body="Roundtrip body",
            to_addresses=["recipient@example.com"],
            ai_confidence=0.75,
        )

        data = original.to_dict()
        restored = DraftReply.from_dict(data)

        assert restored.draft_id == original.draft_id
        assert restored.email_id == original.email_id
        assert restored.subject == original.subject
        assert restored.body == original.body
        assert restored.to_addresses == original.to_addresses
        assert restored.ai_confidence == original.ai_confidence


class TestDraftStatus:
    """Tests for DraftStatus enum"""

    def test_status_values(self):
        """Should have all expected status values"""
        assert DraftStatus.DRAFT.value == "draft"
        assert DraftStatus.SENT.value == "sent"
        assert DraftStatus.DISCARDED.value == "discarded"
        assert DraftStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        """Should create status from string"""
        assert DraftStatus("draft") == DraftStatus.DRAFT
        assert DraftStatus("sent") == DraftStatus.SENT


class TestReplyFormat:
    """Tests for ReplyFormat enum"""

    def test_format_values(self):
        """Should have all expected format values"""
        assert ReplyFormat.PLAIN_TEXT.value == "plain_text"
        assert ReplyFormat.HTML.value == "html"
        assert ReplyFormat.MARKDOWN.value == "markdown"


class TestDraftStorage:
    """Tests for DraftStorage class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create DraftStorage instance with temp directory"""
        return DraftStorage(drafts_dir=temp_dir)

    def test_init_creates_directory(self, temp_dir):
        """Should create drafts directory on init"""
        drafts_dir = temp_dir / "drafts"
        storage = DraftStorage(drafts_dir=drafts_dir)

        assert drafts_dir.exists()
        assert storage.drafts_dir == drafts_dir

    def test_create_draft(self, storage):
        """Should create and save a draft"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Re: Test",
            body="Test body",
            to_addresses=["recipient@example.com"],
        )

        assert draft.draft_id is not None
        assert draft.email_id == 123
        assert draft.subject == "Re: Test"
        assert draft.status == DraftStatus.DRAFT

        # Verify file was created
        file_path = storage.drafts_dir / f"{draft.draft_id}.json"
        assert file_path.exists()

    def test_get_draft(self, storage):
        """Should retrieve draft by ID"""
        created = storage.create_draft(
            email_id=456,
            account_email="test@example.com",
            subject="Re: Get Test",
            body="Get body",
        )

        retrieved = storage.get_draft(created.draft_id)

        assert retrieved is not None
        assert retrieved.draft_id == created.draft_id
        assert retrieved.subject == "Re: Get Test"

    def test_get_draft_not_found(self, storage):
        """Should return None for non-existent draft"""
        result = storage.get_draft("non-existent-id")
        assert result is None

    def test_get_drafts_for_email(self, storage):
        """Should retrieve all drafts for an email"""
        # Create multiple drafts for same email
        storage.create_draft(email_id=100, account_email="test@example.com", subject="Draft 1", body="Body 1")
        storage.create_draft(email_id=100, account_email="test@example.com", subject="Draft 2", body="Body 2")
        storage.create_draft(email_id=200, account_email="test@example.com", subject="Other", body="Other")

        drafts = storage.get_drafts_for_email(100)

        assert len(drafts) == 2
        assert all(d.email_id == 100 for d in drafts)

    def test_get_all_drafts(self, storage):
        """Should retrieve all drafts"""
        storage.create_draft(email_id=1, account_email="a@example.com", subject="A", body="A")
        storage.create_draft(email_id=2, account_email="b@example.com", subject="B", body="B")

        drafts = storage.get_all_drafts()

        assert len(drafts) == 2

    def test_get_all_drafts_with_status_filter(self, storage):
        """Should filter by status"""
        draft1 = storage.create_draft(email_id=1, account_email="test@example.com", subject="A", body="A")
        storage.create_draft(email_id=2, account_email="test@example.com", subject="B", body="B")

        # Mark first as sent
        storage.mark_sent(draft1.draft_id)

        pending = storage.get_all_drafts(status=DraftStatus.DRAFT)
        sent = storage.get_all_drafts(status=DraftStatus.SENT)

        assert len(pending) == 1
        assert len(sent) == 1

    def test_get_all_drafts_with_account_filter(self, storage):
        """Should filter by account"""
        storage.create_draft(email_id=1, account_email="a@example.com", subject="A", body="A")
        storage.create_draft(email_id=2, account_email="b@example.com", subject="B", body="B")
        storage.create_draft(email_id=3, account_email="a@example.com", subject="C", body="C")

        drafts = storage.get_all_drafts(account_email="a@example.com")

        assert len(drafts) == 2
        assert all(d.account_email == "a@example.com" for d in drafts)

    def test_get_pending_drafts(self, storage):
        """Should return only pending drafts"""
        draft1 = storage.create_draft(email_id=1, account_email="test@example.com", subject="A", body="A")
        storage.create_draft(email_id=2, account_email="test@example.com", subject="B", body="B")
        storage.mark_sent(draft1.draft_id)

        pending = storage.get_pending_drafts()

        assert len(pending) == 1
        assert pending[0].status == DraftStatus.DRAFT

    def test_update_draft_body(self, storage):
        """Should update draft body"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Original body",
        )

        updated = storage.update_draft(draft.draft_id, body="New body")

        assert updated is not None
        assert updated.body == "New body"
        assert updated.user_edited is True
        assert len(updated.edit_history) == 1

    def test_update_draft_subject(self, storage):
        """Should update draft subject"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Original",
            body="Body",
        )

        updated = storage.update_draft(draft.draft_id, subject="Updated Subject")

        assert updated.subject == "Updated Subject"
        assert updated.user_edited is True

    def test_update_draft_recipients(self, storage):
        """Should update recipients"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Body",
            to_addresses=["old@example.com"],
        )

        updated = storage.update_draft(
            draft.draft_id,
            to_addresses=["new@example.com"],
            cc_addresses=["cc@example.com"],
        )

        assert updated.to_addresses == ["new@example.com"]
        assert updated.cc_addresses == ["cc@example.com"]

    def test_update_draft_not_found(self, storage):
        """Should return None for non-existent draft"""
        result = storage.update_draft("non-existent", body="New body")
        assert result is None

    def test_update_sent_draft_fails(self, storage):
        """Should not update already sent draft"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Body",
        )
        storage.mark_sent(draft.draft_id)

        result = storage.update_draft(draft.draft_id, body="New body")

        # Should return None because draft is sent
        assert result is None

    def test_mark_sent(self, storage):
        """Should mark draft as sent"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Body",
        )

        result = storage.mark_sent(draft.draft_id)

        assert result is not None
        assert result.status == DraftStatus.SENT
        assert result.sent_at is not None

    def test_mark_failed(self, storage):
        """Should mark draft as failed"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Body",
        )

        result = storage.mark_failed(draft.draft_id, "SMTP error")

        assert result is not None
        assert result.status == DraftStatus.FAILED
        assert any("send_failed" in str(h) for h in result.edit_history)

    def test_discard_draft(self, storage):
        """Should discard draft"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Body",
        )

        result = storage.discard_draft(draft.draft_id, reason="Changed my mind")

        assert result is not None
        assert result.status == DraftStatus.DISCARDED
        assert result.discarded_at is not None

    def test_discard_sent_draft_fails(self, storage):
        """Should not discard already sent draft"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Body",
        )
        storage.mark_sent(draft.draft_id)

        result = storage.discard_draft(draft.draft_id)

        assert result is None

    def test_delete_draft(self, storage):
        """Should delete draft file"""
        draft = storage.create_draft(
            email_id=123,
            account_email="test@example.com",
            subject="Test",
            body="Body",
        )

        file_path = storage.drafts_dir / f"{draft.draft_id}.json"
        assert file_path.exists()

        result = storage.delete_draft(draft.draft_id)

        assert result is True
        assert not file_path.exists()

    def test_delete_non_existent_draft(self, storage):
        """Should return False for non-existent draft"""
        result = storage.delete_draft("non-existent")
        assert result is False

    def test_get_stats(self, storage):
        """Should return correct statistics"""
        draft1 = storage.create_draft(email_id=1, account_email="a@example.com", subject="A", body="A")
        storage.create_draft(email_id=2, account_email="b@example.com", subject="B", body="B")
        storage.create_draft(email_id=3, account_email="a@example.com", subject="C", body="C")
        storage.mark_sent(draft1.draft_id)

        stats = storage.get_stats()

        assert stats["total"] == 3
        assert stats["by_status"]["sent"] == 1
        assert stats["by_status"]["draft"] == 2
        assert stats["by_account"]["a@example.com"] == 2
        assert stats["by_account"]["b@example.com"] == 1

    def test_get_stats_empty(self, storage):
        """Should return empty stats for no drafts"""
        stats = storage.get_stats()

        assert stats["total"] == 0
        assert stats["by_status"] == {}
        assert stats["by_account"] == {}


class TestPrepareEmailReplyAction:
    """Tests for PrepareEmailReplyAction"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def action(self, temp_dir):
        """Create action with temp storage"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="This is the original email content.",
        )
        action._draft_storage = DraftStorage(drafts_dir=temp_dir)
        return action

    def test_action_id(self, action):
        """Should have unique action ID"""
        assert action.action_id.startswith("prepare_reply_")

    def test_action_type(self, action):
        """Should have correct action type"""
        assert action.action_type == "prepare_email_reply"

    def test_validate_success(self, action):
        """Should validate successfully with required fields"""
        result = action.validate()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_email_id(self):
        """Should fail validation with invalid email ID"""
        action = PrepareEmailReplyAction(
            email_id=0,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Content",
        )

        result = action.validate()

        assert result.valid is False
        assert any("Invalid email ID" in e for e in result.errors)

    def test_validate_missing_account(self):
        """Should fail validation without account email"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Content",
        )

        result = action.validate()

        assert result.valid is False
        assert any("Account email is required" in e for e in result.errors)

    def test_validate_missing_from(self):
        """Should fail validation without original sender"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="",
            original_content="Content",
        )

        result = action.validate()

        assert result.valid is False
        assert any("Original sender" in e for e in result.errors)

    def test_validate_warnings_empty_subject(self):
        """Should warn about empty subject"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="",
            original_from="sender@example.com",
            original_content="Content",
        )

        result = action.validate()

        assert result.valid is True
        assert any("subject is empty" in w for w in result.warnings)

    def test_validate_warnings_empty_content(self):
        """Should warn about empty content"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="",
        )

        result = action.validate()

        assert result.valid is True
        assert any("content is empty" in w for w in result.warnings)

    def test_execute_success(self, action):
        """Should execute and create draft"""
        result = action.execute()

        assert result.success is True
        assert "draft_id" in result.output
        assert result.output["subject"] == "Re: Hello"
        assert result.output["to_addresses"] == ["sender@example.com"]
        assert action._created_draft_id is not None

    def test_execute_generates_subject(self, action):
        """Should add Re: prefix to subject"""
        result = action.execute()

        assert result.output["subject"] == "Re: Hello"

    def test_execute_preserves_re_prefix(self, temp_dir):
        """Should not duplicate Re: prefix"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Re: Already replied",
            original_from="sender@example.com",
            original_content="Content",
        )
        action._draft_storage = DraftStorage(drafts_dir=temp_dir)

        result = action.execute()

        assert result.output["subject"] == "Re: Already replied"

    def test_execute_stores_draft(self, action):
        """Should store draft in storage"""
        action.execute()

        draft = action.draft_storage.get_draft(action._created_draft_id)

        assert draft is not None
        assert draft.email_id == 123
        assert draft.account_email == "user@example.com"

    def test_supports_undo(self, action):
        """Should support undo"""
        assert action.supports_undo() is True

    def test_can_undo_after_execute(self, action):
        """Should be able to undo after successful execution"""
        result = action.execute()

        assert action.can_undo(result) is True

    def test_undo_discards_draft(self, action):
        """Should discard draft on undo"""
        result = action.execute()
        draft_id = action._created_draft_id

        undo_result = action.undo(result)

        assert undo_result is True
        draft = action.draft_storage.get_draft(draft_id)
        assert draft.status == DraftStatus.DISCARDED

    def test_dependencies(self, action):
        """Should have no dependencies"""
        assert action.dependencies() == []

    def test_estimated_duration(self, action):
        """Should estimate duration"""
        assert action.estimated_duration() == 3.0


class TestCreateEmailReplyDraft:
    """Tests for factory function"""

    def test_creates_action(self):
        """Should create action with all parameters"""
        now = datetime.now(timezone.utc)

        action = create_email_reply_draft(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Content",
            reply_intent="Thanks for your message",
            tone="casual",
            language="en",
            original_date=now,
            original_message_id="<msg@example.com>",
            include_original=False,
        )

        assert isinstance(action, PrepareEmailReplyAction)
        assert action.email_id == 123
        assert action.tone == "casual"
        assert action.language == "en"
        assert action.include_original is False
        assert action.reply_intent == "Thanks for your message"

    def test_default_values(self):
        """Should use default values"""
        action = create_email_reply_draft(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Content",
        )

        assert action.tone == "professional"
        assert action.language == "fr"
        assert action.include_original is True
        assert action.reply_intent == ""


class TestDraftBodyGeneration:
    """Tests for draft body generation"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_french_professional_greeting(self, temp_dir):
        """Should use French professional greeting"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Content",
            tone="professional",
            language="fr",
            include_original=False,
        )
        action._draft_storage = DraftStorage(drafts_dir=temp_dir)

        action.execute()
        draft = action.draft_storage.get_draft(action._created_draft_id)

        assert "Bonjour," in draft.body
        assert "Cordialement," in draft.body

    def test_english_casual_greeting(self, temp_dir):
        """Should use English casual greeting"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Content",
            tone="casual",
            language="en",
            include_original=False,
        )
        action._draft_storage = DraftStorage(drafts_dir=temp_dir)

        action.execute()
        draft = action.draft_storage.get_draft(action._created_draft_id)

        assert "Hi," in draft.body
        assert "Cheers," in draft.body

    def test_includes_reply_intent(self, temp_dir):
        """Should include reply intent in body"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Content",
            reply_intent="Merci pour votre message",
            include_original=False,
        )
        action._draft_storage = DraftStorage(drafts_dir=temp_dir)

        action.execute()
        draft = action.draft_storage.get_draft(action._created_draft_id)

        assert "Merci pour votre message" in draft.body

    def test_includes_quoted_original(self, temp_dir):
        """Should include quoted original content"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="This is the original message.",
            include_original=True,
        )
        action._draft_storage = DraftStorage(drafts_dir=temp_dir)

        action.execute()
        draft = action.draft_storage.get_draft(action._created_draft_id)

        assert "> This is the original message." in draft.body
        assert "a écrit" in draft.body  # French "wrote"

    def test_placeholder_without_intent(self, temp_dir):
        """Should show placeholder when no reply intent"""
        action = PrepareEmailReplyAction(
            email_id=123,
            account_email="user@example.com",
            original_subject="Hello",
            original_from="sender@example.com",
            original_content="Content",
            reply_intent="",
            language="fr",
            include_original=False,
        )
        action._draft_storage = DraftStorage(drafts_dir=temp_dir)

        action.execute()
        draft = action.draft_storage.get_draft(action._created_draft_id)

        assert "[Votre réponse ici]" in draft.body
