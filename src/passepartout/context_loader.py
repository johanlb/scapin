"""
Context Loader for Dynamic Briefing.

Responsible for loading, caching, and formatting "Global Context" files
(Profile, Projects, Goals) to be injected into AI prompts.
"""

from pathlib import Path
from typing import Dict, List, Optional

from src.core.config_manager import get_config
from src.monitoring.logger import get_logger

logger = get_logger("passepartout.context_loader")


class ContextLoader:
    """
    Loads and manages the Global Context for AI analysis.

    It reads specific markdown files (Briefing Roots), caches them in memory,
    and returns a formatted string suitable for system prompts.
    """

    # Files to look for in the briefing directory
    BRIEFING_FILES = ["Profile.md", "Projects.md", "Goals.md", "Preferences.md"]

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
        self._cache: Dict[str, Dict] = {}

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

        for filename in self.BRIEFING_FILES:
            content = self._read_file_cached(filename)
            if content:
                # Add a header for the section
                section_name = filename.replace(".md", "").upper()
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

    def get_loaded_files(self) -> List[str]:
        """Return list of currently loaded context files."""
        return [k for k in self._cache.keys()]
