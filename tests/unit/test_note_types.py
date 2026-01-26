"""Tests for note types module"""

import pytest

from src.passepartout.note_types import (
    DEFAULT_CONSERVATION_CRITERIA,
    NOTE_TYPE_CONFIGS,
    ConservationCriteria,
    ImportanceLevel,
    NoteType,
    ReviewConfig,
    detect_note_type_from_path,
    get_review_config,
)


class TestNoteType:
    """Tests for NoteType enum"""

    def test_all_types_exist(self):
        """All expected types should exist"""
        expected = [
            "CONCEPT",
            "ENTITE",
            "EVENEMENT",
            "PERSONNE",
            "PROCESSUS",
            "PROJET",
            "REUNION",
            "SOUVENIR",
            "AUTRE",
        ]
        for name in expected:
            assert hasattr(NoteType, name)

    def test_from_folder_standard_names(self):
        """Standard folder names should map correctly"""
        assert NoteType.from_folder("Concepts") == NoteType.CONCEPT
        assert NoteType.from_folder("Personnes") == NoteType.PERSONNE
        assert NoteType.from_folder("Projets") == NoteType.PROJET
        assert NoteType.from_folder("Réunions") == NoteType.REUNION
        assert NoteType.from_folder("Entités") == NoteType.ENTITE

    def test_from_folder_case_insensitive(self):
        """Folder matching should be case insensitive"""
        assert NoteType.from_folder("PERSONNES") == NoteType.PERSONNE
        assert NoteType.from_folder("projets") == NoteType.PROJET

    def test_from_folder_unknown(self):
        """Unknown folders should return AUTRE"""
        assert NoteType.from_folder("Unknown") == NoteType.AUTRE
        assert NoteType.from_folder("Random") == NoteType.AUTRE

    def test_folder_name_property(self):
        """Each type should have a folder name"""
        assert NoteType.CONCEPT.folder_name == "Concepts"
        assert NoteType.PERSONNE.folder_name == "Personnes"
        assert NoteType.PROJET.folder_name == "Projets"
        assert NoteType.AUTRE.folder_name == "Notes"


class TestImportanceLevel:
    """Tests for ImportanceLevel enum"""

    def test_all_levels_exist(self):
        """All expected levels should exist"""
        expected = ["CRITICAL", "HIGH", "NORMAL", "LOW", "ARCHIVE"]
        for name in expected:
            assert hasattr(ImportanceLevel, name)

    def test_string_values(self):
        """Enum values should be strings"""
        assert ImportanceLevel.CRITICAL.value == "critical"
        assert ImportanceLevel.ARCHIVE.value == "archive"


class TestReviewConfig:
    """Tests for ReviewConfig dataclass"""

    def test_default_values(self):
        """Default config should have sensible values"""
        config = ReviewConfig()
        assert config.base_interval_hours == 2.0
        assert config.max_interval_days == 90
        assert config.easiness_factor == 2.5
        assert config.auto_enrich is True
        assert config.web_search_default is False
        assert config.skip_revision is False

    def test_frozen(self):
        """Config should be frozen (immutable)"""
        config = ReviewConfig()
        with pytest.raises(AttributeError):
            config.base_interval_hours = 5.0


class TestNoteTypeConfigs:
    """Tests for NOTE_TYPE_CONFIGS dictionary"""

    def test_all_types_have_config(self):
        """Every NoteType should have a config"""
        for note_type in NoteType:
            assert note_type in NOTE_TYPE_CONFIGS

    def test_souvenir_skips_revision(self):
        """Souvenir type should skip revision"""
        config = NOTE_TYPE_CONFIGS[NoteType.SOUVENIR]
        assert config.skip_revision is True
        assert config.auto_enrich is False

    def test_projet_frequent_revision(self):
        """Projet type should have frequent revision"""
        config = NOTE_TYPE_CONFIGS[NoteType.PROJET]
        assert config.base_interval_hours == 2.0
        assert config.max_interval_days == 14

    def test_personne_no_web_search_default(self):
        """Personne type should not have web search by default"""
        config = NOTE_TYPE_CONFIGS[NoteType.PERSONNE]
        assert config.web_search_default is False

    def test_concept_moderate_revision(self):
        """Concept type should have moderate revision"""
        config = NOTE_TYPE_CONFIGS[NoteType.CONCEPT]
        assert config.base_interval_hours == 48.0
        assert config.auto_enrich is True


class TestGetReviewConfig:
    """Tests for get_review_config function"""

    def test_returns_config_for_known_type(self):
        """Should return correct config for known types"""
        config = get_review_config(NoteType.PERSONNE)
        assert config == NOTE_TYPE_CONFIGS[NoteType.PERSONNE]

    def test_returns_autre_for_unknown(self):
        """Should fall back to AUTRE config"""
        config = get_review_config(NoteType.AUTRE)
        assert config == NOTE_TYPE_CONFIGS[NoteType.AUTRE]


class TestDetectNoteTypeFromPath:
    """Tests for detect_note_type_from_path function"""

    def test_detect_from_full_path(self):
        """Should detect type from full path"""
        path = "/Users/johan/Notes/Personnes/Jean.md"
        assert detect_note_type_from_path(path) == NoteType.PERSONNE

    def test_detect_from_relative_path(self):
        """Should detect type from relative path"""
        path = "Projets/Alpha/notes.md"
        assert detect_note_type_from_path(path) == NoteType.PROJET

    def test_detect_unknown_path(self):
        """Should return AUTRE for unknown paths"""
        path = "/Users/johan/Random/file.md"
        assert detect_note_type_from_path(path) == NoteType.AUTRE

    def test_windows_path(self):
        """Should handle Windows-style paths"""
        path = "C:\\Notes\\Réunions\\meeting.md"
        assert detect_note_type_from_path(path) == NoteType.REUNION


class TestConservationCriteria:
    """Tests for ConservationCriteria dataclass"""

    def test_default_values(self):
        """Default criteria should have sensible values"""
        criteria = ConservationCriteria()
        assert criteria.obsolete_meeting_days == 30
        assert criteria.completed_minor_action_days == 14
        assert criteria.min_confidence_auto_archive == 0.95

    def test_keep_patterns(self):
        """Should have default keep patterns"""
        criteria = ConservationCriteria()
        assert len(criteria.keep_patterns) > 0
        # Check some expected patterns
        assert any("contact" in p.lower() for p in criteria.keep_patterns)

    def test_default_instance(self):
        """DEFAULT_CONSERVATION_CRITERIA should exist"""
        assert DEFAULT_CONSERVATION_CRITERIA is not None
        assert isinstance(DEFAULT_CONSERVATION_CRITERIA, ConservationCriteria)
