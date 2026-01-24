"""
Tests for RetoucheReviewer — Memory Cycles v2
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.passepartout.note_metadata import NoteMetadata, NoteMetadataStore
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import NoteType
from src.passepartout.retouche_reviewer import (
    AnalysisResult,
    RetoucheAction,
    RetoucheActionResult,
    RetoucheContext,
    RetoucheResult,
    RetoucheReviewer,
)


@pytest.fixture
def mock_note_manager():
    """Create a mock NoteManager"""
    manager = MagicMock()
    manager.notes_dir = "/test/notes"
    return manager


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database"""
    return tmp_path / "test_meta.db"


@pytest.fixture
def metadata_store(temp_db):
    """Create metadata store with temp database"""
    return NoteMetadataStore(temp_db)


@pytest.fixture
def scheduler(metadata_store):
    """Create a scheduler"""
    return NoteScheduler(metadata_store)


@pytest.fixture
def reviewer(mock_note_manager, metadata_store, scheduler):
    """Create a RetoucheReviewer"""
    return RetoucheReviewer(
        note_manager=mock_note_manager,
        metadata_store=metadata_store,
        scheduler=scheduler,
    )


class TestRetoucheActionResult:
    """Tests for RetoucheActionResult dataclass"""

    def test_creation(self):
        """Test creating a RetoucheActionResult"""
        result = RetoucheActionResult(
            action_type=RetoucheAction.ENRICH,
            target="content",
            content="New content",
            confidence=0.9,
            reasoning="Test reasoning",
            applied=True,
            model_used="haiku",
        )

        assert result.action_type == RetoucheAction.ENRICH
        assert result.target == "content"
        assert result.confidence == 0.9
        assert result.applied is True


class TestRetoucheResult:
    """Tests for RetoucheResult dataclass"""

    def test_creation(self):
        """Test creating a RetoucheResult"""
        result = RetoucheResult(
            note_id="test-001",
            success=True,
            quality_before=50,
            quality_after=75,
            actions=[],
            questions_added=2,
            model_used="haiku",
            escalated=False,
            reasoning="Test completed",
        )

        assert result.note_id == "test-001"
        assert result.success is True
        assert result.quality_before == 50
        assert result.quality_after == 75


