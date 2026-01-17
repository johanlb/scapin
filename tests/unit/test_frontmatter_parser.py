"""
Tests for Frontmatter Parser and Schema.

Tests the parsing of YAML frontmatter into typed dataclasses.
"""

from datetime import datetime, timezone

import pytest

from src.passepartout.frontmatter_parser import FrontmatterParser
from src.passepartout.frontmatter_schema import (
    ActifFrontmatter,
    BaseFrontmatter,
    Contact,
    EntiteFrontmatter,
    LinkedSource,
    PendingUpdate,
    PersonneFrontmatter,
    ProjetFrontmatter,
    ReunionFrontmatter,
    Stakeholder,
)
from src.passepartout.note_types import (
    Category,
    EntityType,
    ImportanceLevel,
    NoteType,
    ProjectStatus,
    Relation,
    RelationshipStrength,
)


class TestFrontmatterParser:
    """Tests for FrontmatterParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return FrontmatterParser()

    def test_parse_empty_dict(self, parser):
        """Test parsing empty dict returns base frontmatter."""
        result = parser.parse({})
        assert isinstance(result, BaseFrontmatter)
        assert result.title == ""
        assert result.type == NoteType.AUTRE

    def test_parse_minimal_frontmatter(self, parser):
        """Test parsing minimal frontmatter."""
        yaml_dict = {
            "title": "Test Note",
            "tags": ["test", "unit"],
        }
        result = parser.parse(yaml_dict)
        assert result.title == "Test Note"
        assert result.tags == ["test", "unit"]

    def test_detect_type_from_explicit_field(self, parser):
        """Test type detection from explicit type field."""
        yaml_dict = {"title": "Test", "type": "personne"}
        result = parser.parse(yaml_dict)
        assert isinstance(result, PersonneFrontmatter)
        assert result.type == NoteType.PERSONNE

    def test_detect_type_from_path(self, parser):
        """Test type detection from metadata path."""
        yaml_dict = {
            "title": "Test",
            "metadata": {"path": "Personal Knowledge Management/Personnes"},
        }
        result = parser.parse(yaml_dict)
        assert isinstance(result, PersonneFrontmatter)

    def test_parse_personne_full(self, parser):
        """Test parsing full PERSONNE frontmatter."""
        yaml_dict = {
            "title": "Jean Dupont",
            "type": "personne",
            "aliases": ["Jean", "JD", "J. Dupont"],
            "importance": "haute",
            "relation": "collègue",
            "relationship_strength": "forte",
            "introduced_by": "[[Marie Martin]]",
            "organization": "[[Acme Corp]]",
            "role": "Directeur technique",
            "sector": "technologie",
            "email": "jean@acme.com",
            "phone": "+33 6 12 34 56 78",
            "preferred_language": "français",
            "communication_style": "formel",
            "timezone": "Europe/Paris",
            "projects": ["[[Projet Alpha]]", "[[Projet Beta]]"],
            "last_contact": "2026-01-15T10:00:00+00:00",
            "mention_count": 42,
            "first_contact": "2024-06-01",
            "tags": ["tech", "partenaire"],
        }
        result = parser.parse(yaml_dict)

        assert isinstance(result, PersonneFrontmatter)
        assert result.title == "Jean Dupont"
        assert result.aliases == ["Jean", "JD", "J. Dupont"]
        assert result.importance == ImportanceLevel.HIGH
        assert result.relation == Relation.COLLEGUE
        assert result.relationship_strength == RelationshipStrength.FORTE
        assert result.introduced_by == "[[Marie Martin]]"
        assert result.organization == "[[Acme Corp]]"
        assert result.role == "Directeur technique"
        assert result.email == "jean@acme.com"
        assert result.phone == "+33 6 12 34 56 78"
        assert result.projects == ["[[Projet Alpha]]", "[[Projet Beta]]"]
        assert result.mention_count == 42
        assert result.last_contact is not None

    def test_parse_projet_full(self, parser):
        """Test parsing full PROJET frontmatter."""
        yaml_dict = {
            "title": "Projet Immobilier Maurice",
            "type": "projet",
            "aliases": ["Maurice", "ORV"],
            "status": "actif",
            "priority": "haute",
            "domain": "immobilier",
            "start_date": "2024-06-01",
            "target_date": "2027-12-31",
            "stakeholders": [
                {"person": "[[Johan Le Bail]]", "role": "investisseur"},
                {"person": "[[Hugues Lagesse]]", "role": "partenaire"},
            ],
            "budget_range": ">100k€",
            "currency": "EUR",
            "related_entities": ["[[Ocean River Villa]]"],
            "last_activity": "2026-01-15T14:00:00+00:00",
            "activity_count": 45,
        }
        result = parser.parse(yaml_dict)

        assert isinstance(result, ProjetFrontmatter)
        assert result.title == "Projet Immobilier Maurice"
        assert result.status == ProjectStatus.ACTIF
        assert result.domain == "immobilier"
        assert len(result.stakeholders) == 2
        assert result.stakeholders[0].person == "[[Johan Le Bail]]"
        assert result.stakeholders[0].role == "investisseur"
        assert result.budget_range == ">100k€"
        assert result.activity_count == 45

    def test_parse_entite_full(self, parser):
        """Test parsing full ENTITE frontmatter."""
        yaml_dict = {
            "title": "Eufonie",
            "type": "entite",
            "aliases": ["Eufonie SAS"],
            "entity_type": "entreprise",
            "sector": "consulting IT",
            "relationship": "employeur",
            "contacts": [
                {"person": "[[Johan Le Bail]]", "role": "co-fondateur"},
            ],
            "website": "https://eufonie.fr",
            "email_domain": "eufonie.fr",
            "country": "France",
            "projects": ["[[Infrastructure Cloud]]"],
        }
        result = parser.parse(yaml_dict)

        assert isinstance(result, EntiteFrontmatter)
        assert result.title == "Eufonie"
        assert result.entity_type == EntityType.ENTREPRISE
        assert result.relationship == "employeur"
        assert len(result.contacts) == 1
        assert result.website == "https://eufonie.fr"

    def test_parse_reunion_full(self, parser):
        """Test parsing full REUNION frontmatter."""
        yaml_dict = {
            "title": "Point projet - 15 jan 2026",
            "type": "reunion",
            "date": "2026-01-15T14:00:00+00:00",
            "duration_minutes": 60,
            "location": "Teams",
            "location_type": "online",
            "participants": [
                {"person": "[[Johan Le Bail]]", "role": "organisateur"},
                {"person": "[[Hugues Lagesse]]", "role": "participant"},
            ],
            "project": "[[Projet Immobilier Maurice]]",
            "agenda": ["Budget Q1", "Planning", "Questions"],
            "decisions": ["Valider le budget"],
            "action_items": ["Envoyer le rapport"],
        }
        result = parser.parse(yaml_dict)

        assert isinstance(result, ReunionFrontmatter)
        assert result.duration_minutes == 60
        assert result.location == "Teams"
        assert result.location_type == "online"
        assert len(result.participants) == 2
        assert result.agenda == ["Budget Q1", "Planning", "Questions"]

    def test_parse_actif(self, parser):
        """Test parsing ACTIF frontmatter."""
        yaml_dict = {
            "title": "Nautil 6",
            "type": "entite",
            "asset_type": "bien_immobilier",
            "asset_category": "appartement",
            "location": "Azuri",
            "country": "Maurice",
            "current_status": "loué",
            "contacts": [
                {"person": "[[Gestionnaire]]", "role": "syndic"},
            ],
            "projects": ["[[Projet Vente Nautil 6]]"],
        }
        result = parser.parse(yaml_dict)

        assert isinstance(result, ActifFrontmatter)
        assert result.asset_type == "bien_immobilier"
        assert result.current_status == "loué"

    def test_parse_linked_sources(self, parser):
        """Test parsing linked_sources."""
        yaml_dict = {
            "title": "Test",
            "linked_sources": [
                {"type": "folder", "path": "~/Documents/Projets", "priority": 1},
                {"type": "whatsapp", "contact": "Équipe", "priority": 2},
                {"type": "email", "filter": "from:@acme.com"},
            ],
        }
        result = parser.parse(yaml_dict)

        assert len(result.linked_sources) == 3
        assert result.linked_sources[0].type == "folder"
        assert result.linked_sources[0].identifier == "~/Documents/Projets"
        assert result.linked_sources[0].priority == 1
        assert result.linked_sources[1].type == "whatsapp"
        assert result.linked_sources[1].identifier == "Équipe"
        assert result.linked_sources[2].type == "email"

    def test_parse_pending_updates(self, parser):
        """Test parsing pending_updates."""
        yaml_dict = {
            "title": "Test",
            "pending_updates": [
                {
                    "field": "email",
                    "value": "new@example.com",
                    "source": "email_signature",
                    "source_ref": "msg_123",
                    "detected_at": "2026-01-15T10:00:00+00:00",
                    "confidence": 0.92,
                },
            ],
        }
        result = parser.parse(yaml_dict)

        assert len(result.pending_updates) == 1
        pu = result.pending_updates[0]
        assert pu.field == "email"
        assert pu.value == "new@example.com"
        assert pu.source == "email_signature"
        assert pu.confidence == 0.92

    def test_parse_datetime_formats(self, parser):
        """Test parsing various datetime formats."""
        yaml_dict = {
            "title": "Test",
            "type": "personne",
            "created_at": "2026-01-15T10:00:00+00:00",
            "last_contact": "2026-01-15",  # Date only
        }
        result = parser.parse(yaml_dict)

        assert result.created_at is not None
        assert result.created_at.year == 2026
        assert isinstance(result, PersonneFrontmatter)
        assert result.last_contact is not None
        assert result.last_contact.year == 2026

    def test_parse_importance_french(self, parser):
        """Test parsing French importance values."""
        yaml_dict = {"title": "Test", "importance": "haute"}
        result = parser.parse(yaml_dict)
        assert result.importance == ImportanceLevel.HIGH

        yaml_dict2 = {"title": "Test", "importance": "basse"}
        result2 = parser.parse(yaml_dict2)
        assert result2.importance == ImportanceLevel.LOW

    def test_to_dict_roundtrip(self, parser):
        """Test that to_dict produces valid YAML dict."""
        original = PersonneFrontmatter(
            title="Jean Dupont",
            aliases=["Jean", "JD"],
            relation=Relation.COLLEGUE,
            email="jean@example.com",
            projects=["[[Projet A]]"],
        )
        yaml_dict = parser.to_dict(original)

        assert yaml_dict["title"] == "Jean Dupont"
        assert yaml_dict["aliases"] == ["Jean", "JD"]
        assert yaml_dict["relation"] == "collègue"
        assert yaml_dict["email"] == "jean@example.com"
        assert yaml_dict["projects"] == ["[[Projet A]]"]


class TestDataclasses:
    """Tests for dataclass functionality."""

    def test_pending_update_to_dict(self):
        """Test PendingUpdate.to_dict()."""
        pu = PendingUpdate(
            field="email",
            value="test@example.com",
            source="email_signature",
            source_ref="msg_123",
            detected_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            confidence=0.9,
        )
        d = pu.to_dict()
        assert d["field"] == "email"
        assert d["value"] == "test@example.com"
        assert d["confidence"] == 0.9

    def test_stakeholder_to_dict(self):
        """Test Stakeholder.to_dict()."""
        s = Stakeholder(person="[[Johan]]", role="investisseur")
        d = s.to_dict()
        assert d["person"] == "[[Johan]]"
        assert d["role"] == "investisseur"

    def test_linked_source_to_dict(self):
        """Test LinkedSource.to_dict()."""
        ls = LinkedSource(type="folder", identifier="~/Documents", priority=1)
        d = ls.to_dict()
        assert d["type"] == "folder"
        assert d["path"] == "~/Documents"
        assert d["priority"] == 1

    def test_contact_to_dict(self):
        """Test Contact.to_dict()."""
        c = Contact(person="[[Marie]]", role="syndic")
        d = c.to_dict()
        assert d["person"] == "[[Marie]]"
        assert d["role"] == "syndic"


class TestNoteTypesEnums:
    """Tests for new enums in note_types.py."""

    def test_relation_from_string(self):
        """Test Relation.from_string()."""
        assert Relation.from_string("collègue") == Relation.COLLEGUE
        assert Relation.from_string("PARTENAIRE") == Relation.PARTENAIRE
        assert Relation.from_string("invalid") is None
        assert Relation.from_string("") is None

    def test_relationship_strength_from_string(self):
        """Test RelationshipStrength.from_string()."""
        assert RelationshipStrength.from_string("forte") == RelationshipStrength.FORTE
        assert RelationshipStrength.from_string("Moyenne") == RelationshipStrength.MOYENNE
        assert RelationshipStrength.from_string("invalid") is None

    def test_project_status_from_string(self):
        """Test ProjectStatus.from_string()."""
        assert ProjectStatus.from_string("actif") == ProjectStatus.ACTIF
        assert ProjectStatus.from_string("terminé") == ProjectStatus.TERMINE
        assert ProjectStatus.from_string("termine") == ProjectStatus.TERMINE  # Without accent
        assert ProjectStatus.from_string("invalid") is None

    def test_entity_type_from_string(self):
        """Test EntityType.from_string()."""
        assert EntityType.from_string("entreprise") == EntityType.ENTREPRISE
        assert EntityType.from_string("ADMINISTRATION") == EntityType.ADMINISTRATION
        assert EntityType.from_string("invalid") is None

    def test_category_from_string(self):
        """Test Category.from_string()."""
        assert Category.from_string("work") == Category.WORK
        assert Category.from_string("Personal") == Category.PERSONAL
        assert Category.from_string("invalid") is None
