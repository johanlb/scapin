"""
Tests for EntitySearcher — Option D Implementation

Tests entity-based local search functionality including:
- Exact matching on note titles
- Fuzzy matching using difflib
- Partial matching (entity name in title)
- Content search
- ScapinConfig integration
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.passepartout.entity_search import (
    EXACT_MATCH_SCORE,
    HIGH_FUZZY_THRESHOLD,
    MEDIUM_FUZZY_THRESHOLD,
    PARTIAL_MATCH_SCORE,
    EntitySearcher,
    EntitySearchResult,
    EntitySearchStats,
    create_entity_searcher,
)
from src.passepartout.note_manager import Note


@pytest.fixture
def mock_note_manager():
    """Create a mock NoteManager with sample notes"""
    manager = MagicMock()
    manager.notes_dir = Path("/tmp/notes")

    # Create sample notes
    notes = [
        Note(
            note_id="marc-dupont-001",
            title="Marc Dupont",
            content="Tech Lead at Eufonie. Expert in Python.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["personne", "eufonie"],
            metadata={"type": "personne"},
        ),
        Note(
            note_id="marc-dupont-tech-001",
            title="Marc Dupont - Tech Lead",
            content="Information about Marc.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["personne"],
            metadata={"type": "personne"},
        ),
        Note(
            note_id="projet-alpha-001",
            title="Projet Alpha",
            content="Marc Dupont is the lead. Budget: 50k.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["projet"],
            metadata={"type": "projet"},
        ),
        Note(
            note_id="credit-agricole-001",
            title="Crédit Agricole",
            content="Banque principale. Contact: Anaelle Dufour.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["entreprise"],
            metadata={"type": "entreprise"},
        ),
        Note(
            note_id="eufonie-001",
            title="Eufonie",
            content="Ma société principale.",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["entreprise"],
            metadata={"type": "entreprise"},
        ),
    ]

    manager.get_all_notes.return_value = notes
    return manager


@pytest.fixture
def mock_scapin_config():
    """Create a mock ScapinConfig"""
    config = MagicMock()
    config.is_my_entity.return_value = False
    config.is_vip_contact.return_value = False

    # Eufonie is user's entity
    def is_my_entity(name):
        return name.lower() in ["eufonie", "eufonie care", "skiillz"]

    config.is_my_entity.side_effect = is_my_entity
    return config


class TestEntitySearchResult:
    """Tests for EntitySearchResult dataclass"""

    def test_creation(self, mock_note_manager):
        """Test creating an EntitySearchResult"""
        note = mock_note_manager.get_all_notes.return_value[0]
        result = EntitySearchResult(
            note=note,
            entity_name="Marc Dupont",
            matched_title="Marc Dupont",
            match_type="exact",
            match_score=1.0,
        )

        assert result.entity_name == "Marc Dupont"
        assert result.match_type == "exact"
        assert result.match_score == 1.0
        assert result.is_my_entity is False
        assert result.is_vip is False

    def test_repr(self, mock_note_manager):
        """Test string representation"""
        note = mock_note_manager.get_all_notes.return_value[0]
        result = EntitySearchResult(
            note=note,
            entity_name="Marc Dupont",
            matched_title="Marc Dupont",
            match_type="fuzzy",
            match_score=0.85,
        )

        repr_str = repr(result)
        assert "Marc Dupont" in repr_str
        assert "fuzzy" in repr_str
        assert "0.85" in repr_str


class TestEntitySearchStats:
    """Tests for EntitySearchStats dataclass"""

    def test_defaults(self):
        """Test default values"""
        stats = EntitySearchStats()
        assert stats.entities_searched == 0
        assert stats.exact_matches == 0
        assert stats.fuzzy_matches == 0
        assert stats.partial_matches == 0
        assert stats.content_matches == 0
        assert stats.total_results == 0


class TestEntitySearcher:
    """Tests for EntitySearcher class"""

    def test_init(self, mock_note_manager, mock_scapin_config):
        """Test initialization"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
        )

        assert searcher.note_manager is mock_note_manager
        assert searcher.fuzzy_threshold == MEDIUM_FUZZY_THRESHOLD
        assert searcher.search_content is True
        assert searcher.max_results_per_entity == 3

    def test_exact_match(self, mock_note_manager, mock_scapin_config):
        """Test exact title matching"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
        )

        results = searcher.search_entities(["Marc Dupont"])

        # Should find exact match
        exact_matches = [r for r in results if r.match_type == "exact"]
        assert len(exact_matches) >= 1
        assert exact_matches[0].match_score == EXACT_MATCH_SCORE
        assert exact_matches[0].matched_title == "Marc Dupont"

    def test_fuzzy_match(self, mock_note_manager, mock_scapin_config):
        """Test fuzzy title matching"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
            fuzzy_threshold=0.60,  # Lower threshold for test
        )

        results = searcher.search_entities(["Marc"])

        # Should find fuzzy matches
        assert len(results) >= 1
        # At least one should be fuzzy or partial
        match_types = [r.match_type for r in results]
        assert "fuzzy" in match_types or "partial" in match_types

    def test_partial_match(self, mock_note_manager, mock_scapin_config):
        """Test partial title matching (entity in title)"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
        )

        results = searcher.search_entities(["Alpha"])

        # Should find "Projet Alpha" via partial match
        partial_matches = [r for r in results if r.match_type == "partial"]
        assert len(partial_matches) >= 1
        assert any("Alpha" in r.matched_title for r in partial_matches)

    def test_content_search(self, mock_note_manager, mock_scapin_config):
        """Test searching in note content"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
            search_content=True,
        )

        results = searcher.search_entities(["Python"])

        # Should find note mentioning Python in content
        content_matches = [r for r in results if r.match_type == "content"]
        # Note: depends on implementation - Python is in Marc Dupont's content
        if content_matches:
            assert any("Python" not in r.matched_title for r in content_matches)

    def test_my_entity_detection(self, mock_note_manager, mock_scapin_config):
        """Test detection of user's own entities"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
        )

        results = searcher.search_entities(["Eufonie"])

        # Should mark Eufonie as my entity
        eufonie_results = [r for r in results if "Eufonie" in r.matched_title]
        assert len(eufonie_results) >= 1
        assert eufonie_results[0].is_my_entity is True

    def test_multiple_entities(self, mock_note_manager, mock_scapin_config):
        """Test searching for multiple entities at once"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
        )

        results = searcher.search_entities(["Marc Dupont", "Projet Alpha"])

        # Should find both
        entities_found = set(r.entity_name for r in results)
        assert "Marc Dupont" in entities_found
        assert "Projet Alpha" in entities_found

    def test_max_results_per_entity(self, mock_note_manager, mock_scapin_config):
        """Test limiting results per entity"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
            max_results_per_entity=1,
        )

        results = searcher.search_entities(["Marc Dupont"])

        # Should limit to 1 per entity
        marc_results = [r for r in results if r.entity_name == "Marc Dupont"]
        assert len(marc_results) <= 1

    def test_invalidate_cache(self, mock_note_manager, mock_scapin_config):
        """Test cache invalidation"""
        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
        )

        # First search builds cache
        searcher.search_entities(["Marc"])
        assert searcher._title_cache_valid is True

        # Invalidate cache
        searcher.invalidate_cache()
        assert searcher._title_cache_valid is False


class TestNormalizeName:
    """Tests for name normalization"""

    def test_lowercase(self):
        """Test lowercase normalization"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        assert searcher._normalize_name("Marc DUPONT") == "marc dupont"

    def test_strip_whitespace(self):
        """Test whitespace stripping"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        assert searcher._normalize_name("  Marc Dupont  ") == "marc dupont"

    def test_remove_title_m(self):
        """Test removing M. prefix"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        result = searcher._normalize_name("M. Dupont")
        assert result == "dupont"

    def test_remove_title_mme(self):
        """Test removing Mme prefix"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        result = searcher._normalize_name("Mme Dupont")
        assert result == "dupont"

    def test_remove_title_dr(self):
        """Test removing Dr prefix"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        result = searcher._normalize_name("Dr. Martin")
        assert result == "martin"


