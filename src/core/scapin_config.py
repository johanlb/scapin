"""
Scapin Configuration Reader

Reads user configuration from the _Scapin/Configuration.md note.
This allows users to configure entity resolution rules without code changes.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScapinUserConfig:
    """User configuration loaded from _Scapin/Configuration.md"""

    my_entities: list[str] = field(default_factory=list)
    """Companies owned by the user - contacts from these get individual person notes"""

    vip_contacts: list[str] = field(default_factory=list)
    """External contacts important enough to have their own person note"""

    config_path: Path | None = None
    """Path to the configuration file if loaded"""


class ScapinConfigReader:
    """
    Reads and parses the Scapin configuration note.

    The configuration note is expected at: {notes_dir}/_Scapin/Configuration.md

    Format:
    ```markdown
    ## Mes entités
    - Eufonie
    - Eufonie Care

    ## Entités VIP
    - Jean Dupont
    ```
    """

    CONFIG_FILENAME = "_Scapin/Configuration.md"

    def __init__(self, notes_dir: str | Path):
        self.notes_dir = Path(notes_dir)
        self.config_path = self.notes_dir / self.CONFIG_FILENAME
        self._config: ScapinUserConfig | None = None

    def load(self) -> ScapinUserConfig:
        """
        Load configuration from the note file.

        Returns cached config if already loaded.
        """
        if self._config is not None:
            return self._config

        self._config = ScapinUserConfig()

        if not self.config_path.exists():
            logger.warning(
                f"Scapin configuration not found at {self.config_path}. "
                "Using defaults. Create _Scapin/Configuration.md to customize."
            )
            return self._config

        try:
            content = self.config_path.read_text(encoding="utf-8")
            self._config = self._parse_config(content)
            self._config.config_path = self.config_path

            logger.info(
                "Loaded Scapin configuration",
                extra={
                    "my_entities": len(self._config.my_entities),
                    "vip_contacts": len(self._config.vip_contacts),
                    "path": str(self.config_path),
                },
            )

        except Exception as e:
            logger.error(f"Failed to parse Scapin configuration: {e}")
            self._config = ScapinUserConfig()

        return self._config

    def reload(self) -> ScapinUserConfig:
        """Force reload configuration from disk."""
        self._config = None
        return self.load()

    def _parse_config(self, content: str) -> ScapinUserConfig:
        """Parse the markdown configuration content."""
        config = ScapinUserConfig()

        # Find "Mes entités" section
        my_entities_match = re.search(
            r"##\s*Mes entités\s*\n(.*?)(?=\n##|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if my_entities_match:
            config.my_entities = self._extract_list_items(my_entities_match.group(1))

        # Find "Entités VIP" section
        vip_match = re.search(
            r"##\s*Entités VIP\s*\n(.*?)(?=\n##|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if vip_match:
            config.vip_contacts = self._extract_list_items(vip_match.group(1))

        return config

    def _extract_list_items(self, section: str) -> list[str]:
        """Extract list items from a markdown section."""
        items = []
        for line in section.split("\n"):
            line = line.strip()
            # Match "- Item" or "* Item"
            match = re.match(r"^[-*]\s+(.+)$", line)
            if match:
                item = match.group(1).strip()
                # Skip comments and empty items
                if item and not item.startswith("<!--"):
                    # Remove inline comments
                    item = re.sub(r"\s*<!--.*?-->", "", item).strip()
                    if item:
                        items.append(item)
        return items

    def is_my_entity(self, entity_name: str) -> bool:
        """
        Check if an entity belongs to the user.

        Args:
            entity_name: Name of the entity to check

        Returns:
            True if this is one of the user's own companies
        """
        config = self.load()
        entity_lower = entity_name.lower()
        return any(e.lower() in entity_lower or entity_lower in e.lower()
                   for e in config.my_entities)

    def is_vip_contact(self, contact_name: str) -> bool:
        """
        Check if a contact is marked as VIP.

        Args:
            contact_name: Name of the contact to check

        Returns:
            True if this contact should have their own note
        """
        config = self.load()
        contact_lower = contact_name.lower()
        return any(v.lower() in contact_lower or contact_lower in v.lower()
                   for v in config.vip_contacts)

    def should_create_person_note(self, person_name: str, company_name: str | None) -> bool:
        """
        Determine if a person should have their own note vs enriching company note.

        Rules:
        1. If person is from one of my entities → person note
        2. If person is a VIP contact → person note
        3. Otherwise → enrich company note

        Args:
            person_name: Name of the person
            company_name: Company they represent (if any)

        Returns:
            True if person should have their own note
        """
        # VIP contacts always get their own note
        if self.is_vip_contact(person_name):
            return True

        # People from my companies get their own note
        if company_name and self.is_my_entity(company_name):
            return True

        # External contacts → company note
        return False


# Singleton instance
_config_reader: ScapinConfigReader | None = None


def get_scapin_config(notes_dir: str | Path | None = None) -> ScapinConfigReader:
    """
    Get the singleton ScapinConfigReader instance.

    Args:
        notes_dir: Notes directory path. Required on first call.

    Returns:
        ScapinConfigReader instance
    """
    global _config_reader

    if _config_reader is None:
        if notes_dir is None:
            # Try to get from environment/config
            from src.core.config_manager import get_config
            config = get_config()
            notes_dir = config.storage.notes_path

        _config_reader = ScapinConfigReader(notes_dir)

    return _config_reader


def reload_scapin_config() -> ScapinUserConfig:
    """Force reload the Scapin configuration from disk."""
    if _config_reader is not None:
        return _config_reader.reload()
    return get_scapin_config().load()
