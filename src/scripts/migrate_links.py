#!/usr/bin/env python3
"""
Migration Script: Backfill Outgoing Links

This script iterates through all notes in the NoteManager and re-saves them
to trigger the new `outgoing_links` extraction logic.
"""

import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# --- CRITICAL: MOCK DEPENDENCIES BEFORE IMPORTING ANY PROJECT CODE ---

# 1. Mock External ML/System Dependencies
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["git"] = MagicMock()
sys.modules["git.exc"] = MagicMock()
sys.modules["gitdb"] = MagicMock()
sys.modules["gitdb.exc"] = MagicMock()
sys.modules["faiss"] = MagicMock()

# 2. Mock Project Modules causing issues (Integrations, Logger)
# Mocking logger prevents "MagicMock is not JSON serializable" errors
mock_logger_module = MagicMock()
mock_logger = logging.getLogger("migration")
mock_logger_module.get_logger.return_value = mock_logger
sys.modules["src.monitoring.logger"] = mock_logger_module

# Mock Integrations (Python < 3.10 syntax errors)
sys.modules["src.integrations"] = MagicMock()
sys.modules["src.passepartout.enricher"] = MagicMock()
sys.modules["src.passepartout.note_enricher"] = MagicMock()
sys.modules["src.passepartout.note_merger"] = MagicMock()


# 3. Mock EmbeddingGenerator specifically (Class replacement)
class MockEmbeddingGenerator:
    def __init__(self, *args, **kwargs):
        self.model_name = "mock-model"

    def get_dimension(self):
        return 384

    def embed_queries(self, queries):
        return [[0.0] * 384 for _ in queries]

    def embed_documents(self, docs):
        return [[0.0] * 384 for _ in docs]


embeddings_mock = MagicMock()
embeddings_mock.EmbeddingGenerator = MockEmbeddingGenerator
sys.modules["src.passepartout.embeddings"] = embeddings_mock

# --- END MOCKS ---

from src.passepartout.note_manager import NoteManager


def migrate_links():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("migrate_links")

    notes_dir = PROJECT_ROOT / "data" / "notes"
    if not notes_dir.exists():
        # Try local path if defaults don't exist
        notes_dir = Path("/Users/johan/Developer/scapin/data/notes")

    if len(sys.argv) > 1:
        notes_dir = Path(sys.argv[1])

    logger.info(f"Starting migration on notes directory: {notes_dir}")

    try:
        manager = NoteManager(notes_dir=notes_dir, auto_index=False, git_enabled=False)
    except Exception as e:
        logger.error(f"Failed to initialize NoteManager: {e}")
        import traceback

        traceback.print_exc()
        return

    notes = manager.get_all_notes()
    logger.info(f"Found {len(notes)} notes to process.")

    count = 0
    for note in notes:
        try:
            # Force re-extraction by passing content
            manager.update_note(note.note_id, content=note.content)
            count += 1
            if count % 100 == 0:
                logger.info(f"Processed {count}/{len(notes)} notes...")
        except Exception as e:
            logger.error(f"Failed to migrate note {note.note_id}: {e}")

    logger.info(f"Migration complete. {count} notes updated.")


if __name__ == "__main__":
    migrate_links()
