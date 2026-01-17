import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path


# Explicitly mock required modules and submodules
def mock_pkg(name):
    m = MagicMock()
    sys.modules[name] = m
    return m


typer = mock_pkg("typer")
rich = mock_pkg("rich")
mock_pkg("rich.console")
mock_pkg("rich.live")
mock_pkg("rich.panel")
mock_pkg("rich.progress")
mock_pkg("rich.spinner")
mock_pkg("rich.table")
mock_pkg("rich.text")
mock_pkg("anthropic")
mock_pkg("msal")
mock_pkg("faiss")
mock_pkg("sentence_transformers")
mock_pkg("pydantic")
mock_pkg("pydantic_settings")
mock_pkg("yaml")
mock_pkg("git")
mock_pkg("requests")

# Mock Scapin modules to isolate CLI logic
with (
    patch("src.jeeves.cli.get_config") as mock_get_config,
    patch("src.jeeves.cli.NoteManager") as mock_manager_cls,
    patch("src.jeeves.cli.NoteReviewer") as mock_reviewer_cls,
    patch("src.jeeves.cli.create_scheduler") as mock_create_scheduler,
    patch("src.jeeves.cli.AIRouter") as mock_ai_router_cls,
    patch("src.jeeves.cli.console") as mock_console,
):
    # Setup config mock
    mock_config = MagicMock()
    mock_config.storage.notes_path = "/tmp/notes"
    mock_config.storage.database_path = Path("/tmp/pkm.db")
    mock_config.ai.anthropic_api_key = "fake-key"
    mock_get_config.return_value = mock_config

    # Setup manager mock
    mock_manager = mock_manager_cls.return_value
    mock_note1 = MagicMock(note_id="note1")
    mock_note1.updated_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
    mock_note2 = MagicMock(note_id="note2")
    mock_note2.updated_at = datetime(2023, 1, 2, tzinfo=timezone.utc)
    mock_manager.get_all_notes.return_value = [mock_note1, mock_note2]

    # Setup scheduler/store mock
    mock_scheduler = mock_create_scheduler.return_value
    mock_meta1 = MagicMock(note_id="note1")
    mock_meta1.is_due_for_review.return_value = True
    mock_meta2 = MagicMock(note_id="note2")
    mock_meta2.is_due_for_review.return_value = False
    mock_scheduler.store.list_all.return_value = [mock_meta1, mock_meta2]

    # Setup reviewer mock
    mock_reviewer = mock_reviewer_cls.return_value

    # Import the command function after mocking
    from src.jeeves.cli import notes_review

    print("--- Running CLI Plumbing Test ---")

    # Test Scenario 1: Only scheduling (--all)
    print("\n[Test 1] Testing --all (scheduling only)...")
    notes_review(all_notes=True, limit=None, process=False, force=False)
    mock_scheduler.trigger_immediate_review.assert_called()
    print("✅ OK: trigger_immediate_review called.")

    # Test Scenario 2: Processing due notes (--process)
    print("\n[Test 2] Testing --process (due notes only)...")
    mock_scheduler.trigger_immediate_review.reset_mock()
    mock_reviewer.review_note.reset_mock()

    import asyncio

    async def run_test2():
        await notes_review(all_notes=False, limit=None, process=True, force=False)

    asyncio.run(run_test2())
    mock_reviewer.review_note.assert_called_with("note1")
    print("✅ OK: review_note called for due note.")

    # Test Scenario 3: Force processing (--process --force --limit 1)
    print("\n[Test 3] Testing --process --force --limit 1...")
    mock_reviewer.review_note.reset_mock()

    async def run_test3():
        await notes_review(all_notes=False, limit=1, process=True, force=True)

    asyncio.run(run_test3())
    mock_reviewer.review_note.assert_called_once_with("note1")
    print("✅ OK: review_note called for oldest note under limit.")

    print("\n🎉 All CLI plumbing tests passed successfully!")