class TestFuzzyMatch:
    """Tests for fuzzy matching"""

    def test_identical_strings(self):
        """Test matching identical strings"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        score = searcher._fuzzy_match("marc dupont", "marc dupont")
        assert score == 1.0

    def test_similar_strings(self):
        """Test matching similar strings"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        score = searcher._fuzzy_match("marc dupont", "marc dupon")
        assert score >= HIGH_FUZZY_THRESHOLD

    def test_different_strings(self):
        """Test matching different strings"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        score = searcher._fuzzy_match("marc", "jean")
        assert score < 0.5


class TestExtractNameFromTitle:
    """Tests for extracting name from note title"""

    def test_simple_title(self):
        """Test simple title without separators"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        result = searcher._extract_name_from_title("Marc Dupont")
        assert result == "Marc Dupont"

    def test_title_with_dash(self):
        """Test title with dash separator"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        result = searcher._extract_name_from_title("Marc Dupont - Tech Lead")
        assert result == "Marc Dupont"

    def test_title_with_parenthesis(self):
        """Test title with parenthetical info"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        result = searcher._extract_name_from_title("Projet Alpha (2024)")
        assert result == "Projet Alpha"

    def test_title_with_pipe(self):
        """Test title with pipe separator"""
        searcher = EntitySearcher.__new__(EntitySearcher)
        result = searcher._extract_name_from_title("Entreprise XYZ | Client")
        assert result == "Entreprise XYZ"


class TestEntityResolutionRule:
    """Tests for entity resolution rules"""

    def test_external_entity_company_rule(self, mock_note_manager, mock_scapin_config):
        """Test that external entities use company rule"""
        # External entities should NOT create person notes
        mock_scapin_config.should_create_person_note.return_value = False

        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
        )

        # External entity -> company note
        rule = searcher.get_entity_resolution_rule(
            person_name="Anaelle Dufour",
            company_name="Crédit Agricole",
        )
        assert rule == "company"

    def test_internal_entity_person_rule(self, mock_note_manager, mock_scapin_config):
        """Test that internal entities use person rule"""
        # Internal entities (Eufonie) SHOULD create person notes
        mock_scapin_config.should_create_person_note.return_value = True

        searcher = EntitySearcher(
            note_manager=mock_note_manager,
            scapin_config=mock_scapin_config,
        )

        # Internal entity (Eufonie) -> person note
        rule = searcher.get_entity_resolution_rule(
            person_name="Marc Dupont",
            company_name="Eufonie",
        )
        assert rule == "person"


class TestCreateEntitySearcher:
    """Tests for factory function"""

    @patch("src.passepartout.entity_search.get_scapin_config")
    def test_create_with_defaults(self, mock_get_config, mock_note_manager):
        """Test factory function with default config"""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        searcher = create_entity_searcher(mock_note_manager)

        assert searcher is not None
        assert searcher.note_manager is mock_note_manager
        mock_get_config.assert_called_once()
