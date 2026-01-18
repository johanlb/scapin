import logging

from src.core.config_manager import get_config
from src.passepartout.note_manager import NoteManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("index_notes")


def main():
    """
    Force re-index all notes in the PKM system.
    """
    logger.info("Starting PKM re-indexing...")

    config = get_config()
    notes_dir = config.storage.notes_path

    logger.info(f"Target directory: {notes_dir}")

    # Initialize NoteManager with auto_index=False to avoid automatic behavior
    # We want to control the indexing explicitly
    manager = NoteManager(
        notes_dir=notes_dir,
        auto_index=False,
        git_enabled=False,  # No need for git during indexing
    )

    logger.info(f"Current index size: {len(manager.vector_store.id_to_doc)}")

    # 1. Clear existing index (optional, but safer for full rebuild)
    # The _index_all_notes method skips already indexed notes, so we might want to clean first
    # But NoteManager doesn't expose a clear() method easily without messing with internals.
    # However, creating a NEW vector store or just deleting the index files before running this would be cleaner.
    # For now, let's trust _index_all_notes to fill gaps, or we force it by checking if we want to clear.

    # Actually, let's delete the index files to force a clean slate if requested?
    # No, let's just run _index_all_notes(). If the store is empty (as suspected), it should fill it.

    # Check if store is empty
    if len(manager.vector_store.id_to_doc) == 0:
        logger.info("Vector store is empty. Starting full indexation...")
        count = manager._index_all_notes()
        manager._save_index()
        logger.info(f"Indexation complete. Analyzed {count} notes.")
    else:
        logger.info("Vector store is NOT empty.")
        logger.info("To force re-index, delete the .scapin_index folder in your notes directory.")

        # We can also call _index_all_notes which checks for missing ones
        logger.info("Running incremental indexation to add missing notes...")
        count = manager._index_all_notes()
        if count > 0:
            manager._save_index()
            logger.info(f"Added {count} new notes to index.")
        else:
            logger.info("No new notes found to index.")


if __name__ == "__main__":
    main()
