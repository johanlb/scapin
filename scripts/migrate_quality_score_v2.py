#!/usr/bin/env python3
"""
Quality Score Migration Script: v1 -> v2

Recalculates quality_score for all notes using the new v2 formula.

New Formula (base 0, max 100):
    - Content: +10 per threshold (50, 200, 500 words)
    - Structure: +15 summary, +min(10, sections*3)
    - Links: +min(15, outgoing_links*3)
    - Completeness: Calculated at retouche time (not here)

Usage:
    # Dry run (shows what would be updated)
    python scripts/migrate_quality_score_v2.py --dry-run

    # Run migration
    python scripts/migrate_quality_score_v2.py

    # Show statistics only
    python scripts/migrate_quality_score_v2.py --stats

    # Migrate specific note
    python scripts/migrate_quality_score_v2.py --note-id <note_id>
"""

import argparse
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.passepartout.note_manager import NoteManager
from src.passepartout.note_metadata import NoteMetadataStore
from src.utils import get_data_dir


def count_words(content: str) -> int:
    """Count words in content, excluding frontmatter."""
    # Remove frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    # Count words
    words = re.findall(r"\b\w+\b", content)
    return len(words)


def has_summary(content: str) -> bool:
    """Check if content has a summary section."""
    summary_patterns = [
        r"^##?\s*[Rr]ésumé",
        r"^##?\s*[Ss]ummary",
        r"^>\s*\*\*[Rr]ésumé\*\*",
        r"^>\s*\*\*[Ss]ummary\*\*",
    ]
    return any(re.search(pattern, content, re.MULTILINE) for pattern in summary_patterns)


def count_sections(content: str) -> int:
    """Count markdown sections (## headers)."""
    return len(re.findall(r"^##\s+\w", content, re.MULTILINE))


def extract_wikilinks(content: str) -> list[str]:
    """Extract wikilinks from content."""
    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
    return list(set(re.findall(pattern, content)))


def calculate_quality_score_v2(content: str) -> int:
    """
    Calculate quality score using v2 formula.

    Formula:
        - Base: 0
        - Content: +10 per threshold (50, 200, 500 words) = max 30
        - Structure: +15 summary, +min(10, sections*3) = max 25
        - Links: +min(15, outgoing_links*3) = max 15
        - Max: 70 (completeness bonus added at retouche time)
    """
    score = 0

    # Content bonus (max 30)
    word_count = count_words(content)
    if word_count >= 50:
        score += 10
    if word_count >= 200:
        score += 10
    if word_count >= 500:
        score += 10

    # Structure bonus (max 25)
    if has_summary(content):
        score += 15
    section_count = count_sections(content)
    score += min(10, section_count * 3)

    # Links bonus (max 15)
    outgoing_links = extract_wikilinks(content)
    score += min(15, len(outgoing_links) * 3)

    return min(100, max(0, score))


def get_notes_dir() -> Path:
    """Get the notes directory."""
    return get_data_dir() / "notes"


def get_metadata_db() -> Path:
    """Get the metadata database path."""
    return get_data_dir() / "notes_meta.db"


def migrate_note(
    note_manager: NoteManager,
    metadata_store: NoteMetadataStore,
    note_id: str,
    dry_run: bool = False,
) -> tuple[int | None, int | None]:
    """
    Migrate a single note's quality score.

    Returns:
        Tuple of (old_score, new_score) or (None, None) if note not found
    """
    note = note_manager.get_note(note_id)
    if note is None:
        return None, None

    metadata = metadata_store.get(note_id)
    if metadata is None:
        return None, None

    old_score = metadata.quality_score
    new_score = calculate_quality_score_v2(note.content)

    if not dry_run:
        metadata.quality_score = new_score
        metadata_store.save(metadata)

    return old_score, new_score


