import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd()))

from src.core.config_manager import get_config
from src.integrations.apple.notes_models import ConflictResolution
from src.integrations.apple.notes_sync import AppleNotesSync, SyncDirection
from src.monitoring.logger import get_logger

# Configure logging
logger = get_logger("scripts.force_sync")


def main():
    print("Starting manual Apple Notes sync...")
    try:
        config = get_config()
        notes_dir = Path(config.storage.notes_path)

        print(f"Notes directory: {notes_dir}")

        sync_service = AppleNotesSync(
            notes_dir=notes_dir,
            conflict_resolution=ConflictResolution.NEWER_WINS,
        )

        # Run sync
        result = sync_service.sync(direction=SyncDirection.BIDIRECTIONAL)

        print("\nSync completed!")
        print(f"Created: {len(result.created)}")
        for item in result.created:
            print(f"  + {item}")

        print(f"Updated: {len(result.updated)}")
        for item in result.updated:
            print(f"  ~ {item}")

        print(f"Deleted: {len(result.deleted)}")
        print(f"Skipped: {len(result.skipped)}")

        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  ! {error}")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