class TestRetoucheReviewer:
    """Tests for RetoucheReviewer"""

    @pytest.mark.asyncio
    async def test_review_note_not_found(self, reviewer, mock_note_manager):
        """Test review when note not found"""
        mock_note_manager.get_note.return_value = None

        result = await reviewer.review_note("nonexistent")

        assert result.success is False
        assert result.error == "Note not found"

    @pytest.mark.asyncio
    async def test_review_note_creates_metadata(
        self, reviewer, mock_note_manager, metadata_store
    ):
        """Test that review creates metadata if missing"""
        # Setup mock note
        mock_note = MagicMock()
        mock_note.note_id = "test-new"
        mock_note.title = "Test Note"
        mock_note.content = "Some content here " * 20  # > 100 words
        mock_note.file_path = "/test/notes/personne/test-new.md"
        mock_note.tags = []
        mock_note.metadata = {}

        mock_note_manager.get_note.return_value = mock_note
        mock_note_manager.search_notes.return_value = []

        result = await reviewer.review_note("test-new")

        assert result.success is True
        # Metadata should have been created
        metadata = metadata_store.get("test-new")
        assert metadata is not None

    @pytest.mark.asyncio
    async def test_rule_based_analysis(self, reviewer):
        """Test rule-based analysis without AI"""
        # Create context
        mock_note = MagicMock()
        mock_note.title = "Test Note"
        mock_note.content = "Long content " * 100  # > 500 words, < 2 sections

        context = RetoucheContext(
            note=mock_note,
            metadata=NoteMetadata(note_id="test-001"),
            linked_notes=[],
            word_count=600,  # > 500 words to trigger structure suggestion
            has_summary=False,
            section_count=1,  # < 2 sections
            question_count=0,
        )

        # Test rule-based analysis
        result = reviewer._rule_based_analysis(context)

        assert isinstance(result, AnalysisResult)
        assert result.model_used == "rules"
        # Should suggest structure due to long content with few sections
        structure_actions = [
            a for a in result.actions if a.action_type == RetoucheAction.STRUCTURE
        ]
        assert len(structure_actions) > 0

    def test_has_summary_detection(self, reviewer):
        """Test summary detection"""
        # Content with summary
        content_with_summary = """# Note
## Résumé
Ceci est un résumé.

## Contenu
Plus de détails ici.
"""
        assert reviewer._has_summary(content_with_summary) is True

        # Content without summary
        content_without = """# Note
## Introduction
Pas de résumé.
"""
        assert reviewer._has_summary(content_without) is False

    def test_extract_wikilinks(self, reviewer):
        """Test wikilink extraction"""
        content = """
        Some text with [[Link1]] and [[Link2|Display]] links.
        Also [[Another Link]].
        """
        links = reviewer._extract_wikilinks(content)

        assert "Link1" in links
        assert "Link2" in links
        assert "Another Link" in links

    def test_calculate_quality_score(self, reviewer):
        """Test quality score calculation"""
        mock_note = MagicMock()
        mock_note.title = "Test"
        mock_note.content = "Content"

        context = RetoucheContext(
            note=mock_note,
            metadata=NoteMetadata(note_id="test-001"),
            word_count=200,  # +10 points
            has_summary=True,  # +15 points
            section_count=3,  # +9 points
            linked_notes=[MagicMock(), MagicMock()],  # +4 points
        )

        analysis = AnalysisResult(
            actions=[],  # No actions needed
            confidence=0.9,
            model_used="rules",
            escalated=False,
            reasoning="Good",
        )

        score = reviewer._calculate_quality_score(context, analysis)

        # Base 50 + word_count bonus + summary + sections + links
        assert score >= 70

    def test_quality_to_sm2(self, reviewer):
        """Test quality score to SM-2 conversion"""
        assert reviewer._quality_to_sm2(95) == 5
        assert reviewer._quality_to_sm2(80) == 4
        assert reviewer._quality_to_sm2(65) == 3
        assert reviewer._quality_to_sm2(45) == 2
        assert reviewer._quality_to_sm2(25) == 1
        assert reviewer._quality_to_sm2(10) == 0

    def test_apply_summarize_action(self, reviewer):
        """Test applying summarize action"""
        content = """---
title: Test
---

# Content
Some text here.
"""
        action = RetoucheActionResult(
            action_type=RetoucheAction.SUMMARIZE,
            target="header",
            content="This is a summary",
            confidence=0.9,
            applied=True,
            model_used="rules",
        )

        result = reviewer._apply_action(content, action)

        assert "> **Résumé**: This is a summary" in result

    def test_apply_enrich_action(self, reviewer):
        """Test applying enrich action"""
        content = "Original content"
        action = RetoucheActionResult(
            action_type=RetoucheAction.ENRICH,
            target="content",
            content="Additional information",
            confidence=0.9,
            applied=True,
            model_used="rules",
        )

        result = reviewer._apply_action(content, action)

        assert "Original content" in result
        assert "Additional information" in result


