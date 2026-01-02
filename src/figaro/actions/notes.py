"""
Note Actions for Figaro

Concrete implementations of note-related actions using Passepartout.
"""

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from src.core.events.universal_event import Entity
from src.figaro.actions.base import Action, ActionResult, ValidationResult
from src.monitoring.logger import get_logger

logger = get_logger("figaro.actions.notes")


def _sanitize_id_component(text: str, max_length: int = 30) -> str:
    """
    Sanitize text for use in action IDs

    Removes special characters and limits length to prevent
    injection attacks or malformed IDs.

    Args:
        text: Text to sanitize
        max_length: Maximum length of sanitized text

    Returns:
        Sanitized text safe for use in action IDs
    """
    if not text:
        return "unknown"

    # Remove all characters except alphanumeric, spaces, underscores, and hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9_ -]', '', text)

    # Collapse multiple spaces/underscores
    sanitized = re.sub(r'[\s_-]+', '_', sanitized)

    # Strip leading/trailing underscores and whitespace
    sanitized = sanitized.strip('_ ')

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Ensure non-empty
    return sanitized if sanitized else "unknown"


@dataclass
class CreateNoteAction(Action):
    """
    Create a new note in the knowledge base

    Creates a Markdown note with YAML frontmatter containing:
    - Title and content
    - Tags
    - Entities (people, projects, etc.)
    - Metadata
    """

    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Stable unique ID (generated once on creation)
    _action_id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False, repr=False)

    @property
    def action_id(self) -> str:
        """Unique identifier for this action"""
        safe_title = _sanitize_id_component(self.title, max_length=30)
        return f"create_note_{safe_title}_{self._action_id[:8]}"

    @property
    def action_type(self) -> str:
        """Action type"""
        return "create_note"

    def supports_undo(self) -> bool:
        """Note creation supports undo"""
        return True

    def validate(self) -> ValidationResult:
        """
        Validate note creation

        Checks:
        1. Title is not empty
        2. Content is not empty
        3. Entities are valid
        """
        errors = []
        warnings = []

        if not self.title or not self.title.strip():
            errors.append("Note title is required")

        if not self.content or not self.content.strip():
            errors.append("Note content is required")

        # Validate entities
        for i, entity in enumerate(self.entities):
            if not hasattr(entity, 'type') or not entity.type:
                errors.append(f"Entity {i} missing required field: type")
            if not hasattr(entity, 'value') or not entity.value:
                errors.append(f"Entity {i} missing required field: value")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def execute(self) -> ActionResult:
        """
        Execute note creation

        Creates note in knowledge base using Passepartout.
        """
        start_time = time.time()

        try:
            from src.passepartout.note_manager import get_note_manager

            note_manager = get_note_manager()

            # Create note
            note_id = note_manager.create_note(
                title=self.title,
                content=self.content,
                tags=self.tags,
                entities=self.entities,
                metadata=self.metadata
            )

            duration = time.time() - start_time

            logger.info(
                f"Created note: {self.title}",
                extra={
                    "note_id": note_id,
                    "note_title": self.title,
                    "tags": self.tags,
                    "entities": [e.entity_id for e in self.entities],
                    "duration": duration
                }
            )

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "note_id": note_id,
                    "note_title": self.title,
                    "tags": self.tags
                },
                metadata={
                    "action": self,
                    "created_note_id": note_id  # Store for undo
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to create note '{self.title}': {e}", exc_info=True)

            return ActionResult(
                success=False,
                duration=duration,
                error=e,
                metadata={"action": self}
            )

    def can_undo(self, result: ActionResult) -> bool:
        """Note creation is reversible if we have the note ID"""
        return result.success and "created_note_id" in result.metadata

    def undo(self, result: ActionResult) -> bool:
        """
        Undo note creation by deleting the note

        Note: This deletes the note file from disk and removes it from
        the vector store. Git history will preserve it.

        Args:
            result: The ActionResult from execute() containing created_note_id
        """
        if not self.can_undo(result):
            logger.warning("Cannot undo note creation: not executed or note ID unknown")
            return False

        try:
            from src.passepartout.note_manager import get_note_manager

            note_manager = get_note_manager()

            # Extract note ID from result
            created_note_id = result.metadata["created_note_id"]

            # Delete the created note
            note_manager.delete_note(created_note_id)

            logger.info(
                f"Undid note creation: {self.title}",
                extra={
                    "note_id": created_note_id,
                    "note_title": self.title
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to undo note creation for '{self.title}': {e}", exc_info=True)
            return False

    def dependencies(self) -> list[str]:
        """Note creation has no dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated duration in seconds"""
        return 1.5  # File I/O + vector store update + git commit


@dataclass
class UpdateNoteAction(Action):
    """
    Update an existing note in the knowledge base

    Can update:
    - Content (append or replace)
    - Tags (add, remove, or replace)
    - Entities (add or remove)
    - Metadata (merge or replace)
    """

    note_id: str
    new_content: Optional[str] = None
    append_content: bool = False  # If True, append to existing content
    add_tags: list[str] = field(default_factory=list)
    remove_tags: list[str] = field(default_factory=list)
    replace_tags: Optional[list[str]] = None
    add_entities: list[Entity] = field(default_factory=list)
    remove_entities: list[str] = field(default_factory=list)  # Entity IDs
    metadata_updates: dict[str, Any] = field(default_factory=dict)

    # Stable unique ID (generated once on creation)
    _action_id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False, repr=False)

    @property
    def action_id(self) -> str:
        """Unique identifier for this action"""
        safe_note_id = _sanitize_id_component(self.note_id, max_length=40)
        return f"update_note_{safe_note_id}_{self._action_id[:8]}"

    @property
    def action_type(self) -> str:
        """Action type"""
        return "update_note"

    def supports_undo(self) -> bool:
        """Note update supports undo"""
        return True

    def validate(self) -> ValidationResult:
        """
        Validate note update

        Checks:
        1. Note ID is provided
        2. At least one update is specified
        3. Note exists
        """
        errors = []
        warnings = []

        if not self.note_id:
            errors.append("Note ID is required")

        # Check that at least one update is specified
        has_updates = any([
            self.new_content,
            self.add_tags,
            self.remove_tags,
            self.replace_tags is not None,
            self.add_entities,
            self.remove_entities,
            self.metadata_updates
        ])

        if not has_updates:
            errors.append("At least one update must be specified")

        # Check for conflicting tag operations
        if self.replace_tags is not None and (self.add_tags or self.remove_tags):
            warnings.append("replace_tags will override add_tags and remove_tags")

        # Verify note exists
        try:
            from src.passepartout.note_manager import get_note_manager

            note_manager = get_note_manager()
            note = note_manager.get_note(self.note_id)

            if not note:
                errors.append(f"Note not found: {self.note_id}")

        except Exception as e:
            errors.append(f"Failed to verify note exists: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def execute(self) -> ActionResult:
        """
        Execute note update

        Updates note in knowledge base using Passepartout.
        """
        start_time = time.time()

        try:
            from src.passepartout.note_manager import get_note_manager

            note_manager = get_note_manager()

            # Get original note for undo
            original = note_manager.get_note(self.note_id)
            if not original:
                raise ValueError(f"Note not found: {self.note_id}")

            # Store original state for undo
            original_note = {
                "content": original.content,
                "tags": original.tags.copy(),
                "entities": original.entities.copy(),
                "metadata": original.metadata.copy()
            }

            # Build update dict
            updates = {}

            # Content
            if self.new_content:
                if self.append_content:
                    updates["content"] = original.content + "\n\n" + self.new_content
                else:
                    updates["content"] = self.new_content

            # Tags
            if self.replace_tags is not None:
                updates["tags"] = self.replace_tags
            else:
                new_tags = set(original.tags)
                new_tags.update(self.add_tags)
                new_tags.difference_update(self.remove_tags)
                if self.add_tags or self.remove_tags:
                    updates["tags"] = list(new_tags)

            # Entities
            if self.add_entities or self.remove_entities:
                new_entities = [e for e in original.entities if e.entity_id not in self.remove_entities]
                new_entities.extend(self.add_entities)
                updates["entities"] = new_entities

            # Metadata
            if self.metadata_updates:
                new_metadata = original.metadata.copy()
                new_metadata.update(self.metadata_updates)
                updates["metadata"] = new_metadata

            # Update note
            note_manager.update_note(self.note_id, updates)

            duration = time.time() - start_time

            logger.info(
                f"Updated note: {self.note_id}",
                extra={
                    "note_id": self.note_id,
                    "updates": list(updates.keys()),
                    "duration": duration
                }
            )

            return ActionResult(
                success=True,
                duration=duration,
                output={
                    "note_id": self.note_id,
                    "updated_fields": list(updates.keys())
                },
                metadata={
                    "action": self,
                    "original_note": original_note  # Store for undo
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to update note '{self.note_id}': {e}", exc_info=True)

            return ActionResult(
                success=False,
                duration=duration,
                error=e,
                metadata={"action": self}
            )

    def can_undo(self, result: ActionResult) -> bool:
        """Note update is reversible if we have the original state"""
        return result.success and "original_note" in result.metadata

    def undo(self, result: ActionResult) -> bool:
        """
        Undo note update by restoring original state

        Args:
            result: The ActionResult from execute() containing original_note
        """
        if not self.can_undo(result):
            logger.warning("Cannot undo note update: not executed or original state unknown")
            return False

        try:
            from src.passepartout.note_manager import get_note_manager

            note_manager = get_note_manager()

            # Extract original state from result
            original_note = result.metadata["original_note"]

            # Restore original state
            note_manager.update_note(self.note_id, original_note)

            logger.info(
                f"Undid note update: {self.note_id}",
                extra={"note_id": self.note_id}
            )

            return True

        except Exception as e:
            logger.error(f"Failed to undo note update for '{self.note_id}': {e}", exc_info=True)
            return False

    def dependencies(self) -> list[str]:
        """Note update has no dependencies"""
        return []

    def estimated_duration(self) -> float:
        """Estimated duration in seconds"""
        return 1.5  # File I/O + vector store update + git commit
