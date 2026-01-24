"""
Context Loader for Dynamic Briefing.

Responsible for loading, caching, and formatting "Global Context" files
(Profile, Projects, Goals) to be injected into AI prompts.
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
# BRIEFING STATUS STRUCTURES (v3.2)
# ============================================================================

# Seuils de contenu substantiel
MIN_CHARS_SUBSTANTIAL = 100  # Minimum 100 caractères
MIN_LINES_SUBSTANTIAL = 5  # Minimum 5 lignes

# Fichiers obligatoires pour un briefing complet
REQUIRED_FILES = ["Profile", "Projects", "Goals"]


class BriefingFileStatus(str, Enum):
    """Statut d'un fichier de briefing individuel."""

    PRESENT = "present"  # Fichier existe avec contenu substantiel (≥100 chars, ≥5 lignes)
    PARTIAL = "partial"  # Fichier existe mais contenu insuffisant
    EMPTY = "empty"  # Fichier existe mais vide
    MISSING = "missing"  # Fichier n'existe pas


class BriefingCompleteness(str, Enum):
    """Niveau de complétude global du briefing."""

    COMPLETE = "complete"  # Tous les fichiers obligatoires sont PRESENT
    PARTIAL = "partial"  # Au moins un fichier obligatoire est PARTIAL/EMPTY
    INCOMPLETE = "incomplete"  # Au moins un fichier obligatoire est MISSING


@dataclass
class BriefingFileInfo:
    """Information sur un fichier de briefing individuel."""

    name: str
    status: BriefingFileStatus
    char_count: int = 0
    line_count: int = 0
    required: bool = True
    loaded_from: Optional[str] = None


@dataclass
class BriefingStatus:
    """Statut global du briefing avec détails par fichier."""

    completeness: BriefingCompleteness
    files: list[BriefingFileInfo] = field(default_factory=list)
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
    Loads and manages the Global Context for AI analysis.

    It reads specific markdown files (Briefing Roots), caches them in memory,
    and returns a formatted string suitable for system prompts.
    """

    # Files to look for in the briefing directory
    # Support both standard names and Apple Notes sync names (with -AppleNotes suffix)
    BRIEFING_FILES = [
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

        # Determine where briefing files live.
        # We look in a 'Briefing' subdirectory, or root if preferred.
        # Strategy: explicit 'Briefing' folder is cleaner.
        self.briefing_dir = self.notes_dir / "Briefing"

        # Cache structure: {filename: {'content': str, 'mtime': float}}
        self._cache: dict[str, dict] = {}

    def load_context(self) -> str:
        """
        Load and concatenate all valid briefing files.

        Returns:
            A single string containing the formatted context.
        """
        if not self.briefing_dir.exists():
            logger.debug(f"Briefing directory not found at {self.briefing_dir}")
            return ""

        context_parts = []

        for file_options in self.BRIEFING_FILES:
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
        file_path = self.briefing_dir / filename

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
            logger.error(f"Failed to read briefing file {filename}: {e}")
            return None

    def get_loaded_files(self) -> list[str]:
        """Return list of currently loaded context files."""
        return list(self._cache)

    def load_context_with_status(self) -> tuple[str, BriefingStatus]:
        """
        Load the briefing context and return both content and status.

        Returns:
            Tuple of (content string, BriefingStatus with file details)
        """
        file_infos: list[BriefingFileInfo] = []
        context_parts: list[str] = []
        total_chars = 0
        files_present = 0
        files_missing = 0
        files_partial = 0

        if not self.briefing_dir.exists():
            logger.debug(f"Briefing directory not found at {self.briefing_dir}")
            # All files are missing
            for file_options in self.BRIEFING_FILES:
                primary, _ = file_options
                name = primary.replace(".md", "")
                is_required = name in REQUIRED_FILES
                file_infos.append(
                    BriefingFileInfo(
                        name=name,
                        status=BriefingFileStatus.MISSING,
                        required=is_required,
                    )
                )
                if is_required:
                    files_missing += 1

            return "", BriefingStatus(
                completeness=BriefingCompleteness.INCOMPLETE,
                files=file_infos,
                total_chars=0,
                files_present=0,
                files_missing=files_missing,
                files_partial=0,
                loaded_at=datetime.now(timezone.utc).isoformat(),
            )

        for file_options in self.BRIEFING_FILES:
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
                status = BriefingFileStatus.MISSING
                char_count = 0
                line_count = 0
                if is_required:
                    files_missing += 1
            elif len(content.strip()) == 0:
                # File exists but empty
                status = BriefingFileStatus.EMPTY
                char_count = 0
                line_count = 0
                if is_required:
                    files_partial += 1
            else:
                char_count = len(content)
                line_count = len(content.strip().split("\n"))

                if char_count >= MIN_CHARS_SUBSTANTIAL and line_count >= MIN_LINES_SUBSTANTIAL:
                    status = BriefingFileStatus.PRESENT
                    files_present += 1
                    total_chars += char_count
                    # Add to context
                    section_name = name.upper()
                    context_parts.append(f"--- {section_name} ---")
                    context_parts.append(content)
                    context_parts.append("")
                else:
                    status = BriefingFileStatus.PARTIAL
                    if is_required:
                        files_partial += 1
                    total_chars += char_count
                    # Still add to context even if partial
                    section_name = name.upper()
                    context_parts.append(f"--- {section_name} ---")
                    context_parts.append(content)
                    context_parts.append("")

            file_infos.append(
                BriefingFileInfo(
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
        if all(f.status == BriefingFileStatus.PRESENT for f in required_files_status):
            completeness = BriefingCompleteness.COMPLETE
        elif any(f.status == BriefingFileStatus.MISSING for f in required_files_status):
            completeness = BriefingCompleteness.INCOMPLETE
        else:
            completeness = BriefingCompleteness.PARTIAL

        context_str = "\n".join(context_parts).strip()
        status = BriefingStatus(
            completeness=completeness,
            files=file_infos,
            total_chars=total_chars,
            files_present=files_present,
            files_missing=files_missing,
            files_partial=files_partial,
            loaded_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            f"Briefing loaded: {completeness.value}, "
            f"{files_present} present, {files_missing} missing, {files_partial} partial, "
            f"{total_chars} chars total"
        )

        return context_str, status
