"""
Tests pour les modèles Workflow v2.1

Ce module teste les dataclasses et leurs validations pour le pipeline
d'extraction de connaissances.
"""

from datetime import datetime

import pytest

from src.core.models.v2_models import (
    AnalysisResult,
    ContextNote,
    EmailAction,
    EnrichmentResult,
    Extraction,
    ExtractionType,
    ImportanceLevel,
    NoteAction,
    NoteResult,
)


class TestExtraction:
    """Tests pour la classe Extraction"""

    def test_extraction_creation_valid(self):
        """Test création d'une extraction valide"""
        extraction = Extraction(
            info="Budget validé 50k€",
            type=ExtractionType.DECISION,
            importance=ImportanceLevel.HAUTE,
            note_cible="Projet Alpha",
            note_action=NoteAction.ENRICHIR,
            omnifocus=False,
        )

        assert extraction.info == "Budget validé 50k€"
        assert extraction.type == ExtractionType.DECISION
        assert extraction.importance == ImportanceLevel.HAUTE
        assert extraction.note_cible == "Projet Alpha"
        assert extraction.note_action == NoteAction.ENRICHIR
        assert extraction.omnifocus is False

    def test_extraction_with_strings(self):
        """Test création avec des strings au lieu d'enums"""
        extraction = Extraction(
            info="Marc livrera le rapport",
            type="engagement",  # type: ignore
            importance="haute",  # type: ignore
            note_cible="Projet Alpha",
            note_action="enrichir",  # type: ignore
            omnifocus=True,
        )

        assert extraction.type == ExtractionType.ENGAGEMENT
        assert extraction.importance == ImportanceLevel.HAUTE
        assert extraction.note_action == NoteAction.ENRICHIR
        assert extraction.omnifocus is True

    def test_extraction_empty_info_raises(self):
        """Test qu'une info vide lève une erreur"""
        with pytest.raises(ValueError, match="info ne peut pas être vide"):
            Extraction(
                info="",
                type=ExtractionType.FAIT,
                importance=ImportanceLevel.MOYENNE,
                note_cible="Test",
                note_action=NoteAction.CREER,
            )

    def test_extraction_whitespace_info_raises(self):
        """Test qu'une info avec seulement des espaces lève une erreur"""
        with pytest.raises(ValueError, match="info ne peut pas être vide"):
            Extraction(
                info="   ",
                type=ExtractionType.FAIT,
                importance=ImportanceLevel.MOYENNE,
                note_cible="Test",
                note_action=NoteAction.CREER,
            )

    def test_extraction_empty_note_cible_raises(self):
        """Test qu'une note_cible vide lève une erreur"""
        with pytest.raises(ValueError, match="note_cible ne peut pas être vide"):
            Extraction(
                info="Information valide",
                type=ExtractionType.FAIT,
                importance=ImportanceLevel.MOYENNE,
                note_cible="",
                note_action=NoteAction.CREER,
            )

    def test_extraction_invalid_type_raises(self):
        """Test qu'un type invalide lève une erreur"""
        with pytest.raises(ValueError):
            Extraction(
                info="Test",
                type="invalid_type",  # type: ignore
                importance=ImportanceLevel.HAUTE,
                note_cible="Test",
                note_action=NoteAction.ENRICHIR,
            )

    def test_extraction_all_types(self):
        """Test tous les types d'extraction"""
        for extraction_type in ExtractionType:
            extraction = Extraction(
                info=f"Test {extraction_type.value}",
                type=extraction_type,
                importance=ImportanceLevel.MOYENNE,
                note_cible="Test",
                note_action=NoteAction.ENRICHIR,
            )
            assert extraction.type == extraction_type


