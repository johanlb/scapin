"""
Note Merger

Intelligent three-way merge for note conflicts.
Handles conflicts when user edits a note while Scapin is enriching it.
"""

import difflib
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.monitoring.logger import get_logger

logger = get_logger("passepartout.note_merger")


class MergeStrategy(str, Enum):
    """Strategy for handling conflicts"""

    USER_WINS = "user_wins"  # User changes always win
    SCAPIN_WINS = "scapin_wins"  # Scapin changes always win
    SMART_MERGE = "smart_merge"  # Intelligent merge
    MANUAL = "manual"  # Require manual resolution


class ConflictType(str, Enum):
    """Type of merge conflict"""

    SAME_LINE = "same_line"  # Both modified same line
    OVERLAPPING = "overlapping"  # Changes overlap
    ADJACENT = "adjacent"  # Changes are adjacent
    DELETION = "deletion"  # One side deleted, other modified


@dataclass
class Change:
    """A single change in the diff"""

    start_line: int
    end_line: int
    old_content: list[str]
    new_content: list[str]
    source: str  # "user" or "scapin"

    @property
    def is_deletion(self) -> bool:
        return len(self.new_content) == 0

    @property
    def is_addition(self) -> bool:
        return len(self.old_content) == 0

    @property
    def line_range(self) -> range:
        return range(self.start_line, self.end_line + 1)


@dataclass
class Conflict:
    """A merge conflict"""

    type: ConflictType
    user_change: Change
    scapin_change: Change
    resolved_content: Optional[list[str]] = None
    resolution_reason: str = ""


@dataclass
class MergeResult:
    """Result of a merge operation"""

    content: str
    applied_user_changes: int
    applied_scapin_changes: int
    conflicts: list[Conflict]
    pending_enrichments: list[Change]  # Scapin changes that couldn't be applied
    success: bool
    summary: str