class TestRetouchePhase1:
    """Tests for Phase 1 - AI Connection with cache optimization."""

    def test_system_prompt_exists(self):
        """Test that SYSTEM_PROMPT constant exists and contains key instructions."""
        assert hasattr(RetoucheReviewer, "SYSTEM_PROMPT")
        system_prompt = RetoucheReviewer.SYSTEM_PROMPT

        # Check key elements are present
        assert "Scapin" in system_prompt
        assert "Johan" in system_prompt
        assert "score" in system_prompt
        assert "structure" in system_prompt
        assert "enrich" in system_prompt
        assert "JSON" in system_prompt
        assert "confidence" in system_prompt

    def test_system_prompt_is_cacheable(self):
        """Test that SYSTEM_PROMPT is static (suitable for caching)."""
        prompt1 = RetoucheReviewer.SYSTEM_PROMPT
        prompt2 = RetoucheReviewer.SYSTEM_PROMPT

        # Same object reference (immutable string)
        assert prompt1 is prompt2

    def test_build_retouche_prompt_returns_dynamic_content(self, reviewer):
        """Test that _build_retouche_prompt returns note data only."""
        mock_note = MagicMock()
        mock_note.title = "Test Note Title"
        mock_note.content = "This is the note content for testing."

        context = RetoucheContext(
            note=mock_note,
            metadata=NoteMetadata(note_id="test-001", note_type=NoteType.PERSONNE),
            word_count=150,
            has_summary=False,
            section_count=2,
            question_count=1,
            linked_note_excerpts={"Related Note": "Some related content..."},
        )

        prompt = reviewer._build_retouche_prompt(context)

        # Check dynamic content is present
        assert "Test Note Title" in prompt
        assert "This is the note content" in prompt
        assert "150" in prompt  # word count
        assert "personne" in prompt.lower()  # note type
        assert "Related Note" in prompt

        # Check system prompt instructions are NOT in user prompt
        assert "JAMAIS inventer" not in prompt
        assert "Règles absolues" not in prompt

    def test_build_retouche_prompt_handles_missing_note_type(self, reviewer):
        """Test prompt building when note type is missing."""
        mock_note = MagicMock()
        mock_note.title = "Untitled"
        mock_note.content = "Content"

        context = RetoucheContext(
            note=mock_note,
            metadata=NoteMetadata(note_id="test-001"),  # No note_type
            word_count=50,
        )

        prompt = reviewer._build_retouche_prompt(context)

        # Should handle gracefully
        assert "inconnu" in prompt.lower() or "Untitled" in prompt

    @pytest.mark.asyncio
    async def test_call_ai_router_without_engine(self, reviewer):
        """Test _call_ai_router returns empty when no engine available."""
        # reviewer has no ai_router, so _analysis_engine is None
        result = await reviewer._call_ai_router("test prompt", "haiku")

        assert result == {"reasoning": "AI unavailable", "actions": []}

    @pytest.mark.asyncio
    async def test_call_ai_router_uses_system_prompt(self, mock_note_manager, metadata_store, scheduler):
        """Test that _call_ai_router passes system_prompt for caching."""
        from src.sancho.analysis_engine import AICallResult, ModelTier

        # Create mock AI router
        mock_router = MagicMock()

        # Create reviewer with router
        reviewer = RetoucheReviewer(
            note_manager=mock_note_manager,
            metadata_store=metadata_store,
            scheduler=scheduler,
            ai_router=mock_router,
        )

        # Mock the analysis engine's call_ai method
        mock_result = AICallResult(
            response='{"quality_score": 75, "reasoning": "Test", "actions": []}',
            model_used=ModelTier.HAIKU,
            model_id="claude-3-haiku",
            tokens_used=100,
            duration_ms=500.0,
            cache_hit=True,
            cache_read_tokens=500,
        )
        reviewer._analysis_engine.call_ai = AsyncMock(return_value=mock_result)

        # Call the method
        result = await reviewer._call_ai_router("test prompt", "haiku")

        # Verify call_ai was called with system_prompt
        call_args = reviewer._analysis_engine.call_ai.call_args
        assert call_args.kwargs.get("system_prompt") == RetoucheReviewer.SYSTEM_PROMPT

        # Verify result is parsed
        assert result["quality_score"] == 75


