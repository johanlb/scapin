#!/usr/bin/env python3
"""Check which Scapin notes are not synced to Apple Notes."""

import json
from pathlib import Path

NOTES_DIR = Path("/Users/johan/Documents/Scapin/Notes")
SYNC_MAPPING_FILE = NOTES_DIR / "apple_notes_sync.json"
# Only exclude trash and hidden
EXCLUDED_PARTS = {"_Supprimées"}

def get_scapin_notes():
    """Get all Scapin note files."""
    notes = []
    for note_path in NOTES_DIR.rglob("*.md"):
        rel_path = note_path.relative_to(NOTES_DIR)
        # Skip hidden files/folders
        if any(part.startswith(".") for part in rel_path.parts):
            continue
        # Skip excluded folders
        if any(excl in rel_path.parts for excl in EXCLUDED_PARTS):
            continue
        notes.append(str(rel_path))
    return sorted(notes)

def get_synced_notes():
    """Get notes that have apple_id in sync mapping."""
    if not SYNC_MAPPING_FILE.exists():
        return {}

    with open(SYNC_MAPPING_FILE) as f:
        mappings = json.load(f)

    # Mapping is apple_id -> {scapin_path, ...}
    synced = {}
    for apple_id, data in mappings.items():
        scapin_path = data.get("scapin_path", "")
        if scapin_path:
            synced[scapin_path] = apple_id
    return synced

def main():
    scapin_notes = get_scapin_notes()
    synced_notes = get_synced_notes()

    print(f"Scapin notes (files): {len(scapin_notes)}")
    print(f"Synced notes (in mapping): {len(synced_notes)}")

    # Find unsynced
    unsynced = []
    for note in scapin_notes:
        if note not in synced_notes:
            unsynced.append(note)

    print(f"\nUnsynced Scapin notes: {len(unsynced)}")

    if unsynced:
        # Group by folder
        by_folder = {}
        for note in unsynced:
            parts = note.split("/")
            folder = "/".join(parts[:-1]) if len(parts) > 1 else "(root)"
            if folder not in by_folder:
                by_folder[folder] = []
            by_folder[folder].append(parts[-1])

        print("\nUnsynced notes by folder:")
        for folder in sorted(by_folder.keys()):
            notes = by_folder[folder]
            print(f"\n  {folder}/ ({len(notes)} notes)")
            for note in sorted(notes)[:5]:
                print(f"    - {note}")
            if len(notes) > 5:
                print(f"    ... and {len(notes) - 5} more")

    # Find synced but missing files
    missing = []
    for scapin_path in synced_notes:
        full_path = NOTES_DIR / scapin_path
        if not full_path.exists():
            missing.append(scapin_path)

    if missing:
        print(f"\nSynced but file missing: {len(missing)}")
        for p in missing[:10]:
            print(f"  - {p}")

if __name__ == "__main__":
    main()
