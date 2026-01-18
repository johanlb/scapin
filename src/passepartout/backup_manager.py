"""
Backup Manager Service

Handles creation and management of notes directory snapshots.
Used as a safety net before critical operations (like sync).
"""

import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.monitoring.logger import get_logger

logger = get_logger("passepartout.backup")


class BackupManager:
    """
    Manages backups of the notes directory.

    Strategies:
    - Create timestamps zip archives
    - Rotate backups (keep last N)
    - Restore functionality (manual for now, automated if needed)
    """

    def __init__(self, notes_dir: Path, backup_dir: Path, max_backups: int = 10):
        self.notes_dir = Path(notes_dir)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups

        # Ensure backup directory exists
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)

    def create_snapshot(self, prefix: str = "notes") -> Optional[Path]:
        """
        Create a zip snapshot of the notes directory.

        Args:
            prefix: Prefix for the backup filename

        Returns:
            Path to the created backup file, or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{prefix}_{timestamp}.zip"
            backup_path = self.backup_dir / backup_filename

            # Create zip archive
            # zipall content of notes_dir into the zip file
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.notes_dir.rglob("*"):
                    # Skip hidden files and the backup dir itself if it's inside (it shouldn't be)
                    if any(part.startswith(".") for part in file_path.parts):
                        continue

                    if file_path.is_file():
                        # Store relative to notes_dir
                        rel_path = file_path.relative_to(self.notes_dir)
                        zipf.write(file_path, rel_path)

            logger.info(
                f"Created backup snapshot: {backup_path} ({self._get_size_str(backup_path)})"
            )

            # Rotate backups after successful creation
            self._rotate_backups()

            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup snapshot: {e}", exc_info=True)
            return None

    def list_backups(self) -> List[Path]:
        """List all backup files sorted by modification time (newest first)."""
        backups = list(self.backup_dir.glob("*.zip"))
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backups

    def _rotate_backups(self) -> None:
        """Keep only the most recent N backups."""
        backups = self.list_backups()

        if len(backups) > self.max_backups:
            to_delete = backups[self.max_backups :]
            for backup in to_delete:
                try:
                    backup.unlink()
                    logger.info(f"Rotated (deleted) old backup: {backup.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete old backup {backup}: {e}")

    def _get_size_str(self, path: Path) -> str:
        """Get human readable file size."""
        size_bytes = path.stat().st_size
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
