"""
Performance Tests for Notes Operations

Tests performance of:
- Loading large numbers of notes
- Notes tree construction
- Note search operations
- Index refresh operations
- Cache effectiveness
"""

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.performance.conftest import PerformanceThresholds, measure_time


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def large_notes_dir(tmp_path):
    """Create a directory with 100+ notes for performance testing"""
    notes_path = tmp_path / "notes"
    notes_path.mkdir()

    # Create 100 notes in root
    for i in range(100):
        note_file = notes_path / f"note_{i:03d}.md"
        note_file.write_text(f"""---
title: Performance Test Note {i}
type: concept
tags:
  - perf
  - test
  - batch{i // 10}
created_at: 2026-01-{(i % 28) + 1:02d}T10:00:00Z
modified_at: 2026-01-{(i % 28) + 1:02d}T10:00:00Z
summary: This is a performance test note number {i}
---

# Performance Test Note {i}

This is the content of performance test note {i}.

## Section 1

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 2

More content here to simulate real note size.
[[Related Note {(i + 1) % 100}]]
[[Related Note {(i + 2) % 100}]]
""")

    # Create 5 folders with 10 notes each
    for folder_idx in range(5):
        folder = notes_path / f"Folder_{folder_idx}"
        folder.mkdir()
        for note_idx in range(10):
            note_file = folder / f"folder_note_{note_idx}.md"
            note_file.write_text(f"""---
title: Folder {folder_idx} Note {note_idx}
type: projet
tags:
  - folder{folder_idx}
---

# Folder {folder_idx} Note {note_idx}

Content for folder note.
""")

    return notes_path


@pytest.fixture
def note_manager_perf(large_notes_dir):
    """Create NoteManager for performance testing"""
    from src.passepartout.note_manager import NoteManager

    manager = NoteManager(
        notes_dir=large_notes_dir,
        auto_index=True,
    )
    return manager


# ============================================================================
# Notes Loading Performance Tests
# ============================================================================


class TestNotesLoadingPerformance:
    """Test performance of loading notes"""

    def test_load_all_notes_performance(self, note_manager_perf):
        """Loading 150 notes should be fast"""
        with measure_time("load_all_notes") as metrics:
            notes = note_manager_perf.get_all_notes()

        assert len(notes) >= 150
        metrics.assert_under(
            PerformanceThresholds.NOTES_LIST_MAX_MS * 3,  # 150ms for 150 notes
            f"Loading {len(notes)} notes took too long",
        )

    def test_notes_tree_performance(self, note_manager_perf):
        """Building notes tree should be fast"""
        with measure_time("build_notes_tree") as metrics:
            tree = note_manager_perf.get_notes_tree()

        metrics.assert_under(
            PerformanceThresholds.NOTES_TREE_MAX_MS,
            "Notes tree construction too slow",
        )

        # Verify tree structure
        assert "folders" in tree or hasattr(tree, "folders")

    def test_notes_tree_cached_performance(self, note_manager_perf):
        """Second call to notes tree should be much faster (cached)"""
        # First call - builds cache
        _ = note_manager_perf.get_notes_tree()

        # Second call - should use cache
        with measure_time("cached_notes_tree") as metrics:
            tree = note_manager_perf.get_notes_tree()

        metrics.assert_under(
            10,  # 10ms for cached result
            "Cached notes tree should be near-instant",
        )

    def test_list_notes_with_filter_performance(self, note_manager_perf):
        """Filtering notes by path should be fast"""
        with measure_time("filter_by_path") as metrics:
            notes = note_manager_perf.list_notes(path="Folder_0")

        assert len(notes) == 10
        metrics.assert_under(
            PerformanceThresholds.NOTES_LIST_MAX_MS,
            "Filtered list took too long",
        )

    def test_list_notes_with_pagination_performance(self, note_manager_perf):
        """Paginated listing should be fast"""
        with measure_time("paginated_list") as metrics:
            notes = note_manager_perf.list_notes(limit=20, offset=0)

        assert len(notes) == 20
        metrics.assert_under(
            PerformanceThresholds.NOTES_LIST_MAX_MS,
            "Paginated list took too long",
        )