class TestAnalysisResult:
    """Tests pour la classe AnalysisResult"""

    def test_analysis_result_creation_valid(self):
        """Test création d'un AnalysisResult valide"""
        result = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.92,
            raisonnement="Newsletter sans information permanente",
            model_used="haiku",
            tokens_used=450,
            duration_ms=1200.5,
        )

        assert result.extractions == []
        assert result.action == EmailAction.ARCHIVE
        assert result.confidence == 0.92
        assert result.model_used == "haiku"
        assert result.tokens_used == 450
        assert result.duration_ms == 1200.5
        assert result.escalated is False
        assert isinstance(result.timestamp, datetime)

    def test_analysis_result_with_extractions(self):
        """Test avec des extractions"""
        extraction = Extraction(
            info="Test info",
            type=ExtractionType.DECISION,
            importance=ImportanceLevel.HAUTE,
            note_cible="Test Note",
            note_action=NoteAction.ENRICHIR,
            omnifocus=True,
        )

        result = AnalysisResult(
            extractions=[extraction],
            action=EmailAction.FLAG,
            confidence=0.85,
            raisonnement="Important decision found",
            model_used="sonnet",
            tokens_used=800,
            duration_ms=2500.0,
            escalated=True,
        )

        assert len(result.extractions) == 1
        assert result.has_extractions is True
        assert result.extraction_count == 1
        assert result.omnifocus_tasks_count == 1
        assert result.escalated is True

    def test_analysis_result_action_from_string(self):
        """Test conversion string → EmailAction"""
        result = AnalysisResult(
            extractions=[],
            action="queue",  # type: ignore
            confidence=0.5,
            raisonnement="Uncertain",
            model_used="haiku",
            tokens_used=300,
            duration_ms=800.0,
        )

        assert result.action == EmailAction.QUEUE

    def test_analysis_result_confidence_bounds(self):
        """Test que confidence doit être entre 0 et 1"""
        with pytest.raises(ValueError, match="confidence doit être entre 0 et 1"):
            AnalysisResult(
                extractions=[],
                action=EmailAction.RIEN,
                confidence=1.5,  # Invalid
                raisonnement="Test",
                model_used="haiku",
                tokens_used=100,
                duration_ms=500.0,
            )

        with pytest.raises(ValueError, match="confidence doit être entre 0 et 1"):
            AnalysisResult(
                extractions=[],
                action=EmailAction.RIEN,
                confidence=-0.1,  # Invalid
                raisonnement="Test",
                model_used="haiku",
                tokens_used=100,
                duration_ms=500.0,
            )

    def test_analysis_result_negative_tokens_raises(self):
        """Test que tokens_used négatif lève une erreur"""
        with pytest.raises(ValueError, match="tokens_used doit être >= 0"):
            AnalysisResult(
                extractions=[],
                action=EmailAction.ARCHIVE,
                confidence=0.9,
                raisonnement="Test",
                model_used="haiku",
                tokens_used=-10,
                duration_ms=500.0,
            )

    def test_analysis_result_negative_duration_raises(self):
        """Test que duration_ms négatif lève une erreur"""
        with pytest.raises(ValueError, match="duration_ms doit être >= 0"):
            AnalysisResult(
                extractions=[],
                action=EmailAction.ARCHIVE,
                confidence=0.9,
                raisonnement="Test",
                model_used="haiku",
                tokens_used=100,
                duration_ms=-500.0,
            )

    def test_analysis_result_high_confidence_property(self):
        """Test propriété high_confidence"""
        high_conf = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.90,
            raisonnement="",
            model_used="haiku",
            tokens_used=100,
            duration_ms=500.0,
        )
        assert high_conf.high_confidence is True

        low_conf = AnalysisResult(
            extractions=[],
            action=EmailAction.QUEUE,
            confidence=0.60,
            raisonnement="",
            model_used="haiku",
            tokens_used=100,
            duration_ms=500.0,
        )
        assert low_conf.high_confidence is False

        # Edge case: exactement 0.85
        edge_conf = AnalysisResult(
            extractions=[],
            action=EmailAction.ARCHIVE,
            confidence=0.85,
            raisonnement="",
            model_used="haiku",
            tokens_used=100,
            duration_ms=500.0,
        )
        assert edge_conf.high_confidence is True

    def test_analysis_result_omnifocus_count(self):
        """Test comptage des tâches OmniFocus"""
        extractions = [
            Extraction(
                info="Task 1",
                type=ExtractionType.DEADLINE,
                importance=ImportanceLevel.HAUTE,
                note_cible="Note 1",
                note_action=NoteAction.ENRICHIR,
                omnifocus=True,
            ),
            Extraction(
                info="Task 2",
                type=ExtractionType.DECISION,
                importance=ImportanceLevel.MOYENNE,
                note_cible="Note 2",
                note_action=NoteAction.ENRICHIR,
                omnifocus=False,
            ),
            Extraction(
                info="Task 3",
                type=ExtractionType.ENGAGEMENT,
                importance=ImportanceLevel.HAUTE,
                note_cible="Note 3",
                note_action=NoteAction.ENRICHIR,
                omnifocus=True,
            ),
        ]

        result = AnalysisResult(
            extractions=extractions,
            action=EmailAction.ARCHIVE,
            confidence=0.9,
            raisonnement="",
            model_used="sonnet",
            tokens_used=1000,
            duration_ms=3000.0,
        )

        assert result.extraction_count == 3
        assert result.omnifocus_tasks_count == 2


