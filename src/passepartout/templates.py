"""
Template Manager Service

Handles loading and instantiating note templates.
Ensures notes are created with the correct "Molecular" structure (Sections).
"""

from pathlib import Path
from typing import Dict, Optional

from src.monitoring.logger import get_logger

logger = get_logger("passepartout.templates")


class TemplateManager:
    """
    Manages note templates.
    """

    # Mapping from 'type' (used in create_note) to Template Filename
    TEMPLATE_MAP = {
        "personne": "personne.md",
        "projet": "projet.md",
        "project": "projet.md",
        "entite": "entite.md",
        "entity": "entite.md",
        "reunion": "reunion.md",
        "meeting": "reunion.md",
        "evenement": "evenement.md",
        "event": "evenement.md",
    }

    # Source mapping for ingestion (Existing User Notes -> System Templates)
    INGEST_MAP = {
        "Modèle — Fiche Personne.md": "personne.md",
        "Modèle — Fiche Projet.md": "projet.md",
        "Modèle — Fiche Entité.md": "entite.md",
        "Modèle — Fiche Réunion.md": "reunion.md",
        "Modèle — Fiche Événement.md": "evenement.md",
    }

    def __init__(self, templates_dir: Path):
        self.templates_dir = Path(templates_dir)
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True)

    def get_template(self, template_type: str) -> Optional[str]:
        """
        Get the content of a template by type.
        """
        filename = self.TEMPLATE_MAP.get(template_type.lower())
        if not filename:
            return None

        template_path = self.templates_dir / filename
        if not template_path.exists():
            logger.warning(f"Template file not found: {template_path}")
            return None

        try:
            return template_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading template {filename}: {e}")
            return None

    def ingest_from_directory(self, source_dir: Path) -> Dict[str, str]:
        """
        Ingest templates from a user directory (e.g. Processus).
        Copies them to the system templates directory with standard names.
        """
        stats = {"found": 0, "copied": 0, "errors": 0}
        source_dir = Path(source_dir)

        if not source_dir.exists():
            logger.warning(f"Source directory for ingestion not found: {source_dir}")
            return stats

        for source_name, target_name in self.INGEST_MAP.items():
            source_file = source_dir / source_name
            if source_file.exists():
                stats["found"] += 1
                target_file = self.templates_dir / target_name
                try:
                    # Copy and normalize content if needed (optional)
                    # For now, exact copy
                    content = source_file.read_text(encoding="utf-8")

                    # Optional: Strip specific user metadata (like apple_id) if we want "Clean" templates
                    # But the user logic handles frontmatter separately usually.

                    target_file.write_text(content, encoding="utf-8")
                    stats["copied"] += 1
                    logger.info(f"Ingested template: {source_name} -> {target_name}")
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Failed to copy {source_name}: {e}")
            else:
                logger.debug(f"Source template not found: {source_name}")

        return stats