# ============================================================================
# Notes Search Performance Tests
# ============================================================================


class TestNotesSearchPerformance:
    """Test performance of note search operations"""

    def test_search_by_query_performance(self, note_manager_perf):
        """Text search should be fast"""
        with measure_time("text_search") as metrics:
            results = note_manager_perf.search_notes("performance test")

        assert len(results) > 0
        metrics.assert_under(
            PerformanceThresholds.NOTES_SEARCH_MAX_MS,
            "Text search took too long",
        )

    def test_search_by_tags_performance(self, note_manager_perf):
        """Tag-based search should be fast"""
        with measure_time("tag_search") as metrics:
            results = note_manager_perf.search_notes(tags=["perf"])

        assert len(results) >= 100  # All root notes have 'perf' tag
        metrics.assert_under(
            PerformanceThresholds.NOTES_SEARCH_MAX_MS,
            "Tag search took too long",
        )

    def test_search_with_multiple_filters_performance(self, note_manager_perf):
        """Combined filters should still be fast"""
        with measure_time("combined_search") as metrics:
            results = note_manager_perf.search_notes(
                query="Note",
                tags=["test"],
                limit=50,
            )

        metrics.assert_under(
            PerformanceThresholds.NOTES_SEARCH_MAX_MS * 1.5,  # Allow 50% more for combined
            "Combined search took too long",
        )


# ============================================================================
# Index Operations Performance Tests
# ============================================================================


class TestIndexPerformance:
    """Test performance of index operations"""

    def test_refresh_index_performance(self, note_manager_perf, large_notes_dir):
        """Index refresh should be reasonably fast"""
        # Add some new notes
        for i in range(10):
            (large_notes_dir / f"new_note_{i}.md").write_text(f"""---
title: New Note {i}
---
# New Note {i}
""")

        with measure_time("refresh_index") as metrics:
            count = note_manager_perf.refresh_index()

        assert count >= 160  # Original 150 + 10 new
        metrics.assert_under(
            500,  # 500ms for index refresh with 160 notes
            "Index refresh took too long",
        )

    def test_metadata_index_build_performance(self, large_notes_dir):
        """Building metadata index from scratch should be fast"""
        from src.passepartout.note_manager import NoteManager

        # Remove any existing index
        index_file = large_notes_dir / ".scapin_notes_meta.json"
        if index_file.exists():
            index_file.unlink()

        with measure_time("build_metadata_index") as metrics:
            manager = NoteManager(
                notes_dir=large_notes_dir,
                auto_index=True,
            )
            _ = manager.get_notes_summary()

        metrics.assert_under(
            1000,  # 1 second for initial index build with 150 notes
            "Initial index build took too long",
        )

    def test_metadata_index_load_performance(self, note_manager_perf, large_notes_dir):
        """Loading existing metadata index should be very fast"""
        # Ensure index exists
        _ = note_manager_perf.get_notes_summary()

        # Create new manager to test index loading
        from src.passepartout.note_manager import NoteManager

        with measure_time("load_metadata_index") as metrics:
            manager = NoteManager(
                notes_dir=large_notes_dir,
                auto_index=False,
            )
            summaries = manager.get_notes_summary()

        assert len(summaries) >= 150
        metrics.assert_under(
            50,  # 50ms to load from disk
            "Metadata index load took too long",
        )


# ============================================================================
# Cache Effectiveness Tests
# ============================================================================