class TestNoteResult:
    """Tests pour la classe NoteResult"""

    def test_note_result_success(self):
        """Test NoteResult succès"""
        result = NoteResult(
            note_id="note_123",
            created=False,
            title="Test Note",
        )

        assert result.note_id == "note_123"
        assert result.created is False
        assert result.title == "Test Note"
        assert result.error is None
        assert result.success is True

    def test_note_result_created(self):
        """Test NoteResult avec création"""
        result = NoteResult(
            note_id="note_new",
            created=True,
            title="New Note",
        )

        assert result.created is True
        assert result.success is True

    def test_note_result_error(self):
        """Test NoteResult avec erreur"""
        result = NoteResult(
            note_id="note_123",
            created=False,
            title="Failed Note",
            error="Note not found",
        )

        assert result.error == "Note not found"
        assert result.success is False


class TestEnrichmentResult:
    """Tests pour la classe EnrichmentResult"""

    def test_enrichment_result_empty(self):
        """Test EnrichmentResult vide"""
        result = EnrichmentResult()

        assert result.notes_updated == []
        assert result.notes_created == []
        assert result.tasks_created == []
        assert result.errors == []
        assert result.success is True
        assert result.total_notes_affected == 0
        assert result.has_changes is False

    def test_enrichment_result_with_notes(self):
        """Test EnrichmentResult avec des notes"""
        result = EnrichmentResult(
            notes_updated=["note_1", "note_2"],
            notes_created=["note_new"],
            tasks_created=["task_1"],
            errors=[],
        )

        assert len(result.notes_updated) == 2
        assert len(result.notes_created) == 1
        assert len(result.tasks_created) == 1
        assert result.success is True
        assert result.total_notes_affected == 3
        assert result.has_changes is True

    def test_enrichment_result_with_errors(self):
        """Test EnrichmentResult avec erreurs"""
        result = EnrichmentResult(
            notes_updated=["note_1"],
            notes_created=[],
            tasks_created=[],
            errors=["Failed to update note_2: permission denied"],
        )

        assert result.success is False
        assert len(result.errors) == 1
        assert result.has_changes is True

    def test_enrichment_result_only_tasks(self):
        """Test EnrichmentResult avec seulement des tâches"""
        result = EnrichmentResult(
            notes_updated=[],
            notes_created=[],
            tasks_created=["task_1", "task_2"],
            errors=[],
        )

        assert result.success is True
        assert result.total_notes_affected == 0
        assert result.has_changes is True  # Tasks count as changes


