"""
Context Loader for Canevas (Dynamic Context).

Responsible for loading, caching, and formatting "Canevas" files
(Profile, Projects, Goals, Preferences) to be injected into AI prompts.

The Canevas is Johan's permanent context - the scenario that guides
the AI valets' improvisation, like in Commedia dell'arte.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.core.config_manager import get_config
from src.monitoring.logger import get_logger

logger = get_logger("passepartout.context_loader")

# ============================================================================
# CANEVAS STATUS STRUCTURES (v3.2)
# ============================================================================

# Seuils de contenu substantiel
MIN_CHARS_SUBSTANTIAL = 100  # Minimum 100 caractères
MIN_LINES_SUBSTANTIAL = 5  # Minimum 5 lignes

# Fichiers obligatoires pour un canevas complet
REQUIRED_FILES = ["Profile", "Projects", "Goals"]


class CanevasFileStatus(str, Enum):
    """Statut d'un fichier de canevas individuel."""

    PRESENT = "present"  # Fichier existe avec contenu substantiel (≥100 chars, ≥5 lignes)
    PARTIAL = "partial"  # Fichier existe mais contenu insuffisant
    EMPTY = "empty"  # Fichier existe mais vide
    MISSING = "missing"  # Fichier n'existe pas


class CanevasCompleteness(str, Enum):
    """Niveau de complétude global du canevas."""

    COMPLETE = "complete"  # Tous les fichiers obligatoires sont PRESENT
    PARTIAL = "partial"  # Au moins un fichier obligatoire est PARTIAL/EMPTY
    INCOMPLETE = "incomplete"  # Au moins un fichier obligatoire est MISSING


@dataclass
class CanevasFileInfo:
    """Information sur un fichier de canevas individuel."""

    name: str
    status: CanevasFileStatus
    char_count: int = 0
    line_count: int = 0
    required: bool = True
    loaded_from: Optional[str] = None