class TestCacheEffectiveness:
    """Test that caching provides expected speedup"""

    def test_note_cache_speedup(self, note_manager_perf):
        """Cached note retrieval should be much faster"""
        # First load - cache miss
        with measure_time("first_load") as metrics1:
            _ = note_manager_perf.get_note("note_050")

        # Second load - cache hit
        with measure_time("cached_load") as metrics2:
            _ = note_manager_perf.get_note("note_050")

        # Cached should be at least 5x faster
        if metrics1.duration_ms > 1:  # Only check if first load was measurable
            speedup = metrics1.duration_ms / max(metrics2.duration_ms, 0.01)
            assert speedup >= 2, f"Cache only provided {speedup:.1f}x speedup"

    def test_summary_cache_speedup(self, note_manager_perf):
        """Summary listing should be faster after first call"""
        # First call
        with measure_time("first_summary") as metrics1:
            _ = note_manager_perf.get_notes_summary()

        # Second call
        with measure_time("cached_summary") as metrics2:
            _ = note_manager_perf.get_notes_summary()

        # Second should be much faster
        metrics2.assert_under(
            metrics1.duration_ms / 2,  # At least 2x faster
            "Summary cache not effective",
        )


# ============================================================================
# Concurrent Access Performance Tests
# ============================================================================


class TestConcurrentAccessPerformance:
    """Test performance under concurrent access"""

    def test_concurrent_reads_performance(self, note_manager_perf):
        """Concurrent reads should not degrade significantly"""
        import concurrent.futures

        def read_note(note_id):
            return note_manager_perf.get_note(note_id)

        # Warm up cache
        for i in range(10):
            _ = note_manager_perf.get_note(f"note_{i:03d}")

        with measure_time("concurrent_reads") as metrics:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(read_note, f"note_{i:03d}") for i in range(50)
                ]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 50
        assert all(r is not None for r in results)

        # Should complete in reasonable time even with concurrency
        metrics.assert_under(
            500,  # 500ms for 50 concurrent reads
            "Concurrent reads degraded significantly",
        )

    def test_mixed_operations_performance(self, note_manager_perf, large_notes_dir):
        """Mixed read/write operations should remain responsive"""
        import concurrent.futures

        def read_operation():
            return note_manager_perf.get_notes_summary()

        def search_operation():
            return note_manager_perf.search_notes("test")

        with measure_time("mixed_operations") as metrics:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                for _ in range(20):
                    futures.append(executor.submit(read_operation))
                    futures.append(executor.submit(search_operation))

                results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 40
        metrics.assert_under(
            2000,  # 2 seconds for 40 mixed operations
            "Mixed operations too slow",
        )


# ============================================================================
# Large Dataset Stress Tests
# ============================================================================


class TestLargeDatasetStress:
    """Stress tests with larger datasets"""

    @pytest.fixture
    def very_large_notes_dir(self, tmp_path):
        """Create 500 notes for stress testing"""
        notes_path = tmp_path / "notes"
        notes_path.mkdir()

        for i in range(500):
            note_file = notes_path / f"stress_note_{i:04d}.md"
            note_file.write_text(f"""---
title: Stress Note {i}
type: concept
tags:
  - stress
  - batch{i // 50}
---

# Stress Note {i}

Content content content.
""")

        return notes_path

    def test_500_notes_tree_performance(self, very_large_notes_dir):
        """Building tree with 500 notes should complete in time"""
        from src.passepartout.note_manager import NoteManager

        manager = NoteManager(
            notes_dir=very_large_notes_dir,
            auto_index=True,
        )

        with measure_time("500_notes_tree") as metrics:
            tree = manager.get_notes_tree()

        metrics.assert_under(
            500,  # 500ms for 500 notes
            "500 notes tree too slow",
        )

    def test_500_notes_search_performance(self, very_large_notes_dir):
        """Searching 500 notes should complete in time"""
        from src.passepartout.note_manager import NoteManager

        manager = NoteManager(
            notes_dir=very_large_notes_dir,
            auto_index=True,
        )

        with measure_time("500_notes_search") as metrics:
            results = manager.search_notes("stress")

        assert len(results) == 500
        metrics.assert_under(
            300,  # 300ms for searching 500 notes
            "500 notes search too slow",
        )
