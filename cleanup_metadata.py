#!/usr/bin/env python3
"""Clean up stale entries from metadata index."""

import json
from pathlib import Path

NOTES_DIR = Path("/Users/johan/Documents/Scapin/Notes")
METADATA_FILE = NOTES_DIR / ".scapin_notes_meta.json"

def main():
    # Load metadata
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print(f"Metadata entries: {len(metadata)}")

    # Check which entries have actual files
    stale = []
    valid = {}

    for note_id, data in metadata.items():
        path = data.get("path", "")
        if path:
            file_path = NOTES_DIR / path / f"{note_id}.md"
        else:
            file_path = NOTES_DIR / f"{note_id}.md"

        if file_path.exists():
            valid[note_id] = data
        else:
            stale.append((note_id, data.get("title", "?"), path))

    print(f"Valid entries: {len(valid)}")
    print(f"Stale entries: {len(stale)}")

    if stale:
        print("\nStale entries (first 20):")
        for note_id, title, path in stale[:20]:
            print(f"  - {title} ({path}/{note_id})")
        if len(stale) > 20:
            print(f"  ... and {len(stale) - 20} more")

        # Save cleaned metadata
        print(f"\nCleaning metadata index...")
        with open(METADATA_FILE, "w") as f:
            json.dump(valid, f, indent=2, ensure_ascii=False)
        print(f"Done. Removed {len(stale)} stale entries.")

if __name__ == "__main__":
    main()