class NoteMerger:
    """
    Three-way merge for notes

    Handles conflicts between user edits and Scapin enrichments
    with preference for user changes on conflict.

    Algorithm:
    1. Diff original → user_version (user changes)
    2. Diff original → scapin_version (scapin changes)
    3. Identify non-conflicting changes
    4. For conflicts: user wins, scapin changes saved as pending
    """

    def __init__(
        self,
        strategy: MergeStrategy = MergeStrategy.SMART_MERGE,
    ):
        """
        Initialize merger

        Args:
            strategy: Default merge strategy
        """
        self.strategy = strategy

    def merge(
        self,
        original: str,
        user_version: str,
        scapin_version: str,
        strategy: Optional[MergeStrategy] = None,
    ) -> MergeResult:
        """
        Perform three-way merge

        Args:
            original: Original content before either edit
            user_version: User's modified version
            scapin_version: Scapin's enriched version

        Returns:
            MergeResult with merged content and conflict info
        """
        strategy = strategy or self.strategy
        logger.info(f"Merging with strategy: {strategy.value}")

        # Convert to lines for diff
        original_lines = original.splitlines(keepends=True)
        user_lines = user_version.splitlines(keepends=True)
        scapin_lines = scapin_version.splitlines(keepends=True)

        # Compute diffs
        user_changes = self._compute_changes(original_lines, user_lines, source="user")
        scapin_changes = self._compute_changes(original_lines, scapin_lines, source="scapin")

        logger.debug(
            f"Found {len(user_changes)} user changes, {len(scapin_changes)} scapin changes"
        )

        # Handle based on strategy
        if strategy == MergeStrategy.USER_WINS:
            return self._user_wins_merge(user_version, user_changes, scapin_changes)
        elif strategy == MergeStrategy.SCAPIN_WINS:
            return self._scapin_wins_merge(scapin_version, user_changes, scapin_changes)
        elif strategy == MergeStrategy.SMART_MERGE:
            return self._smart_merge(original_lines, user_changes, scapin_changes)
        else:
            # Manual - return with conflicts marked
            return self._mark_conflicts(original_lines, user_changes, scapin_changes)

    def _compute_changes(
        self,
        original: list[str],
        modified: list[str],
        source: str,
    ) -> list[Change]:
        """Compute list of changes between original and modified"""
        changes = []

        # Use difflib for comparison
        matcher = difflib.SequenceMatcher(None, original, modified)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            changes.append(
                Change(
                    start_line=i1,
                    end_line=i2 - 1 if i2 > i1 else i1,
                    old_content=original[i1:i2],
                    new_content=modified[j1:j2],
                    source=source,
                )
            )

        return changes

    def _find_conflicts(
        self,
        user_changes: list[Change],
        scapin_changes: list[Change],
    ) -> tuple[list[Conflict], list[Change], list[Change]]:
        """
        Find conflicts between changes

        Returns:
            (conflicts, non_conflicting_user, non_conflicting_scapin)
        """
        conflicts = []
        non_conflict_user = []
        non_conflict_scapin = []

        # Check each scapin change for conflicts with user changes
        scapin_conflicting = set()
        user_conflicting = set()

        for i, sc in enumerate(scapin_changes):
            for j, uc in enumerate(user_changes):
                if self._changes_overlap(sc, uc):
                    conflict_type = self._determine_conflict_type(sc, uc)
                    conflicts.append(
                        Conflict(
                            type=conflict_type,
                            user_change=uc,
                            scapin_change=sc,
                        )
                    )
                    scapin_conflicting.add(i)
                    user_conflicting.add(j)

        # Collect non-conflicting changes
        for i, change in enumerate(user_changes):
            if i not in user_conflicting:
                non_conflict_user.append(change)

        for i, change in enumerate(scapin_changes):
            if i not in scapin_conflicting:
                non_conflict_scapin.append(change)

        return conflicts, non_conflict_user, non_conflict_scapin

    def _changes_overlap(self, change1: Change, change2: Change) -> bool:
        """Check if two changes overlap"""
        range1 = change1.line_range
        range2 = change2.line_range

        # Check for any overlap
        return range1.start <= range2.stop and range2.start <= range1.stop

    def _determine_conflict_type(
        self,
        change1: Change,
        change2: Change,
    ) -> ConflictType:
        """Determine the type of conflict"""
        if change1.is_deletion or change2.is_deletion:
            return ConflictType.DELETION

        if change1.start_line == change2.start_line:
            return ConflictType.SAME_LINE

        # Check if changes are adjacent
        if (
            abs(change1.end_line - change2.start_line) <= 1
            or abs(change2.end_line - change1.start_line) <= 1
        ):
            return ConflictType.ADJACENT

        return ConflictType.OVERLAPPING

    def _user_wins_merge(
        self,
        user_version: str,
        user_changes: list[Change],
        scapin_changes: list[Change],
    ) -> MergeResult:
        """Merge where user changes always win"""
        conflicts, _, non_conflict_scapin = self._find_conflicts(user_changes, scapin_changes)

        # Scapin changes that conflict are saved as pending
        pending = [c.scapin_change for c in conflicts]

        return MergeResult(
            content=user_version,
            applied_user_changes=len(user_changes),
            applied_scapin_changes=len(non_conflict_scapin),
            conflicts=conflicts,
            pending_enrichments=pending,
            success=True,
            summary=f"User wins: {len(user_changes)} user changes applied, "
            f"{len(pending)} scapin enrichments saved for later",
        )

    def _scapin_wins_merge(
        self,
        scapin_version: str,
        user_changes: list[Change],
        scapin_changes: list[Change],
    ) -> MergeResult:
        """Merge where scapin changes win"""
        conflicts, non_conflict_user, _ = self._find_conflicts(user_changes, scapin_changes)

        return MergeResult(
            content=scapin_version,
            applied_user_changes=len(non_conflict_user),
            applied_scapin_changes=len(scapin_changes),
            conflicts=conflicts,
            pending_enrichments=[],
            success=True,
            summary=f"Scapin wins: {len(scapin_changes)} enrichments applied, "
            f"{len(conflicts)} user changes overwritten",
        )

    def _smart_merge(
        self,
        original_lines: list[str],
        user_changes: list[Change],
        scapin_changes: list[Change],
    ) -> MergeResult:
        """
        Intelligent merge

        - Apply all user changes
        - Apply non-conflicting scapin changes
        - For conflicts: user wins, scapin saved as pending
        """
        conflicts, non_conflict_user, non_conflict_scapin = self._find_conflicts(
            user_changes, scapin_changes
        )

        # Start with original
        result_lines = list(original_lines)

        # Track line offset from changes
        offset = 0

        # Collect all changes to apply, sorted by start line
        changes_to_apply = []
        changes_to_apply.extend((c, "user") for c in user_changes)
        changes_to_apply.extend((c, "scapin") for c in non_conflict_scapin)

        # Sort by start line (stable sort maintains user preference)
        changes_to_apply.sort(key=lambda x: x[0].start_line)

        # Apply changes
        applied_user = 0
        applied_scapin = 0

        for change, source in changes_to_apply:
            adjusted_start = change.start_line + offset
            adjusted_end = change.end_line + offset + 1

            # Apply change
            result_lines[adjusted_start:adjusted_end] = change.new_content

            # Update offset
            old_len = change.end_line - change.start_line + 1
            new_len = len(change.new_content)
            offset += new_len - old_len

            if source == "user":
                applied_user += 1
            else:
                applied_scapin += 1

        # Pending enrichments from conflicts
        pending = [c.scapin_change for c in conflicts]

        # Resolve conflicts for reporting
        for conflict in conflicts:
            conflict.resolved_content = conflict.user_change.new_content
            conflict.resolution_reason = "User change prioritized"

        merged_content = "".join(result_lines)

        return MergeResult(
            content=merged_content,
            applied_user_changes=applied_user,
            applied_scapin_changes=applied_scapin,
            conflicts=conflicts,
            pending_enrichments=pending,
            success=True,
            summary=f"Smart merge: {applied_user} user + {applied_scapin} scapin changes applied, "
            f"{len(conflicts)} conflicts resolved (user wins)",
        )

    def _mark_conflicts(
        self,
        original_lines: list[str],
        user_changes: list[Change],
        scapin_changes: list[Change],
    ) -> MergeResult:
        """Mark conflicts in content for manual resolution"""
        conflicts, _, _ = self._find_conflicts(user_changes, scapin_changes)

        # Build content with conflict markers
        result_lines = list(original_lines)

        for conflict in reversed(conflicts):  # Reverse to maintain line numbers
            start = conflict.user_change.start_line
            end = conflict.user_change.end_line + 1

            # Insert conflict markers
            marker_content = []
            marker_content.append("<<<<<<< USER\n")
            marker_content.extend(conflict.user_change.new_content)
            marker_content.append("=======\n")
            marker_content.extend(conflict.scapin_change.new_content)
            marker_content.append(">>>>>>> SCAPIN\n")

            result_lines[start:end] = marker_content

        merged_content = "".join(result_lines)

        return MergeResult(
            content=merged_content,
            applied_user_changes=0,
            applied_scapin_changes=0,
            conflicts=conflicts,
            pending_enrichments=[],
            success=False,
            summary=f"Manual resolution required: {len(conflicts)} conflicts marked",
        )

    def detect_external_changes(
        self,
        stored_hash: str,
        current_content: str,
    ) -> bool:
        """
        Detect if content has changed externally

        Args:
            stored_hash: Previously stored content hash
            current_content: Current content to check

        Returns:
            True if content has changed
        """
        import hashlib

        current_hash = hashlib.sha256(current_content.encode()).hexdigest()
        return current_hash != stored_hash

    def preview_merge(
        self,
        original: str,
        user_version: str,
        scapin_version: str,
    ) -> dict:
        """
        Preview merge without applying

        Returns:
            Dictionary with merge statistics
        """
        original_lines = original.splitlines(keepends=True)
        user_lines = user_version.splitlines(keepends=True)
        scapin_lines = scapin_version.splitlines(keepends=True)

        user_changes = self._compute_changes(original_lines, user_lines, source="user")
        scapin_changes = self._compute_changes(original_lines, scapin_lines, source="scapin")

        conflicts, non_conflict_user, non_conflict_scapin = self._find_conflicts(
            user_changes, scapin_changes
        )

        return {
            "user_changes": len(user_changes),
            "scapin_changes": len(scapin_changes),
            "conflicts": len(conflicts),
            "non_conflicting_user": len(non_conflict_user),
            "non_conflicting_scapin": len(non_conflict_scapin),
            "conflict_details": [
                {
                    "type": c.type.value,
                    "user_lines": f"{c.user_change.start_line}-{c.user_change.end_line}",
                    "scapin_lines": f"{c.scapin_change.start_line}-{c.scapin_change.end_line}",
                }
                for c in conflicts
            ],
        }
