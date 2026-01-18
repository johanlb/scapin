"""
Apple Notes Client

AppleScript-based client for interacting with Apple Notes.app.
"""

import subprocess
from datetime import datetime
from typing import Optional

from src.integrations.apple.notes_models import AppleFolder, AppleNote
from src.monitoring.logger import get_logger

logger = get_logger("integrations.apple.notes")


class AppleNotesClient:
    """Client for interacting with Apple Notes via AppleScript"""

    def __init__(self) -> None:
        """Initialize the Apple Notes client"""
        # Assuming 'config' and 'AppleNotesConfig' are defined elsewhere or will be added.
        # For now, I'll comment out the new lines that depend on them to maintain syntax.
        # self._config = config or AppleNotesConfig()
        # self._script_path = None
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if Apple Notes is available on this system"""
        if self._available is not None:
            return self._available

        try:
            self._run_applescript(
                'tell application "System Events" to (name of processes) contains "Notes"'
            )
            # Even if Notes isn't running, we can still use it
            self._available = True
        except Exception as e:
            logger.warning(f"Apple Notes not available: {e}")
            self._available = False

        return self._available

    def get_folders(self) -> list[AppleFolder]:
        """Get all folders from Apple Notes (including nested folders with full paths)

        Only includes truly top-level folders and their children.
        Uses folder container class to distinguish top-level from nested folders.
        """
        # AppleScript to get all folders with full paths
        # Returns: "name|||path" for each folder
        script = """
        tell application "Notes"
            set allFolders to {}

            -- First, identify true top-level folders (container is an account)
            repeat with f in folders
                set isTopLevel to false
                try
                    set containerClass to class of container of f as string
                    if containerClass is "account" then
                        set isTopLevel to true
                    end if
                end try

                if isTopLevel then
                    set fName to name of f
                    set end of allFolders to fName & "|||" & fName
                    my getFolderChildren(f, fName, allFolders)
                end if
            end repeat

            return allFolders
        end tell

        on getFolderChildren(parentFolder, parentPath, folderList)
            tell application "Notes"
                try
                    repeat with subf in folders of parentFolder
                        set subName to name of subf
                        set subPath to parentPath & "/" & subName
                        set end of folderList to subName & "|||" & subPath
                        my getFolderChildren(subf, subPath, folderList)
                    end repeat
                end try
            end tell
        end getFolderChildren
        """
        result = self._run_applescript(script)
        folder_entries = self._parse_list(result)
        folders = []

        for entry in folder_entries:
            if "|||" in entry:
                name, path = entry.split("|||", 1)
                folders.append(AppleFolder(name=name.strip(), path=path.strip()))
            else:
                folders.append(AppleFolder(name=entry.strip(), path=entry.strip()))
        return folders

    def get_notes_in_folder(self, folder_path: str, include_body: bool = True) -> list[AppleNote]:
        """Get all notes in a specific folder

        Args:
            folder_path: Folder path like "Notes" or "Notes/Entités" for nested folders
            include_body: If True, fetch full HTML body (slow). If False, only metadata (fast).
        """
        # Build AppleScript to navigate to nested folder
        path_parts = folder_path.split("/")
        escaped_parts = [part.replace('"', '\\"') for part in path_parts]

        # Build nested tell blocks for folder path
        if len(escaped_parts) == 1:
            # Simple case: top-level folder
            folder_access = f'folder "{escaped_parts[0]}"'
        else:
            # Nested folder: tell folder "A" to tell folder "B"...
            folder_access = " of ".join([f'folder "{p}"' for p in reversed(escaped_parts)])

        # Optimization: Conditionally fetch body
        body_field = "body of n" if include_body else '""'

        # Robust Date Parsing: extracting components directly in AppleScript
        # Returns: yyyy-mm-dd HH:MM:SS
        date_extraction = """
        -- Capture date objects
        set cDate to creation date of n
        set mDate to modification date of n
        
        -- Helper to format number with leading zero
        script DateFormatter
            on pad(num)
                if num < 10 then
                    return "0" & num
                else
                    return num as string
                end if
            end pad
            
            on formatDate(d)
                try
                    if d is missing value then
                        return "1970-01-01 00:00:00"
                    end if
                    set y to year of d
                    set m to month of d as integer
                    set d_day to day of d
                    set t_hour to hours of d
                    set t_min to minutes of d
                    set t_sec to seconds of d
                    
                    return (y as string) & "-" & my pad(m) & "-" & my pad(d_day) & " " & my pad(t_hour) & ":" & my pad(t_min) & ":" & my pad(t_sec)
                on error
                    return "1970-01-01 00:00:00"
                end try
            end formatDate
        end script
        
        set cDateStr to DateFormatter's formatDate(cDate)
        set mDateStr to DateFormatter's formatDate(mDate)
        """

        script = f"""
        tell application "Notes"
            set notesList to {{}}
            tell {folder_access}
                repeat with n in notes
                    {date_extraction}
                    
                    set noteData to {{id of n, name of n, {body_field}, cDateStr, mDateStr}}
                    set end of notesList to noteData
                end repeat
            end tell
            return notesList
        end tell
        """

        try:
            result = self._run_applescript(script)
            return self._parse_notes(result, folder_path)
        except Exception as e:
            logger.error(f"Failed to get notes from folder '{folder_path}': {e}")
            return []

    def get_all_notes(self, include_body: bool = True) -> list[AppleNote]:
        """Get all notes from all folders (including nested folders)"""
        folders = self.get_folders()
        all_notes: list[AppleNote] = []

        for folder in folders:
            # Skip Recently Deleted and Quick Notes
            if folder.name in ("Recently Deleted", "Quick Notes"):
                continue
            # Use folder.path to access nested folders
            notes = self.get_notes_in_folder(folder.path, include_body=include_body)
            for note in notes:
                # Update folder field to use full path
                note.folder = folder.path
            all_notes.extend(notes)

        return all_notes

    def get_deleted_notes(self) -> list[AppleNote]:
        """Get notes from the 'Recently Deleted' folder in Apple Notes

        Returns a list of notes that have been deleted but not yet permanently removed.
        """
        # Improved robustness for deleted notes too
        date_extraction = """
        set cDate to creation date of n
        set mDate to modification date of n
        
        script DateFormatter
            on pad(num)
                if num < 10 then return "0" & num else return num as string
            end pad
            on formatDate(d)
                return (year of d as string) & "-" & my pad(month of d as integer) & "-" & my pad(day of d) & " " & my pad(hours of d) & ":" & my pad(minutes of d) & ":" & my pad(seconds of d)
            end formatDate
        end script
        
        set cDateStr to DateFormatter's formatDate(cDate)
        set mDateStr to DateFormatter's formatDate(mDate)
        """

        script = f"""
        tell application "Notes"
            set notesList to {{}}
            try
                tell folder "Recently Deleted"
                    repeat with n in notes
                        {date_extraction}
                        set noteData to {{id of n, name of n, body of n, cDateStr, mDateStr}}
                        set end of notesList to noteData
                    end repeat
                end tell
            on error errMsg
                -- Folder may not exist or be empty
                return {{}}
            end try
            return notesList
        end tell
        """

        try:
            result = self._run_applescript(script, timeout=180)
            return self._parse_notes(result, "Recently Deleted")
        except Exception as e:
            logger.error(f"Failed to get deleted notes: {e}")
            return []

    def get_note_by_id(self, note_id: str) -> Optional[AppleNote]:
        """Get a specific note by its ID"""
        escaped_id = note_id.replace('"', '\\"')

        date_extraction = """
        set cDate to creation date of n
        set mDate to modification date of n
        
        script DateFormatter
            on pad(num)
                if num < 10 then return "0" & num else return num as string
            end pad
            on formatDate(d)
                return (year of d as string) & "-" & my pad(month of d as integer) & "-" & my pad(day of d) & " " & my pad(hours of d) & ":" & my pad(minutes of d) & ":" & my pad(seconds of d)
            end formatDate
        end script
        
        set cDateStr to DateFormatter's formatDate(cDate)
        set mDateStr to DateFormatter's formatDate(mDate)
        """

        script = f'''
        tell application "Notes"
            try
                set n to note id "{escaped_id}"
                set folderName to name of container of n
                
                {date_extraction}
                
                return {{id of n, name of n, body of n, folderName, cDateStr, mDateStr}}
            on error
                return ""
            end try
        end tell
        '''

        try:
            result = self._run_applescript(script)
            if not result or result == '""':
                return None
            return self._parse_single_note(result)
        except Exception as e:
            logger.error(f"Failed to get note by ID '{note_id}': {e}")
            return None

    def create_note(
        self,
        folder_name: str,
        title: str,
        body_html: str,
    ) -> Optional[str]:
        """
        Create a new note in Apple Notes

        Args:
            folder_name: Target folder name
            title: Note title
            body_html: Note body in HTML format

        Returns:
            The ID of the created note, or None if failed
        """
        escaped_folder = folder_name.replace('"', '\\"')
        escaped_title = title.replace('"', '\\"')
        escaped_body = body_html.replace('"', '\\"').replace("\n", "\\n")

        script = f'''
        tell application "Notes"
            tell folder "{escaped_folder}"
                set newNote to make new note with properties {{name:"{escaped_title}", body:"{escaped_body}"}}
                return id of newNote
            end tell
        end tell
        '''

        try:
            result = self._run_applescript(script)
            note_id = result.strip()
            logger.info(f"Created note '{title}' in folder '{folder_name}'")
            return note_id
        except Exception as e:
            logger.error(f"Failed to create note '{title}': {e}")
            return None

    def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        body_html: Optional[str] = None,
    ) -> bool:
        """
        Update an existing note in Apple Notes

        Args:
            note_id: The note ID to update
            title: New title (optional)
            body_html: New body in HTML format (optional)

        Returns:
            True if successful, False otherwise
        """
        escaped_id = note_id.replace('"', '\\"')

        properties = []
        if title is not None:
            escaped_title = title.replace('"', '\\"')
            properties.append(f'name:"{escaped_title}"')
        if body_html is not None:
            escaped_body = body_html.replace('"', '\\"').replace("\n", "\\n")
            properties.append(f'body:"{escaped_body}"')

        if not properties:
            return True  # Nothing to update

        props_str = ", ".join(properties)
        script = f'''
        tell application "Notes"
            try
                set n to note id "{escaped_id}"
                set properties of n to {{{props_str}}}
                return "success"
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        '''

        try:
            result = self._run_applescript(script)
            if result.startswith("error:"):
                logger.error(f"Failed to update note: {result}")
                return False
            logger.info(f"Updated note {note_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update note '{note_id}': {e}")
            return False

    def delete_note(self, note_id: str) -> bool:
        """
        Delete a note from Apple Notes (moves to Recently Deleted)

        Args:
            note_id: The note ID to delete

        Returns:
            True if successful, False otherwise
        """
        escaped_id = note_id.replace('"', '\\"')

        script = f'''
        tell application "Notes"
            try
                delete note id "{escaped_id}"
                return "success"
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        '''

        try:
            result = self._run_applescript(script)
            if result.startswith("error:"):
                logger.error(f"Failed to delete note: {result}")
                return False
            logger.info(f"Deleted note {note_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete note '{note_id}': {e}")
            return False

    def create_folder(self, folder_name: str) -> bool:
        """
        Create a new folder in Apple Notes

        Args:
            folder_name: Name of the folder to create

        Returns:
            True if successful, False otherwise
        """
        escaped_name = folder_name.replace('"', '\\"')

        script = f'''
        tell application "Notes"
            try
                make new folder with properties {{name:"{escaped_name}"}}
                return "success"
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        '''

        try:
            result = self._run_applescript(script)
            if result.startswith("error:"):
                # Folder might already exist
                if "already exists" in result.lower():
                    return True
                logger.error(f"Failed to create folder: {result}")
                return False
            logger.info(f"Created folder '{folder_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            return False

    def move_note_to_folder(self, note_id: str, folder_name: str) -> bool:
        """
        Move a note to a different folder

        Args:
            note_id: The note ID to move
            folder_name: Target folder name

        Returns:
            True if successful, False otherwise
        """
        escaped_id = note_id.replace('"', '\\"')
        escaped_folder = folder_name.replace('"', '\\"')

        script = f'''
        tell application "Notes"
            try
                move note id "{escaped_id}" to folder "{escaped_folder}"
                return "success"
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        '''

        try:
            result = self._run_applescript(script)
            if result.startswith("error:"):
                logger.error(f"Failed to move note: {result}")
                return False
            logger.info(f"Moved note {note_id} to folder '{folder_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to move note '{note_id}': {e}")
            return False

    def _run_applescript(self, script: str, timeout: int = 180) -> str:
        """Execute an AppleScript and return the result

        Args:
            script: AppleScript code to execute
            timeout: Maximum execution time in seconds (default 180s for large folders)
        """
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                raise RuntimeError(f"AppleScript error: {result.stderr}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("AppleScript timed out") from e
        except Exception as e:
            raise RuntimeError(f"Failed to run AppleScript: {e}") from e

    def _parse_list(self, result: str) -> list[str]:
        """Parse an AppleScript list result"""
        if not result:
            return []
        # AppleScript returns comma-separated values
        items = result.split(", ")
        return [item.strip() for item in items if item.strip()]

    def _parse_notes(self, result: str, folder_name: str) -> list[AppleNote]:
        """Parse notes from AppleScript result"""
        if not result:
            return []

        notes: list[AppleNote] = []

        # The result is a complex nested structure
        # Each note is: {id, name, body, creation_date, modification_date}

        # NOTE: AppleScript output with list of lists can be tricky to parse with regex
        # especially if body contains commas.
        # But we are getting string representation of a list of lists.
        # e.g.: {{id, name, body, date, date}, {id, ...}}

        # More robust parsing needed if bodies are large/complex.
        # For now, relying on the pattern matcher which seems to handle it reasonably well
        # given AppleScript's string conversion quirks, BUT:
        # We need to update pattern for our new date format (YYYY-MM-DD HH:MM:SS)

        import re

        # Find all note entries using the ID pattern
        # The new date format is YYYY-MM-DD HH:MM:SS which doesn't contain commas or standard AppleScript date junk
        # Pattern: (id), (name), (body), (date), (date)
        # Note: Body might be empty string "" if include_body=False

        # Updated regex to handle standard ISO-like dates
        note_pattern = r"(x-coredata://[^,]+), ([^,]+), (.*?), (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}), (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
        matches = re.findall(note_pattern, result, re.DOTALL)

        for match in matches:
            try:
                note_id, name, body, created_str, modified_str = match
                notes.append(
                    AppleNote(
                        id=note_id.strip(),
                        name=name.strip(),
                        body_html=body.strip(),
                        folder=folder_name,
                        created_at=self._parse_date(created_str),
                        modified_at=self._parse_date(modified_str),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse note: {e}")
                continue

        return notes

    def _parse_single_note(self, result: str) -> Optional[AppleNote]:
        """Parse a single note from AppleScript result"""
        import re

        # Pattern: {id, name, body, folder, creation_date, modification_date}
        # Updated for ISO-like dates
        pattern = r"(x-coredata://[^,]+), ([^,]+), (.*?), ([^,]+), (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}), (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
        match = re.search(pattern, result, re.DOTALL)

        if not match:
            return None

        note_id, name, body, folder, created_str, modified_str = match.groups()
        return AppleNote(
            id=note_id.strip(),
            name=name.strip(),
            body_html=body.strip(),
            folder=folder.strip(),
            created_at=self._parse_date(created_str),
            modified_at=self._parse_date(modified_str),
        )

    def _parse_date(self, date_str: str) -> datetime:
        """Parse Date string from AppleScript (Now ISO-like format)"""
        # Format: "YYYY-MM-DD HH:MM:SS" (generated by our AppleScript helper)
        date_str = date_str.strip()

        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Fallback just in case
            logger.warning(f"Date parse failed for '{date_str}', using now()")
            return datetime.now()


def get_apple_notes_client() -> AppleNotesClient:
    """Get an instance of the Apple Notes client"""
    return AppleNotesClient()