class TestContextNote:
    """Tests pour la classe ContextNote"""

    def test_context_note_creation_valid(self):
        """Test création d'une ContextNote valide"""
        context = ContextNote(
            title="Projet Alpha",
            type="projet",
            content_summary="Projet de refonte API, deadline mars 2026...",
            relevance=0.87,
            note_id="projets/alpha",
        )

        assert context.title == "Projet Alpha"
        assert context.type == "projet"
        assert context.content_summary.startswith("Projet de refonte")
        assert context.relevance == 0.87
        assert context.note_id == "projets/alpha"

    def test_context_note_without_id(self):
        """Test ContextNote sans note_id"""
        context = ContextNote(
            title="Marc Dupont",
            type="personne",
            content_summary="Directeur technique chez Acme Corp",
            relevance=0.75,
        )

        assert context.note_id is None

    def test_context_note_relevance_bounds(self):
        """Test que relevance doit être entre 0 et 1"""
        with pytest.raises(ValueError, match="relevance doit être entre 0 et 1"):
            ContextNote(
                title="Test",
                type="concept",
                content_summary="Test summary",
                relevance=1.5,  # Invalid
            )

        with pytest.raises(ValueError, match="relevance doit être entre 0 et 1"):
            ContextNote(
                title="Test",
                type="concept",
                content_summary="Test summary",
                relevance=-0.1,  # Invalid
            )

    def test_context_note_empty_title_raises(self):
        """Test qu'un titre vide lève une erreur"""
        with pytest.raises(ValueError, match="title ne peut pas être vide"):
            ContextNote(
                title="",
                type="projet",
                content_summary="Some content",
                relevance=0.5,
            )

    def test_context_note_whitespace_title_raises(self):
        """Test qu'un titre avec espaces seulement lève une erreur"""
        with pytest.raises(ValueError, match="title ne peut pas être vide"):
            ContextNote(
                title="   ",
                type="projet",
                content_summary="Some content",
                relevance=0.5,
            )


class TestEnums:
    """Tests pour les enums du module"""

    def test_extraction_type_values(self):
        """Test que tous les types d'extraction sont bien définis"""
        # 14 types définis dans v2.1.1
        expected_values = {
            "decision", "engagement", "fait", "deadline", "relation",
            "coordonnees", "montant", "reference", "evenement", "demande",
            "citation", "objectif", "competence", "preference"
        }
        actual_values = {t.value for t in ExtractionType}
        assert actual_values == expected_values

    def test_importance_level_values(self):
        """Test les niveaux d'importance (3 niveaux v2.1.1)"""
        assert ImportanceLevel.HAUTE.value == "haute"
        assert ImportanceLevel.MOYENNE.value == "moyenne"
        assert ImportanceLevel.BASSE.value == "basse"

    def test_note_action_values(self):
        """Test les actions sur les notes"""
        assert NoteAction.ENRICHIR.value == "enrichir"
        assert NoteAction.CREER.value == "creer"

    def test_email_action_values(self):
        """Test les actions sur les emails"""
        expected_values = {"archive", "flag", "queue", "delete", "rien"}
        actual_values = {a.value for a in EmailAction}
        assert actual_values == expected_values


class TestEdgeCases:
    """Tests pour les cas limites"""

    def test_extraction_minimal_valid(self):
        """Test extraction avec les valeurs minimales"""
        extraction = Extraction(
            info="X",
            type=ExtractionType.FAIT,
            importance=ImportanceLevel.MOYENNE,
            note_cible="Y",
            note_action=NoteAction.ENRICHIR,
        )
        assert extraction.info == "X"
        assert extraction.omnifocus is False  # Default

    def test_analysis_result_zero_confidence(self):
        """Test avec confidence = 0"""
        result = AnalysisResult(
            extractions=[],
            action=EmailAction.QUEUE,
            confidence=0.0,
            raisonnement="Completely uncertain",
            model_used="haiku",
            tokens_used=0,
            duration_ms=0.0,
        )
        assert result.confidence == 0.0
        assert result.high_confidence is False

    def test_analysis_result_max_confidence(self):
        """Test avec confidence = 1"""
        result = AnalysisResult(
            extractions=[],
            action=EmailAction.DELETE,
            confidence=1.0,
            raisonnement="Absolutely certain",
            model_used="sonnet",
            tokens_used=1000,
            duration_ms=5000.0,
        )
        assert result.confidence == 1.0
        assert result.high_confidence is True

    def test_context_note_zero_relevance(self):
        """Test ContextNote avec relevance = 0"""
        context = ContextNote(
            title="Irrelevant",
            type="autre",
            content_summary="Not related",
            relevance=0.0,
        )
        assert context.relevance == 0.0

    def test_context_note_max_relevance(self):
        """Test ContextNote avec relevance = 1"""
        context = ContextNote(
            title="Highly Relevant",
            type="projet",
            content_summary="Directly related",
            relevance=1.0,
        )
        assert context.relevance == 1.0
