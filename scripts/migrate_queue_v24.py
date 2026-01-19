#!/usr/bin/env python3
"""
Queue Migration Script: v2.3 -> v2.4

Migrates queue items from legacy status-based model to the new
state/resolution/snooze/error model.

Migration Details:
    - Adds 'state' field based on legacy 'status'
    - Adds 'resolution' field for processed items
    - Adds 'snooze' field (null for non-snoozed items)
    - Adds 'error' field (null for non-error items)
    - Adds 'timestamps' structure
    - Preserves all existing fields for backwards compatibility

Status Mapping:
    - pending -> state: awaiting_review, resolution: null
    - approved -> state: processed, resolution: manual_approved
    - rejected -> state: processed, resolution: manual_rejected
    - skipped -> state: processed, resolution: manual_skipped

Usage:
    # Dry run (shows what would be migrated)
    python scripts/migrate_queue_v24.py --dry-run

    # Run migration
    python scripts/migrate_queue_v24.py

    # Run with backup
    python scripts/migrate_queue_v24.py --backup

    # Migrate specific item
    python scripts/migrate_queue_v24.py --item-id <uuid>
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models.peripetie import (
    ResolvedBy,
    migrate_legacy_status,
)
from src.utils import get_data_dir


def get_queue_dir() -> Path:
    """Get the queue directory."""
    return get_data_dir() / "queue"


def backup_queue(queue_dir: Path) -> Path:
    """Create a backup of the queue directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = queue_dir.parent / f"queue_backup_{timestamp}"
    shutil.copytree(queue_dir, backup_dir)
    return backup_dir


def needs_migration(item: dict) -> bool:
    """Check if an item needs migration."""
    return "state" not in item


def migrate_item(item: dict) -> dict:
    """
    Migrate a single item to v2.4 format.

    Args:
        item: Queue item dictionary

    Returns:
        Migrated item dictionary
    """
    # Skip if already migrated
    if not needs_migration(item):
        return item

    # Get legacy status
    legacy_status = item.get("status", "pending")
    state, resolution_type = migrate_legacy_status(legacy_status)

    # Add v2.4 fields
    item["state"] = state.value

    # Create resolution if item was processed
    if resolution_type:
        item["resolution"] = {
            "type": resolution_type.value,
            "action_taken": item.get("analysis", {}).get("action", "unknown"),
            "resolved_at": item.get("reviewed_at") or item.get("queued_at"),
            "resolved_by": ResolvedBy.USER.value,
            "confidence_at_resolution": item.get("analysis", {}).get("confidence"),
            "user_modified_action": False,
            "original_action": None,
        }
    else:
        item["resolution"] = None

    # Add snooze and error fields (null for legacy items)
    item["snooze"] = None
    item["error"] = None

    # Add timestamps structure
    item["timestamps"] = {
        "queued_at": item.get("queued_at"),
        "analysis_started_at": item.get("queued_at"),
        "analysis_completed_at": item.get("queued_at"),
        "reviewed_at": item.get("reviewed_at"),
    }

    return item


def migrate_file(file_path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Migrate a single queue file.

    Args:
        file_path: Path to the queue file
        dry_run: If True, don't actually modify the file

    Returns:
        Tuple of (migrated: bool, message: str)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            item = json.load(f)
    except Exception as e:
        return False, f"Failed to read: {e}"

    if not needs_migration(item):
        return False, "Already migrated"

    # Migrate
    migrated_item = migrate_item(item)

    if dry_run:
        return True, f"Would migrate: status={item.get('status')} -> state={migrated_item['state']}"

    # Write back
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(migrated_item, f, indent=2, ensure_ascii=False)
        return True, f"Migrated: status={item.get('status')} -> state={migrated_item['state']}"
    except Exception as e:
        return False, f"Failed to write: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Migrate queue items from v2.3 to v2.4 format"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a backup before migration",
    )
    parser.add_argument(
        "--item-id",
        type=str,
        help="Migrate a specific item by ID",
    )
    parser.add_argument(
        "--queue-dir",
        type=str,
        help="Override queue directory path",
    )

    args = parser.parse_args()

    # Get queue directory
    queue_dir = Path(args.queue_dir) if args.queue_dir else get_queue_dir()

    if not queue_dir.exists():
        print(f"Queue directory not found: {queue_dir}")
        sys.exit(1)

    print(f"Queue directory: {queue_dir}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Create backup if requested
    if args.backup and not args.dry_run:
        backup_dir = backup_queue(queue_dir)
        print(f"✓ Backup created: {backup_dir}")
        print()

    # Get files to migrate
    if args.item_id:
        files = [queue_dir / f"{args.item_id}.json"]
        if not files[0].exists():
            print(f"Item not found: {args.item_id}")
            sys.exit(1)
    else:
        files = [f for f in queue_dir.glob("*.json") if not f.name.startswith(".")]

    print(f"Found {len(files)} queue files")
    print()

    # Migrate files
    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in sorted(files):
        item_id = file_path.stem
        migrated, message = migrate_file(file_path, dry_run=args.dry_run)

        if migrated:
            migrated_count += 1
            print(f"  ✓ {item_id[:8]}... {message}")
        elif "Already migrated" in message:
            skipped_count += 1
            if args.dry_run:
                print(f"  - {item_id[:8]}... {message}")
        else:
            error_count += 1
            print(f"  ✗ {item_id[:8]}... {message}")

    # Summary
    print()
    print("=" * 50)
    print(f"Migration {'preview' if args.dry_run else 'complete'}:")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped:  {skipped_count}")
    print(f"  Errors:   {error_count}")

    if args.dry_run and migrated_count > 0:
        print()
        print("Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
