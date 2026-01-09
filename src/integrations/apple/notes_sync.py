"""
Apple Notes Sync Service

Handles bidirectional synchronization between Apple Notes and Scapin notes.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.integrations.apple.notes_client import AppleNotesClient, get_apple_notes_client
from src.integrations.apple.notes_models import (
    AppleNote,
    ConflictResolution,
    SyncAction,
    SyncConflict,
    SyncDirection,
    SyncMapping,
    SyncResult,
)
from src.monitoring.logger import get_logger

logger = get_logger("integrations.apple.sync")


class AppleNotesSync:
    """
    Bidirectional sync service between Apple Notes and Scapin

    Sync logic:
    1. Read all Apple Notes and Scapin notes
    2. Compare using sync mappings (stored in data/apple_notes_sync.json)
    3. Determine actions based on modification dates
    4. Execute sync in both directions
    5. Update sync mappings
    """

    SYNC_MAPPING_FILE = "apple_notes_sync.json"
    EXCLUDED_FOLDERS = {"Recently Deleted", "Quick Notes"}

    def __init__(
        self,
        notes_dir: Path,
        client: AppleNotesClient | None = None,
        conflict_resolution: ConflictResolution = ConflictResolution.NEWER_WINS,
    ) -> None:
        """
        Initialize the sync service

        Args:
            notes_dir: Path to Scapin notes directory
            client: AppleNotesClient instance (optional)
            conflict_resolution: How to resolve conflicts
        """
        self.notes_dir = Path(notes_dir)
        self.client = client or get_apple_notes_client()
        self.conflict_resolution = conflict_resolution
        self._mappings: dict[str, SyncMapping] = {}
        self._load_mappings()

    def sync(
        self,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        dry_run: bool = False,
    ) -> SyncResult:
        """
        Perform synchronization

        Args:
            direction: Direction of sync
            dry_run: If True, don't make any changes, just report what would happen

        Returns:
            SyncResult with details of the sync operation
        """
        result = SyncResult(success=True, direction=direction)

        try:
            # Get all notes from both sources
            apple_notes = self._get_apple_notes()
            scapin_notes = self._get_scapin_notes()

            logger.info(
                f"Syncing: {len(apple_notes)} Apple Notes, "
                f"{len(scapin_notes)} Scapin notes"
            )

            # Determine sync actions
            actions = self._determine_sync_actions(
                apple_notes, scapin_notes, direction
            )

            # Execute actions
            if not dry_run:
                self._execute_sync_actions(actions, result)
                self._save_mappings()
            else:
                # In dry run, just populate result without making changes
                for apple_id, action, _data in actions:
                    if action == SyncAction.CREATE:
                        result.created.append(apple_id)
                    elif action == SyncAction.UPDATE:
                        result.updated.append(apple_id)
                    elif action == SyncAction.DELETE:
                        result.deleted.append(apple_id)
                    elif action == SyncAction.SKIP:
                        result.skipped.append(apple_id)

            result.completed_at = datetime.now()

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            result.success = False
            result.errors.append(str(e))
            result.completed_at = datetime.now()

        return result

    def _get_apple_notes(self) -> dict[str, AppleNote]:
        """Get all Apple Notes indexed by ID"""
        notes: dict[str, AppleNote] = {}

        for folder in self.client.get_folders():
            # Check if folder name or any part of path is in excluded folders
            if folder.name in self.EXCLUDED_FOLDERS:
                continue
            if any(excl in folder.path.split("/") for excl in self.EXCLUDED_FOLDERS):
                continue

            # Use folder.path for nested folder access
            folder_notes = self.client.get_notes_in_folder(folder.path)
            for note in folder_notes:
                # Store the full path in the note's folder field
                note.folder = folder.path
                notes[note.id] = note

        return notes

    def _get_scapin_notes(self) -> dict[str, tuple[Path, datetime]]:
        """
        Get all Scapin notes indexed by relative path

        Returns:
            Dict mapping relative path to (absolute path, modified time)
        """
        notes: dict[str, tuple[Path, datetime]] = {}

        if not self.notes_dir.exists():
            return notes

        for note_path in self.notes_dir.rglob("*.md"):
            # Skip hidden files and directories
            if any(part.startswith(".") for part in note_path.parts):
                continue

            rel_path = str(note_path.relative_to(self.notes_dir))
            modified = datetime.fromtimestamp(note_path.stat().st_mtime)
            notes[rel_path] = (note_path, modified)

        return notes

    def _determine_sync_actions(
        self,
        apple_notes: dict[str, AppleNote],
        scapin_notes: dict[str, tuple[Path, datetime]],
        direction: SyncDirection,
    ) -> list[tuple[str, SyncAction, dict]]:
        """
        Determine what sync actions to take

        Returns:
            List of (identifier, action, data) tuples
        """
        actions: list[tuple[str, SyncAction, dict]] = []

        # Track which notes we've processed
        processed_apple: set[str] = set()
        processed_scapin: set[str] = set()

        # Check existing mappings
        for apple_id, mapping in self._mappings.items():
            apple_note = apple_notes.get(apple_id)
            scapin_data = scapin_notes.get(mapping.scapin_path)

            if apple_note and scapin_data:
                # Both exist - check for updates
                scapin_path, scapin_modified = scapin_data
                apple_modified = apple_note.modified_at

                # Compare modification times
                if apple_modified > mapping.last_synced:
                    if scapin_modified > mapping.last_synced:
                        # Both modified - conflict!
                        action = self._resolve_conflict(
                            apple_note, scapin_path, scapin_modified
                        )
                        actions.append(
                            (
                                apple_id,
                                action,
                                {
                                    "apple_note": apple_note,
                                    "scapin_path": scapin_path,
                                    "direction": "conflict",
                                },
                            )
                        )
                    elif direction in (
                        SyncDirection.APPLE_TO_SCAPIN,
                        SyncDirection.BIDIRECTIONAL,
                    ):
                        # Apple updated - update Scapin
                        actions.append(
                            (
                                apple_id,
                                SyncAction.UPDATE,
                                {
                                    "apple_note": apple_note,
                                    "scapin_path": scapin_path,
                                    "direction": "apple_to_scapin",
                                },
                            )
                        )
                elif scapin_modified > mapping.last_synced:
                    if direction in (
                        SyncDirection.SCAPIN_TO_APPLE,
                        SyncDirection.BIDIRECTIONAL,
                    ):
                        # Scapin updated - update Apple
                        actions.append(
                            (
                                apple_id,
                                SyncAction.UPDATE,
                                {
                                    "apple_note": apple_note,
                                    "scapin_path": scapin_path,
                                    "direction": "scapin_to_apple",
                                },
                            )
                        )
                else:
                    # No changes
                    actions.append((apple_id, SyncAction.SKIP, {}))

                processed_apple.add(apple_id)
                processed_scapin.add(mapping.scapin_path)

            elif apple_note and not scapin_data:
                # Apple exists but Scapin deleted - handle based on direction
                if direction in (
                    SyncDirection.SCAPIN_TO_APPLE,
                    SyncDirection.BIDIRECTIONAL,
                ):
                    # Delete from Apple (Scapin wins)
                    actions.append(
                        (
                            apple_id,
                            SyncAction.DELETE,
                            {"apple_note": apple_note, "direction": "delete_apple"},
                        )
                    )
                processed_apple.add(apple_id)

            elif scapin_data and not apple_note:
                # Scapin exists but Apple deleted
                if direction in (
                    SyncDirection.APPLE_TO_SCAPIN,
                    SyncDirection.BIDIRECTIONAL,
                ):
                    # Delete from Scapin (Apple wins)
                    scapin_path, _ = scapin_data
                    actions.append(
                        (
                            mapping.scapin_path,
                            SyncAction.DELETE,
                            {"scapin_path": scapin_path, "direction": "delete_scapin"},
                        )
                    )
                processed_scapin.add(mapping.scapin_path)

        # Find new Apple notes (not in mappings)
        for apple_id, apple_note in apple_notes.items():
            if apple_id in processed_apple:
                continue

            if direction in (
                SyncDirection.APPLE_TO_SCAPIN,
                SyncDirection.BIDIRECTIONAL,
            ):
                # Create in Scapin
                actions.append(
                    (
                        apple_id,
                        SyncAction.CREATE,
                        {"apple_note": apple_note, "direction": "apple_to_scapin"},
                    )
                )

        # Find new Scapin notes (not in mappings)
        for scapin_path, (abs_path, _modified) in scapin_notes.items():
            if scapin_path in processed_scapin:
                continue

            if direction in (
                SyncDirection.SCAPIN_TO_APPLE,
                SyncDirection.BIDIRECTIONAL,
            ):
                # Create in Apple
                actions.append(
                    (
                        scapin_path,
                        SyncAction.CREATE,
                        {
                            "scapin_path": abs_path,
                            "scapin_rel_path": scapin_path,
                            "direction": "scapin_to_apple",
                        },
                    )
                )

        return actions

    def _resolve_conflict(
        self,
        apple_note: AppleNote,
        _scapin_path: Path,
        scapin_modified: datetime,
    ) -> SyncAction:
        """Resolve a sync conflict based on configured resolution strategy"""
        if self.conflict_resolution == ConflictResolution.APPLE_WINS:
            return SyncAction.UPDATE  # Will update Scapin
        elif self.conflict_resolution == ConflictResolution.SCAPIN_WINS:
            return SyncAction.UPDATE  # Will update Apple
        elif self.conflict_resolution == ConflictResolution.NEWER_WINS:
            if apple_note.modified_at > scapin_modified:
                return SyncAction.UPDATE  # Apple is newer
            else:
                return SyncAction.UPDATE  # Scapin is newer
        else:
            return SyncAction.CONFLICT  # Manual resolution needed

    def _execute_sync_actions(
        self,
        actions: list[tuple[str, SyncAction, dict]],
        result: SyncResult,
    ) -> None:
        """Execute the determined sync actions"""
        for identifier, action, data in actions:
            try:
                if action == SyncAction.CREATE:
                    self._execute_create(identifier, data, result)
                elif action == SyncAction.UPDATE:
                    self._execute_update(identifier, data, result)
                elif action == SyncAction.DELETE:
                    self._execute_delete(identifier, data, result)
                elif action == SyncAction.SKIP:
                    result.skipped.append(identifier)
                elif action == SyncAction.CONFLICT:
                    result.conflicts.append(
                        SyncConflict(
                            note_id=identifier,
                            apple_note=data.get("apple_note"),
                            scapin_note_path=str(data.get("scapin_path", "")),
                            apple_modified=data.get("apple_note", AppleNote).modified_at
                            if data.get("apple_note")
                            else None,
                            scapin_modified=None,
                            reason="Both modified since last sync",
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to execute {action} for {identifier}: {e}")
                result.errors.append(f"{action} {identifier}: {e}")

    def _execute_create(
        self,
        _identifier: str,
        data: dict,
        result: SyncResult,
    ) -> None:
        """Execute a create action"""
        direction = data.get("direction", "")

        if direction == "apple_to_scapin":
            # Create Scapin note from Apple note
            apple_note: AppleNote = data["apple_note"]
            scapin_path = self._create_scapin_note(apple_note)
            if scapin_path:
                self._add_mapping(apple_note.id, scapin_path, apple_note.modified_at)
                result.created.append(apple_note.name)

        elif direction == "scapin_to_apple":
            # Create Apple note from Scapin note
            scapin_path: Path = data["scapin_path"]
            scapin_rel_path: str = data["scapin_rel_path"]
            apple_id = self._create_apple_note(scapin_path)
            if apple_id:
                modified = datetime.fromtimestamp(scapin_path.stat().st_mtime)
                self._add_mapping(apple_id, scapin_rel_path, modified)
                result.created.append(scapin_path.stem)

    def _execute_update(
        self,
        _identifier: str,
        data: dict,
        result: SyncResult,
    ) -> None:
        """Execute an update action"""
        direction = data.get("direction", "")

        if direction == "apple_to_scapin":
            # Update Scapin from Apple
            apple_note: AppleNote = data["apple_note"]
            scapin_path: Path = data["scapin_path"]
            if self._update_scapin_note(scapin_path, apple_note):
                self._update_mapping(apple_note.id, apple_note.modified_at)
                result.updated.append(apple_note.name)

        elif direction == "scapin_to_apple":
            # Update Apple from Scapin
            apple_note: AppleNote = data["apple_note"]
            scapin_path: Path = data["scapin_path"]
            if self._update_apple_note(apple_note.id, scapin_path):
                modified = datetime.fromtimestamp(scapin_path.stat().st_mtime)
                self._update_mapping(apple_note.id, modified)
                result.updated.append(scapin_path.stem)

        elif direction == "conflict":
            # Handle conflict based on resolution strategy
            apple_note: AppleNote = data["apple_note"]
            scapin_path: Path = data["scapin_path"]
            scapin_modified = datetime.fromtimestamp(scapin_path.stat().st_mtime)

            if self.conflict_resolution == ConflictResolution.NEWER_WINS:
                if apple_note.modified_at > scapin_modified:
                    # Apple is newer
                    if self._update_scapin_note(scapin_path, apple_note):
                        self._update_mapping(apple_note.id, apple_note.modified_at)
                        result.updated.append(f"{apple_note.name} (Apple wins)")
                else:
                    # Scapin is newer
                    if self._update_apple_note(apple_note.id, scapin_path):
                        self._update_mapping(apple_note.id, scapin_modified)
                        result.updated.append(f"{scapin_path.stem} (Scapin wins)")

    def _execute_delete(
        self,
        _identifier: str,
        data: dict,
        result: SyncResult,
    ) -> None:
        """Execute a delete action"""
        direction = data.get("direction", "")

        if direction == "delete_apple":
            apple_note: AppleNote = data["apple_note"]
            if self.client.delete_note(apple_note.id):
                self._remove_mapping(apple_note.id)
                result.deleted.append(apple_note.name)

        elif direction == "delete_scapin":
            scapin_path: Path = data["scapin_path"]
            try:
                scapin_path.unlink()
                # Find and remove mapping
                for apple_id, mapping in list(self._mappings.items()):
                    if mapping.scapin_path == str(
                        scapin_path.relative_to(self.notes_dir)
                    ):
                        self._remove_mapping(apple_id)
                        break
                result.deleted.append(scapin_path.stem)
            except Exception as e:
                logger.error(f"Failed to delete Scapin note: {e}")

    def _create_scapin_note(self, apple_note: AppleNote) -> str | None:
        """Create a Scapin note from an Apple note"""
        # Determine target folder
        folder_path = self.notes_dir / self._sanitize_folder_name(apple_note.folder)
        folder_path.mkdir(parents=True, exist_ok=True)

        # Create filename from title
        filename = self._sanitize_filename(apple_note.name) + ".md"
        note_path = folder_path / filename

        # Handle duplicates
        counter = 1
        while note_path.exists():
            filename = f"{self._sanitize_filename(apple_note.name)}_{counter}.md"
            note_path = folder_path / filename
            counter += 1

        # Write content
        try:
            content = self._format_scapin_note(apple_note)
            note_path.write_text(content, encoding="utf-8")
            logger.info(f"Created Scapin note: {note_path}")
            return str(note_path.relative_to(self.notes_dir))
        except Exception as e:
            logger.error(f"Failed to create Scapin note: {e}")
            return None

    def _create_apple_note(self, scapin_path: Path) -> str | None:
        """Create an Apple note from a Scapin note"""
        # Read Scapin note
        content = scapin_path.read_text(encoding="utf-8")

        # Determine folder from path
        rel_path = scapin_path.relative_to(self.notes_dir)
        folder_name = rel_path.parts[0] if len(rel_path.parts) > 1 else "Notes"

        # Ensure folder exists in Apple Notes
        self.client.create_folder(folder_name)

        # Convert Markdown to HTML
        html_body = self._markdown_to_html(content)
        title = scapin_path.stem

        return self.client.create_note(folder_name, title, html_body)

    def _update_scapin_note(self, scapin_path: Path, apple_note: AppleNote) -> bool:
        """Update a Scapin note from an Apple note"""
        try:
            content = self._format_scapin_note(apple_note)
            scapin_path.write_text(content, encoding="utf-8")
            logger.info(f"Updated Scapin note: {scapin_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to update Scapin note: {e}")
            return False

    def _update_apple_note(self, apple_id: str, scapin_path: Path) -> bool:
        """Update an Apple note from a Scapin note"""
        content = scapin_path.read_text(encoding="utf-8")
        html_body = self._markdown_to_html(content)
        title = scapin_path.stem
        return self.client.update_note(apple_id, title=title, body_html=html_body)

    def _yaml_safe_string(self, value: str) -> str:
        """
        Format a string value for YAML safely.

        Quotes strings that contain special YAML characters:
        - Colon (anywhere in the string, as it could be interpreted as key-value separator)
        - Leading dash (-)
        - Brackets ([ ] { })
        - Hash (#)
        - Other special chars that could break parsing
        """
        # Characters that require quoting - be more aggressive to avoid YAML parsing issues
        needs_quoting = (
            ":" in value  # Any colon can break YAML parsing
            or value.startswith("-")
            or value.startswith("[")
            or value.startswith("{")
            or "#" in value
            or value.startswith("@")
            or value.startswith("!")
            or value.startswith("&")
            or value.startswith("*")
            or value.startswith(">")
            or value.startswith("|")
            or "'" in value
            or '"' in value
            or "\n" in value  # Multiline strings (newline)
            or "\u2028" in value  # Line separator (Unicode)
            or "\u2029" in value  # Paragraph separator (Unicode)
            or "\r" in value  # Carriage return
            or "\xa0" in value  # Non-breaking space
            or value.startswith(" ")  # Leading spaces
            or value.endswith(" ")  # Trailing spaces
        )

        if needs_quoting:
            # Escape double quotes and wrap in double quotes
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return value

    def _format_scapin_note(self, apple_note: AppleNote) -> str:
        """Format an Apple note as Scapin Markdown"""
        # Add frontmatter with metadata - properly quote strings
        safe_title = self._yaml_safe_string(apple_note.name)
        safe_folder = self._yaml_safe_string(apple_note.folder)

        frontmatter = f"""---
title: {safe_title}
source: apple_notes
apple_id: {apple_note.id}
apple_folder: {safe_folder}
created: {apple_note.created_at.isoformat()}
modified: {apple_note.modified_at.isoformat()}
synced: {datetime.now(timezone.utc).isoformat()}
---

"""
        return frontmatter + apple_note.body_markdown

    def _markdown_to_html(self, markdown: str) -> str:
        """Convert Markdown to Apple Notes HTML"""
        # Strip frontmatter if present
        if markdown.startswith("---"):
            parts = markdown.split("---", 2)
            if len(parts) >= 3:
                markdown = parts[2].strip()

        html = markdown

        # Headings
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
        html = re.sub(r"\*(.+?)\*", r"<i>\1</i>", html)

        # Links
        html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

        # Lists
        html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)

        # Paragraphs / line breaks
        lines = html.split("\n")
        wrapped_lines = []
        for line in lines:
            if line.strip():
                if not line.strip().startswith("<"):
                    line = f"<div>{line}</div>"
                wrapped_lines.append(line)
            else:
                wrapped_lines.append("<div><br></div>")

        return "\n".join(wrapped_lines)

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename"""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized.strip()

    def _sanitize_folder_name(self, name: str) -> str:
        """Sanitize a folder name or path (preserving path separators)"""
        # Handle folder paths with "/" - sanitize each component separately
        if "/" in name:
            parts = name.split("/")
            sanitized_parts = [self._sanitize_filename(part) for part in parts]
            return "/".join(sanitized_parts)
        return self._sanitize_filename(name)

    def _load_mappings(self) -> None:
        """Load sync mappings from file"""
        mapping_file = self.notes_dir / self.SYNC_MAPPING_FILE
        if mapping_file.exists():
            try:
                data = json.loads(mapping_file.read_text(encoding="utf-8"))
                for apple_id, mapping_data in data.items():
                    self._mappings[apple_id] = SyncMapping(
                        apple_id=apple_id,
                        scapin_path=mapping_data["scapin_path"],
                        apple_modified=datetime.fromisoformat(
                            mapping_data["apple_modified"]
                        ),
                        scapin_modified=datetime.fromisoformat(
                            mapping_data["scapin_modified"]
                        ),
                        last_synced=datetime.fromisoformat(mapping_data["last_synced"]),
                    )
            except Exception as e:
                logger.warning(f"Failed to load sync mappings: {e}")

    def _save_mappings(self) -> None:
        """Save sync mappings to file"""
        mapping_file = self.notes_dir / self.SYNC_MAPPING_FILE
        data = {}
        for apple_id, mapping in self._mappings.items():
            data[apple_id] = {
                "scapin_path": mapping.scapin_path,
                "apple_modified": mapping.apple_modified.isoformat(),
                "scapin_modified": mapping.scapin_modified.isoformat(),
                "last_synced": mapping.last_synced.isoformat(),
            }
        mapping_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _add_mapping(
        self, apple_id: str, scapin_path: str, modified: datetime
    ) -> None:
        """Add a new sync mapping"""
        now = datetime.now()
        self._mappings[apple_id] = SyncMapping(
            apple_id=apple_id,
            scapin_path=scapin_path,
            apple_modified=modified,
            scapin_modified=modified,
            last_synced=now,
        )

    def _update_mapping(self, apple_id: str, modified: datetime) -> None:
        """Update an existing mapping's last sync time"""
        if apple_id in self._mappings:
            self._mappings[apple_id].last_synced = datetime.now()
            self._mappings[apple_id].apple_modified = modified
            self._mappings[apple_id].scapin_modified = modified

    def _remove_mapping(self, apple_id: str) -> None:
        """Remove a sync mapping"""
        self._mappings.pop(apple_id, None)


def get_apple_notes_sync(notes_dir: Path) -> AppleNotesSync:
    """Get an instance of the Apple Notes sync service"""
    return AppleNotesSync(notes_dir)
