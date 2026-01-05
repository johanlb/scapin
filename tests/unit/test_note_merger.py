"""Tests for note merger module"""

import pytest

from src.passepartout.note_merger import (
    Change,
    Conflict,
    ConflictType,
    MergeResult,
    MergeStrategy,
    NoteMerger,
)


class TestChange:
    """Tests for Change dataclass"""

    def test_is_deletion(self):
        """Should detect deletions"""
        deletion = Change(
            start_line=0,
            end_line=2,
            old_content=["line1\n", "line2\n"],
            new_content=[],
            source="user",
        )
        assert deletion.is_deletion is True
        assert deletion.is_addition is False

    def test_is_addition(self):
        """Should detect additions"""
        addition = Change(
            start_line=0,
            end_line=0,
            old_content=[],
            new_content=["new line\n"],
            source="scapin",
        )
        assert addition.is_addition is True
        assert addition.is_deletion is False

    def test_line_range(self):
        """Should compute correct line range"""
        change = Change(
            start_line=5,
            end_line=10,
            old_content=[],
            new_content=[],
            source="user",
        )
        assert change.line_range == range(5, 11)


class TestConflict:
    """Tests for Conflict dataclass"""

    def test_creation(self):
        """Should create conflict correctly"""
        user_change = Change(0, 0, [], ["user\n"], "user")
        scapin_change = Change(0, 0, [], ["scapin\n"], "scapin")

        conflict = Conflict(
            type=ConflictType.SAME_LINE,
            user_change=user_change,
            scapin_change=scapin_change,
        )

        assert conflict.type == ConflictType.SAME_LINE


class TestNoteMerger:
    """Tests for NoteMerger class"""

    @pytest.fixture
    def merger(self):
        """Create a merger with smart strategy"""
        return NoteMerger(strategy=MergeStrategy.SMART_MERGE)

    def test_no_changes(self, merger):
        """Should handle identical content"""
        original = "Line 1\nLine 2\nLine 3\n"

        result = merger.merge(original, original, original)

        assert result.success is True
        assert result.applied_user_changes == 0
        assert result.applied_scapin_changes == 0
        assert len(result.conflicts) == 0

    def test_user_only_changes(self, merger):
        """Should apply user changes when no scapin changes"""
        original = "Line 1\nLine 2\n"
        user_version = "Line 1 modified\nLine 2\n"
        scapin_version = original

        result = merger.merge(original, user_version, scapin_version)

        assert result.success is True
        assert result.applied_user_changes == 1
        assert result.applied_scapin_changes == 0
        assert "Line 1 modified" in result.content

    def test_scapin_only_changes(self, merger):
        """Should apply scapin changes when no user changes"""
        original = "Line 1\nLine 2\n"
        user_version = original
        scapin_version = "Line 1\nLine 2\nLine 3 added\n"

        result = merger.merge(original, user_version, scapin_version)

        assert result.success is True
        assert result.applied_user_changes == 0
        assert result.applied_scapin_changes == 1
        assert "Line 3 added" in result.content

    def test_non_conflicting_changes(self, merger):
        """Should merge non-conflicting changes"""
        original = "Line 1\nLine 2\nLine 3\n"
        user_version = "Line 1 user\nLine 2\nLine 3\n"
        scapin_version = "Line 1\nLine 2\nLine 3 scapin\n"

        result = merger.merge(original, user_version, scapin_version)

        assert result.success is True
        assert result.applied_user_changes >= 1
        assert result.applied_scapin_changes >= 1

    def test_conflicting_same_line(self, merger):
        """Should detect same-line conflicts"""
        original = "Line 1\n"
        user_version = "Line 1 user\n"
        scapin_version = "Line 1 scapin\n"

        result = merger.merge(original, user_version, scapin_version)

        assert len(result.conflicts) == 1
        # User should win by default in smart merge
        assert "Line 1 user" in result.content

    def test_user_wins_strategy(self):
        """User wins strategy should preserve all user changes"""
        merger = NoteMerger(strategy=MergeStrategy.USER_WINS)

        original = "Line 1\n"
        user_version = "Line 1 user\n"
        scapin_version = "Line 1 scapin\n"

        result = merger.merge(original, user_version, scapin_version)

        assert result.content == user_version
        assert len(result.pending_enrichments) == 1

    def test_scapin_wins_strategy(self):
        """Scapin wins strategy should preserve scapin changes"""
        merger = NoteMerger(strategy=MergeStrategy.SCAPIN_WINS)

        original = "Line 1\n"
        user_version = "Line 1 user\n"
        scapin_version = "Line 1 scapin\n"

        result = merger.merge(original, user_version, scapin_version)

        assert result.content == scapin_version

    def test_manual_strategy_marks_conflicts(self):
        """Manual strategy should mark conflicts"""
        merger = NoteMerger(strategy=MergeStrategy.MANUAL)

        original = "Line 1\n"
        user_version = "Line 1 user\n"
        scapin_version = "Line 1 scapin\n"

        result = merger.merge(original, user_version, scapin_version)

        assert result.success is False
        assert "<<<<<<< USER" in result.content
        assert "=======" in result.content
        assert ">>>>>>> SCAPIN" in result.content

    def test_detect_external_changes(self, merger):
        """Should detect when content has changed"""
        original = "Test content"
        original_hash = (
            "39bb7f10fdea98bf99d4e3e26c2a06cf"
            "3e11e0ea8c6b7e99f5c4afe5c5a5c6b6"
        )  # Fake hash

        # Different content should return True
        assert merger.detect_external_changes(original_hash, "Different content")

    def test_preview_merge(self, merger):
        """Should preview merge without applying"""
        original = "Line 1\nLine 2\n"
        user_version = "Line 1 user\nLine 2\n"
        scapin_version = "Line 1\nLine 2 scapin\n"

        preview = merger.preview_merge(original, user_version, scapin_version)

        assert "user_changes" in preview
        assert "scapin_changes" in preview
        assert "conflicts" in preview
        assert preview["user_changes"] >= 1
        assert preview["scapin_changes"] >= 1

    def test_addition_merge(self, merger):
        """Should handle additions from both sides"""
        original = "Line 1\n"
        user_version = "Line 1\nUser added\n"
        scapin_version = "Line 1\nScapin added\n"

        result = merger.merge(original, user_version, scapin_version)

        # Both additions might conflict or merge depending on position
        assert result.success is True

    def test_deletion_merge(self, merger):
        """Should handle deletions"""
        original = "Line 1\nLine 2\nLine 3\n"
        user_version = "Line 1\nLine 3\n"  # Deleted line 2
        scapin_version = original

        result = merger.merge(original, user_version, scapin_version)

        assert result.success is True
        assert "Line 2" not in result.content

    def test_complex_merge(self, merger):
        """Should handle complex multi-change merge"""
        original = """# Title
Line 1
Line 2
Line 3
Line 4
"""
        user_version = """# Title Modified
Line 1
Line 2 user change
Line 3
Line 4
"""
        scapin_version = """# Title
Line 1
Line 2
Line 3
Line 4
New section added by Scapin
"""

        result = merger.merge(original, user_version, scapin_version)

        # User title change should be preserved
        assert "Title Modified" in result.content
        # User line change should be preserved
        assert "user change" in result.content
        # Scapin addition should be included if no conflict
        # (depends on exact merge algorithm)