class TestRetouchePhase2:
    """Tests for Phase 2 - Jinja2 templates per note type."""

    def test_templates_exist(self):
        """Test that all retouche templates exist."""
        from pathlib import Path

        template_dir = Path(__file__).parent.parent.parent / "templates" / "ai" / "v2" / "retouche"

        expected_templates = [
            "retouche_user.j2",
            "personne.j2",
            "projet.j2",
            "reunion.j2",
            "entite.j2",
            "processus.j2",
            "evenement.j2",
            "generique.j2",
        ]

        for template in expected_templates:
            assert (template_dir / template).exists(), f"Template missing: {template}"

    def test_template_renderer_has_render_retouche(self):
        """Test that TemplateRenderer has render_retouche method."""
        from src.sancho.template_renderer import TemplateRenderer

        assert hasattr(TemplateRenderer, "render_retouche")

    def test_render_retouche_for_personne(self, reviewer):
        """Test that render_retouche produces correct output for PERSONNE type."""
        from src.sancho.template_renderer import get_template_renderer

        mock_note = MagicMock()
        mock_note.title = "Jean Dupont"
        mock_note.content = "Directeur technique chez Acme Corp."

        renderer = get_template_renderer()
        prompt = renderer.render_retouche(
            note=mock_note,
            note_type="personne",
            word_count=50,
            content=mock_note.content,
            quality_score=60,
            linked_notes={"Acme Corp": "Entreprise de technologie..."},
        )

        # Check note data is present
        assert "Jean Dupont" in prompt
        assert "personne" in prompt.lower()
        assert "50" in prompt  # word count

        # Check PERSONNE-specific instructions are included
        assert "contact" in prompt.lower()
        assert "Historique" in prompt or "historique" in prompt

    def test_render_retouche_for_projet(self, reviewer):
        """Test that render_retouche produces correct output for PROJET type."""
        from src.sancho.template_renderer import get_template_renderer

        mock_note = MagicMock()
        mock_note.title = "Migration Cloud"
        mock_note.content = "Migration des services vers AWS."

        renderer = get_template_renderer()
        prompt = renderer.render_retouche(
            note=mock_note,
            note_type="projet",
            word_count=100,
            content=mock_note.content,
        )

        # Check PROJET-specific instructions are included
        assert "Migration Cloud" in prompt
        assert "statut" in prompt.lower() or "status" in prompt.lower()
        assert "Parties prenantes" in prompt or "parties prenantes" in prompt.lower()

    def test_render_retouche_for_reunion(self, reviewer):
        """Test that render_retouche produces correct output for REUNION type."""
        from src.sancho.template_renderer import get_template_renderer

        mock_note = MagicMock()
        mock_note.title = "Réunion Projet Alpha"
        mock_note.content = "Participants: Jean, Marie. Décisions: lancer la phase 2."

        renderer = get_template_renderer()
        prompt = renderer.render_retouche(
            note=mock_note,
            note_type="reunion",
            word_count=80,
            content=mock_note.content,
        )

        # Check REUNION-specific instructions are included
        assert "Réunion Projet Alpha" in prompt
        assert "Participants" in prompt or "participants" in prompt.lower()
        assert "Décisions" in prompt or "décisions" in prompt.lower()

    def test_render_retouche_with_frontmatter(self, reviewer):
        """Test that frontmatter is included in prompt."""
        from src.sancho.template_renderer import get_template_renderer

        mock_note = MagicMock()
        mock_note.title = "Test Note"
        mock_note.content = "Some content"

        renderer = get_template_renderer()
        prompt = renderer.render_retouche(
            note=mock_note,
            note_type="autre",
            word_count=50,
            content=mock_note.content,
            frontmatter="title: Test Note\ntags: [test]",
        )

        # Check frontmatter section is present
        assert "Frontmatter" in prompt
        assert "tags:" in prompt

    def test_render_retouche_with_linked_notes(self, reviewer):
        """Test that linked notes are included in prompt."""
        from src.sancho.template_renderer import get_template_renderer

        mock_note = MagicMock()
        mock_note.title = "Main Note"
        mock_note.content = "References [[Other Note]]"

        renderer = get_template_renderer()
        prompt = renderer.render_retouche(
            note=mock_note,
            note_type="projet",
            word_count=50,
            content=mock_note.content,
            linked_notes={
                "Other Note": "This is the excerpt from Other Note...",
                "Another Note": "Another excerpt here...",
            },
        )

        # Check linked notes section is present
        assert "Notes liées" in prompt
        assert "Other Note" in prompt
        assert "Another Note" in prompt

    def test_build_retouche_prompt_uses_template(self, reviewer, mock_note_manager):
        """Test that _build_retouche_prompt uses TemplateRenderer."""
        mock_note = MagicMock()
        mock_note.title = "Template Test"
        mock_note.content = "---\ntitle: Template Test\n---\n\nContent here."

        context = RetoucheContext(
            note=mock_note,
            metadata=NoteMetadata(note_id="test-001", note_type=NoteType.PERSONNE),
            word_count=50,
            has_summary=False,
            section_count=1,
            linked_note_excerpts={"Related": "Related content..."},
        )

        prompt = reviewer._build_retouche_prompt(context)

        # Check template was used (should have structured format)
        assert "Template Test" in prompt
        assert "personne" in prompt.lower()
        assert "50" in prompt  # word count

    def test_unknown_note_type_uses_generique(self, reviewer):
        """Test that unknown note types fall back to generique template."""
        from src.sancho.template_renderer import get_template_renderer

        mock_note = MagicMock()
        mock_note.title = "Unknown Type Note"
        mock_note.content = "Some random content."

        renderer = get_template_renderer()
        prompt = renderer.render_retouche(
            note=mock_note,
            note_type="unknown_type",
            word_count=30,
            content=mock_note.content,
        )

        # Should use generique template instructions
        assert "Unknown Type Note" in prompt
        # generique template should have general focus points
        assert "Structure" in prompt or "structure" in prompt.lower()