@dataclass
class CanevasStatus:
    """Statut global du canevas avec détails par fichier."""

    completeness: CanevasCompleteness
    files: list[CanevasFileInfo] = field(default_factory=list)
    total_chars: int = 0
    files_present: int = 0
    files_missing: int = 0
    files_partial: int = 0
    loaded_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convertir en dictionnaire pour sérialisation JSON."""
        return {
            "completeness": self.completeness.value,
            "files": [
                {
                    "name": f.name,
                    "status": f.status.value,
                    "char_count": f.char_count,
                    "line_count": f.line_count,
                    "required": f.required,
                    "loaded_from": f.loaded_from,
                }
                for f in self.files
            ],
            "total_chars": self.total_chars,
            "files_present": self.files_present,
            "files_missing": self.files_missing,
            "files_partial": self.files_partial,
            "loaded_at": self.loaded_at,
        }


class ContextLoader:
    """
    Loads and manages the Canevas (Global Context) for AI analysis.

    It reads specific markdown files (Canevas files), caches them in memory,
    and returns a formatted string suitable for system prompts.

    The Canevas is the permanent context that guides the AI valets,
    like the scenario in Commedia dell'arte.
    """

    # Files to look for in the canevas directory
    # Support both standard names and Apple Notes sync names (with -AppleNotes suffix)
    CANEVAS_FILES = [
        ("Profile.md", "Profile-AppleNotes.md"),
        ("Projects.md", "Projects-AppleNotes.md"),
        ("Goals.md", "Goals-AppleNotes.md"),
        ("Preferences.md", "Preferences-AppleNotes.md"),
    ]

    def __init__(self, notes_dir: Optional[Path] = None):
        """
        Initialize ContextLoader.

        Args:
            notes_dir: Root directory of notes. If None, loaded from config.
        """
        if notes_dir:
            self.notes_dir = notes_dir
        else:
            config = get_config()
            self.notes_dir = config.storage.notes_dir

        # Determine where canevas files live.
        # The Canevas folder contains permanent user context (profile, goals, projects).
        self.canevas_dir = self.notes_dir / "Canevas"

        # Cache structure: {filename: {'content': str, 'mtime': float}}
        self._cache: dict[str, dict] = {}

    def load_context(self) -> str:
        """
        Load and concatenate all valid canevas files.

        Returns:
            A single string containing the formatted context.
        """
        if not self.canevas_dir.exists():
            logger.debug(f"Canevas directory not found at {self.canevas_dir}")
            return ""

        context_parts = []

        for file_options in self.CANEVAS_FILES:
            # Each entry is a tuple of (primary_name, alternative_name)
            primary, alternative = file_options
            content = self._read_file_cached(primary)
            if not content:
                content = self._read_file_cached(alternative)
            if content:
                # Add a header for the section (use primary name for consistency)
                section_name = primary.replace(".md", "").upper()
                context_parts.append(f"--- {section_name} ---")
                context_parts.append(content)
                context_parts.append("")  # Spacing

        return "\n".join(context_parts).strip()

    def _read_file_cached(self, filename: str) -> Optional[str]:
        """Read a file with simple mtime caching."""
        file_path = self.canevas_dir / filename

        if not file_path.exists():
            return None

        try:
            stat = file_path.stat()
            mtime = stat.st_mtime

            # Check cache
            if filename in self._cache:
                cached = self._cache[filename]
                if cached["mtime"] == mtime:
                    return cached["content"]

            # Read fresh
            content = file_path.read_text(encoding="utf-8").strip()

            # Update cache
            self._cache[filename] = {"content": content, "mtime": mtime}
            logger.debug(f"Loaded fresh context from {filename}")
            return content

        except Exception as e:
            logger.error(f"Failed to read canevas file {filename}: {e}")
            return None

    def get_loaded_files(self) -> list[str]:
        """Return list of currently loaded context files."""
        return list(self._cache)

    def load_context_with_status(self) -> tuple[str, CanevasStatus]:
        """
        Load the canevas context and return both content and status.

        Returns:
            Tuple of (content string, CanevasStatus with file details)
        """
        file_infos: list[CanevasFileInfo] = []
        context_parts: list[str] = []
        total_chars = 0
        files_present = 0
        files_missing = 0
        files_partial = 0

        if not self.canevas_dir.exists():
            logger.debug(f"Canevas directory not found at {self.canevas_dir}")
            # All files are missing
            for file_options in self.CANEVAS_FILES:
                primary, _ = file_options
                name = primary.replace(".md", "")
                is_required = name in REQUIRED_FILES
                file_infos.append(
                    CanevasFileInfo(
                        name=name,
                        status=CanevasFileStatus.MISSING,
                        required=is_required,
                    )
                )
                if is_required:
                    files_missing += 1

            return "", CanevasStatus(
                completeness=CanevasCompleteness.INCOMPLETE,
                files=file_infos,
                total_chars=0,
                files_present=0,
                files_missing=files_missing,
                files_partial=0,
                loaded_at=datetime.now(timezone.utc).isoformat(),
            )

        for file_options in self.CANEVAS_FILES:
            primary, alternative = file_options
            name = primary.replace(".md", "")
            is_required = name in REQUIRED_FILES

            # Try primary, then alternative
            content = self._read_file_cached(primary)
            loaded_from = primary if content else None
            if not content:
                content = self._read_file_cached(alternative)
                loaded_from = alternative if content else None

            # Determine file status
            if content is None:
                # File doesn't exist
                status = CanevasFileStatus.MISSING
                char_count = 0
                line_count = 0
                if is_required:
                    files_missing += 1
            elif len(content.strip()) == 0:
                # File exists but empty
                status = CanevasFileStatus.EMPTY
                char_count = 0
                line_count = 0
                if is_required:
                    files_partial += 1
            else:
                char_count = len(content)
                line_count = len(content.strip().split("\n"))

                if char_count >= MIN_CHARS_SUBSTANTIAL and line_count >= MIN_LINES_SUBSTANTIAL:
                    status = CanevasFileStatus.PRESENT
                    files_present += 1
                    total_chars += char_count
                    # Add to context
                    section_name = name.upper()
                    context_parts.append(f"--- {section_name} ---")
                    context_parts.append(content)
                    context_parts.append("")
                else:
                    status = CanevasFileStatus.PARTIAL
                    if is_required:
                        files_partial += 1
                    total_chars += char_count
                    # Still add to context even if partial
                    section_name = name.upper()
                    context_parts.append(f"--- {section_name} ---")
                    context_parts.append(content)
                    context_parts.append("")

            file_infos.append(
                CanevasFileInfo(
                    name=name,
                    status=status,
                    char_count=char_count,
                    line_count=line_count,
                    required=is_required,
                    loaded_from=loaded_from,
                )
            )

        # Determine overall completeness based on required files
        required_files_status = [f for f in file_infos if f.required]
        if all(f.status == CanevasFileStatus.PRESENT for f in required_files_status):
            completeness = CanevasCompleteness.COMPLETE
        elif any(f.status == CanevasFileStatus.MISSING for f in required_files_status):
            completeness = CanevasCompleteness.INCOMPLETE
        else:
            completeness = CanevasCompleteness.PARTIAL

        context_str = "\n".join(context_parts).strip()
        status = CanevasStatus(
            completeness=completeness,
            files=file_infos,
            total_chars=total_chars,
            files_present=files_present,
            files_missing=files_missing,
            files_partial=files_partial,
            loaded_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            f"Canevas loaded: {completeness.value}, "
            f"{files_present} present, {files_missing} missing, {files_partial} partial, "
            f"{total_chars} chars total"
        )

        return context_str, status