def show_stats(metadata_store: NoteMetadataStore) -> None:
    """Show current quality score statistics."""
    all_metadata = metadata_store.list_all()

    scores = [m.quality_score for m in all_metadata if m.quality_score is not None]
    null_scores = [m for m in all_metadata if m.quality_score is None]

    print("\n=== Quality Score Statistics ===")
    print(f"Total notes with metadata: {len(all_metadata)}")
    print(f"Notes with score: {len(scores)}")
    print(f"Notes without score: {len(null_scores)}")

    if scores:
        print("\nScore distribution:")
        print(f"  Min: {min(scores)}")
        print(f"  Max: {max(scores)}")
        print(f"  Average: {sum(scores) / len(scores):.1f}")

        # Distribution buckets
        buckets = {
            "0-20": 0,
            "21-40": 0,
            "41-60": 0,
            "61-80": 0,
            "81-100": 0,
        }
        for score in scores:
            if score <= 20:
                buckets["0-20"] += 1
            elif score <= 40:
                buckets["21-40"] += 1
            elif score <= 60:
                buckets["41-60"] += 1
            elif score <= 80:
                buckets["61-80"] += 1
            else:
                buckets["81-100"] += 1

        print("\nDistribution:")
        for bucket, count in buckets.items():
            bar = "#" * (count * 40 // max(1, len(scores)))
            print(f"  {bucket:>6}: {count:>4} {bar}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate quality scores to v2 formula"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics only, don't migrate",
    )
    parser.add_argument(
        "--note-id",
        type=str,
        help="Migrate a specific note only",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    # Initialize stores
    notes_dir = get_notes_dir()
    metadata_db = get_metadata_db()

    if not notes_dir.exists():
        print(f"Error: Notes directory not found: {notes_dir}")
        sys.exit(1)

    if not metadata_db.exists():
        print(f"Error: Metadata database not found: {metadata_db}")
        sys.exit(1)

    note_manager = NoteManager(notes_dir)
    metadata_store = NoteMetadataStore(metadata_db)

    # Stats only mode
    if args.stats:
        show_stats(metadata_store)
        return

    # Single note mode
    if args.note_id:
        old_score, new_score = migrate_note(
            note_manager, metadata_store, args.note_id, args.dry_run
        )
        if old_score is None:
            print(f"Note not found: {args.note_id}")
            sys.exit(1)

        action = "Would update" if args.dry_run else "Updated"
        print(f"{action} {args.note_id}: {old_score} -> {new_score}")
        return

    # Full migration
    print("=== Quality Score Migration v1 -> v2 ===")
    if args.dry_run:
        print("DRY RUN - No changes will be made\n")

    all_metadata = metadata_store.list_all()
    total = len(all_metadata)
    updated = 0
    skipped = 0
    errors = 0

    score_changes = []

    for i, metadata in enumerate(all_metadata, 1):
        note_id = metadata.note_id

        try:
            old_score, new_score = migrate_note(
                note_manager, metadata_store, note_id, args.dry_run
            )

            if old_score is None:
                skipped += 1
                if args.verbose:
                    print(f"  [{i}/{total}] SKIP {note_id} (note not found)")
                continue

            updated += 1
            change = (new_score or 0) - (old_score or 0)
            score_changes.append(change)

            if args.verbose:
                print(f"  [{i}/{total}] {note_id}: {old_score} -> {new_score} ({change:+d})")

        except Exception as e:
            errors += 1
            print(f"  [{i}/{total}] ERROR {note_id}: {e}")

    # Summary
    print("\n=== Migration Summary ===")
    print(f"Total notes: {total}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")

    if score_changes:
        avg_change = sum(score_changes) / len(score_changes)
        print("\nScore changes:")
        print(f"  Average change: {avg_change:+.1f}")
        print(f"  Max increase: {max(score_changes):+d}")
        print(f"  Max decrease: {min(score_changes):+d}")

    if args.dry_run:
        print("\nDRY RUN - No changes were made. Run without --dry-run to apply.")


if __name__ == "__main__":
    main()
