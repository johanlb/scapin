#!/usr/bin/env python3
"""Find Apple Notes that don't have a corresponding Scapin note."""

import json
import subprocess
from pathlib import Path

NOTES_DIR = Path("/Users/johan/Documents/Scapin/Notes")
SYNC_MAPPING_FILE = NOTES_DIR / "apple_notes_sync.json"

def get_apple_notes():
    """Get all Apple Notes from iCloud (excluding Recently Deleted)."""
    script = '''
    tell application "Notes"
        set noteList to {}
        set accountRef to account "iCloud"
        set allFolders to every folder of accountRef

        repeat with f in allFolders
            set folderName to name of f
            if folderName is not "Recently Deleted" then
                set folderNotes to every note of f
                set noteCount to count of folderNotes

                repeat with i from 1 to noteCount
                    set n to item i of folderNotes
                    set noteId to id of n
                    set noteName to name of n
                    set end of noteList to noteId & "|||" & noteName & "|||" & folderName
                end repeat
            end if
        end repeat

        set AppleScript's text item delimiters to "###"
        return noteList as text
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return []

    notes = []
    if result.stdout.strip():
        for entry in result.stdout.strip().split("###"):
            if "|||" in entry:
                parts = entry.split("|||")
                notes.append({
                    "id": parts[0],
                    "name": parts[1] if len(parts) > 1 else "?",
                    "folder": parts[2] if len(parts) > 2 else "?"
                })
    return notes

def get_synced_apple_ids():
    """Get Apple IDs that are in the sync mapping."""
    if not SYNC_MAPPING_FILE.exists():
        return set()

    with open(SYNC_MAPPING_FILE) as f:
        mappings = json.load(f)

    return set(mappings.keys())

def main():
    print("Fetching Apple Notes...")
    apple_notes = get_apple_notes()
    print(f"Apple Notes found: {len(apple_notes)}")

    synced_ids = get_synced_apple_ids()
    print(f"Synced Apple IDs: {len(synced_ids)}")

    # Find orphan notes (in Apple but not synced to Scapin)
    orphans = []
    for note in apple_notes:
        if note["id"] not in synced_ids:
            orphans.append(note)

    print(f"\nOrphan Apple Notes (not synced to Scapin): {len(orphans)}")

    if orphans:
        # Group by folder
        by_folder = {}
        for note in orphans:
            folder = note.get("folder", "?")
            if folder not in by_folder:
                by_folder[folder] = []
            by_folder[folder].append(note)

        print("\nOrphan notes by folder:")
        for folder in sorted(by_folder.keys()):
            notes = by_folder[folder]
            print(f"\n  [{folder}] ({len(notes)} notes)")
            for note in sorted(notes, key=lambda x: x["name"])[:10]:
                print(f"    - {note['name']}")
            if len(notes) > 10:
                print(f"    ... and {len(notes) - 10} more")

if __name__ == "__main__":
    main()
