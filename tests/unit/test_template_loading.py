"""
Tests for Template Loading in RetoucheReviewer

Tests the _load_template_for_type method that loads template structures
from "Modèle — Fiche X" notes in PKM/Modèles/.
"""

from pathlib import Path
from unittest.mock import MagicMock

from src.passepartout.retouche_reviewer import (
    TEMPLATE_FOLDER,
    TEMPLATE_TYPE_MAP,
    RetoucheReviewer,
)


class TestLoadTemplateForType:
    """Tests for _load_template_for_type method."""

    def _create_reviewer_with_notes_dir(self, notes_dir: Path) -> RetoucheReviewer:
        """Create a RetoucheReviewer with mocked dependencies."""
        mock_note_manager = MagicMock()
        mock_note_manager.notes_dir = notes_dir
        mock_metadata_store = MagicMock()
        mock_scheduler = MagicMock()

        return RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=mock_metadata_store,
            scheduler=mock_scheduler,
            ai_router=None,
        )

    def test_returns_none_for_unknown_type(self, tmp_path: Path) -> None:
        """Returns None for unknown note types."""
        reviewer = self._create_reviewer_with_notes_dir(tmp_path)

        result = reviewer._load_template_for_type("unknown_type")

        assert result is None

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        """Returns None when template file doesn't exist."""
        reviewer = self._create_reviewer_with_notes_dir(tmp_path)

        result = reviewer._load_template_for_type("personne")

        assert result is None

    def test_extracts_content_between_markers(self, tmp_path: Path) -> None:
        """Extracts content between DÉBUT and FIN MODÈLE markers."""
        # Create template directory
        template_dir = tmp_path / TEMPLATE_FOLDER
        template_dir.mkdir(parents=True)

        # Create template file with markers
        template_file = template_dir / TEMPLATE_TYPE_MAP["personne"]
        template_content = """---
title: Modèle — Fiche Personne
---

Some intro text

━━━ DÉBUT MODÈLE ━━━

name: [Prénom Nom]

👤 COORDONNÉES

Nom : [Prénom Nom]
Email : [email]

🤝 RELATION

Type : [Client / Ami]

━━━ FIN MODÈLE ━━━

Some footer text
"""
        template_file.write_text(template_content, encoding="utf-8")

        reviewer = self._create_reviewer_with_notes_dir(tmp_path)

        result = reviewer._load_template_for_type("personne")

        assert result is not None
        assert "name: [Prénom Nom]" in result
        assert "👤 COORDONNÉES" in result
        assert "🤝 RELATION" in result
        # Markers themselves should not be in the result
        assert "DÉBUT MODÈLE" not in result
        assert "FIN MODÈLE" not in result
        # Content outside markers should not be included
        assert "Some intro text" not in result
        assert "Some footer text" not in result

    def test_returns_full_content_without_markers(self, tmp_path: Path) -> None:
        """Returns full content (minus frontmatter) if no markers present."""
        template_dir = tmp_path / TEMPLATE_FOLDER
        template_dir.mkdir(parents=True)

        template_file = template_dir / TEMPLATE_TYPE_MAP["projet"]
        template_content = """---
title: Modèle — Fiche Projet
---

This is the project template
With some structure
"""
        template_file.write_text(template_content, encoding="utf-8")

        reviewer = self._create_reviewer_with_notes_dir(tmp_path)

        result = reviewer._load_template_for_type("projet")

        assert result is not None
        assert "This is the project template" in result
        # Frontmatter should be stripped
        assert "title: Modèle" not in result

    def test_handles_all_mapped_types(self, tmp_path: Path) -> None:
        """All types in TEMPLATE_TYPE_MAP can be loaded."""
        template_dir = tmp_path / TEMPLATE_FOLDER
        template_dir.mkdir(parents=True)

        # Create all template files
        for note_type, filename in TEMPLATE_TYPE_MAP.items():
            template_file = template_dir / filename
            template_file.write_text(
                f"""---
title: {filename}
---

━━━ DÉBUT MODÈLE ━━━

Template for {note_type}

━━━ FIN MODÈLE ━━━
""",
                encoding="utf-8",
            )

        reviewer = self._create_reviewer_with_notes_dir(tmp_path)

        for note_type in TEMPLATE_TYPE_MAP:
            result = reviewer._load_template_for_type(note_type)
            assert result is not None, f"Failed for type: {note_type}"
            assert f"Template for {note_type}" in result

    def test_case_insensitive_type_matching(self, tmp_path: Path) -> None:
        """Type matching is case-insensitive."""
        template_dir = tmp_path / TEMPLATE_FOLDER
        template_dir.mkdir(parents=True)

        template_file = template_dir / TEMPLATE_TYPE_MAP["personne"]
        template_file.write_text(
            """━━━ DÉBUT MODÈLE ━━━
Test content
━━━ FIN MODÈLE ━━━""",
            encoding="utf-8",
        )

        reviewer = self._create_reviewer_with_notes_dir(tmp_path)

        # Test various case variations
        assert reviewer._load_template_for_type("personne") is not None
        assert reviewer._load_template_for_type("PERSONNE") is not None
        assert reviewer._load_template_for_type("Personne") is not None
