import asyncio
import json
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath("src"))

from src.core.config_manager import get_config
from src.trivelin.processor import EmailProcessor
from src.core.schemas import EmailMetadata, EmailContent, EmailAnalysis, EmailCategory, EmailAction
from src.passepartout.note_manager import NoteManager
from src.utils import now_utc


async def reproduce():
    print("Starting reproduction...")

    # 1. Setup mocks
    # Mock IMAPClient to return a test email
    test_metadata = EmailMetadata(
        id=123,
        from_address="test@example.com",
        from_name="Test User",
        to_addresses=["johan@scapin.me"],
        subject="Important meeting notes",
        date=datetime.now(),
        has_attachments=False,
    )

    test_content = EmailContent(
        plain_text="Here are the notes from our meeting. We decided to launch Project X on July 1st.",
        preview="Here are the notes from our meeting...",
    )

    # Mock AI Router to return an analysis with proposed notes
    test_analysis = EmailAnalysis(
        action=EmailAction.ARCHIVE,
        category=EmailCategory.WORK,
        confidence=95,
        reasoning="Meeting notes about Project X",
        summary="Meeting notes for Project X launch",
        proposed_notes=[
            {
                "action": "create",
                "note_type": "projet",
                "title": "Project X",
                "content_summary": "Launch planned for July 1st.",
                "confidence": 0.92,
                "reasoning": "New project mentioned in email",
                "required": True,
            }
        ],
    )

    config = get_config()
    # Ensure a temporary notes directory
    notes_dir = os.path.abspath("tmp_notes")
    os.makedirs(notes_dir, exist_ok=True)

    # Initialize processor with mocked AI Router
    # We patch BOTH the constructor and the get_ai_router call
    with (
        patch("src.trivelin.processor.IMAPClient") as mock_imap_cls,
        patch("src.trivelin.processor.get_ai_router") as mock_get_router,
    ):
        # Setup IMAP mock
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.connect.return_value.__enter__.return_value = mock_imap
        mock_imap.fetch_emails.return_value = [(test_metadata, test_content)]

        # Setup AI Router mock
        mock_router = MagicMock()
        mock_get_router.return_value = mock_router
        mock_router.analyze_email.return_value = test_analysis

        # Initialize NoteManager with tmp dir
        note_manager = NoteManager(notes_dir=notes_dir)

        processor = EmailProcessor()
        # Override note_manager
        processor.note_manager = note_manager

        print(f"Processing inbox (notes_dir={notes_dir})...")
        results = processor.process_inbox(auto_execute=True)

        print(f"Processed {len(results)} emails.")
        for r in results:
            print(f"Email ID: {r.metadata.id}")
            print(f"Analysis Action: {r.analysis.action}")
            print(f"Analysis Confidence: {r.analysis.confidence}")

        # Check if note was created
        notes = note_manager.list_notes()
        print(f"Total notes in {notes_dir}: {len(notes)}")
        for note in notes:
            print(f"Note found: {note.title} (ID: {note.note_id})")

    # Cleanup
    # import shutil
    # shutil.rmtree(notes_dir)


if __name__ == "__main__":
    asyncio.run(reproduce())
