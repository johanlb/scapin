#!/usr/bin/env python3
"""
Fix Corrupted Note Titles

Finds and fixes notes with corrupted titles (e.g., "ultimate-guitar-2d66ff7d"
instead of "Ultimate Guitar"). These corruptions happen when notes are synced
with Apple Notes using the filename stem instead of the frontmatter title.

Usage:
    # Dry run (show what would be fixed)
    python scripts/fix_corrupted_titles.py

    # Actually fix the titles
    python scripts/fix_corrupted_titles.py --fix

    # Verbose mode
    python scripts/fix_corrupted_titles.py --fix --verbose
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.logger import get_logger  # noqa: E402

if TYPE_CHECKING:
    import logging

logger: logging.Logger = get_logger("scripts.fix_titles")

# Pattern for corrupted titles: slug with hash suffix (e.g., "my-title-2d66ff7d")
CORRUPTED_TITLE_PATTERN = re.compile(r"^[a-z0-9-]+-[a-f0-9]{8}$")


def is_corrupted_title(title: str) -> bool:
    """
    Check if a title looks corrupted (slug with hash suffix).

    Examples:
        "ultimate-guitar-2d66ff7d" -> True
        "Ultimate Guitar" -> False
        "my-project-abc" -> False (not 8 hex chars)
    """
    return bool(CORRUPTED_TITLE_PATTERN.match(title.lower()))


def fix_title(corrupted: str) -> str:
    """
    Fix a corrupted title.

    Removes the hash suffix and converts to title case.

    Args:
        corrupted: Corrupted title like "ultimate-guitar-2d66ff7d"

    Returns:
        Fixed title like "Ultimate Guitar"
    """
    # Remove hash suffix (8 hex chars at the end)
    cleaned = (
        corrupted.rsplit("-", 1)[0]
        if re.match(r".*-[a-f0-9]{8}$", corrupted)
        else corrupted
    )

    # Convert dashes/underscores to spaces and title case
    cleaned = cleaned.replace("-", " ").replace("_", " ")
    return cleaned.title()


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from note content.

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    if not content.startswith("---"):
        return {}, content

    try:
        # Find the closing ---
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return {}, content

        frontmatter_str = content[4:end_idx]
        frontmatter = yaml.safe_load(frontmatter_str) or {}
        body = content[end_idx + 4:].lstrip("\n")
        return frontmatter, body
    except yaml.YAMLError:
        return {}, content


def rebuild_content(frontmatter: dict, body: str) -> str:
    """
    Rebuild note content from frontmatter and body.
    """
    if not frontmatter:
        return body

    # Use yaml.dump with proper formatting
    frontmatter_str = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return f"---\n{frontmatter_str}---\n\n{body}"


def find_corrupted_notes(notes_dir: Path) -> list[tuple[Path, str, str]]:
    """
    Find all notes with corrupted titles.

    Returns:
        List of (file_path, current_title, suggested_title) tuples
    """
    corrupted = []

    for note_path in notes_dir.rglob("*.md"):
        # Skip hidden files
        if any(part.startswith(".") for part in note_path.parts):
            continue

        try:
            content = note_path.read_text(encoding="utf-8")
            frontmatter, _ = parse_frontmatter(content)

            title = frontmatter.get("title", "")
            if title and is_corrupted_title(title):
                suggested = fix_title(title)
                corrupted.append((note_path, title, suggested))

        except Exception as e:
            logger.warning(f"Error reading {note_path}: {e}")

    return corrupted


def fix_note_title(note_path: Path, new_title: str) -> bool:
    """
    Fix a note's title in its frontmatter.

    Returns:
        True if successful, False otherwise
    """
    try:
        content = note_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        if not frontmatter:
            logger.warning(f"No frontmatter found in {note_path}")
            return False

        # Update title
        frontmatter["title"] = new_title

        # Rebuild and save
        new_content = rebuild_content(frontmatter, body)
        note_path.write_text(new_content, encoding="utf-8")

        return True

    except Exception as e:
        logger.error(f"Error fixing {note_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Find and fix corrupted note titles"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Actually fix the titles (default is dry run)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--notes-dir",
        type=Path,
        default=Path.home() / "Documents" / "Scapin" / "Notes",
        help="Notes directory (default: ~/Documents/Scapin/Notes)",
    )
    args = parser.parse_args()

    if not args.notes_dir.exists():
        print(f"Error: Notes directory not found: {args.notes_dir}")
        sys.exit(1)

    print(f"Scanning notes in: {args.notes_dir}")
    print()

    corrupted = find_corrupted_notes(args.notes_dir)

    if not corrupted:
        print("No corrupted titles found!")
        return

    print(f"Found {len(corrupted)} notes with corrupted titles:\n")

    fixed_count = 0
    for note_path, current, suggested in corrupted:
        rel_path = note_path.relative_to(args.notes_dir)

        if args.verbose:
            print(f"  File: {rel_path}")
            print(f"    Current:   {current}")
            print(f"    Suggested: {suggested}")
        else:
            print(f"  {current!r} -> {suggested!r}")
            if args.verbose:
                print(f"    ({rel_path})")

        if args.fix:
            if fix_note_title(note_path, suggested):
                fixed_count += 1
                if args.verbose:
                    print("    -> Fixed!")
            else:
                print("    -> FAILED")

        if args.verbose:
            print()

    print()
    if args.fix:
        print(f"Fixed {fixed_count}/{len(corrupted)} notes")
        print()
        print("IMPORTANT: Run the index rebuild to update the search index:")
        print("  curl -X POST http://localhost:8000/api/notes/index/rebuild")
    else:
        print("This was a dry run. Use --fix to actually fix the titles.")


if __name__ == "__main__":
    main()
