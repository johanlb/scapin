"""Tests for Grimaud Analyzer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.grimaud.analyzer import (
    DetectedProblem,
    GrimaudAnalyzer,
    ProblemType,
    Severity,
)
from src.grimaud.models import GrimaudActionType


@pytest.fixture
def mock_note_manager():
    """Mock NoteManager."""
    manager = MagicMock()
    return manager


@pytest.fixture
def analyzer(mock_note_manager):
    """Cree un analyzer avec mocks."""
    return GrimaudAnalyzer(note_manager=mock_note_manager)


class TestProblemType:
    """Tests for ProblemType enum."""

    def test_all_problem_types_exist(self):
        """Tous les types de problemes existent."""
        assert ProblemType.EMPTY_SECTION
        assert ProblemType.BROKEN_LINK
        assert ProblemType.MISSING_FRONTMATTER
        assert ProblemType.SIMILAR_NOTE
        assert ProblemType.OUTDATED
        assert ProblemType.TOO_SHORT
        assert ProblemType.TOO_LONG


class TestDetectedProblem:
    """Tests for DetectedProblem dataclass."""

    def test_create_detected_problem(self):
        """Cree un probleme detecte."""
        problem = DetectedProblem(
            problem_type=ProblemType.EMPTY_SECTION,
            severity=Severity.MEDIUM,
            details="Section vide: ## References",
        )

        assert problem.problem_type == ProblemType.EMPTY_SECTION
        assert problem.severity == Severity.MEDIUM
        assert "References" in problem.details


class TestDetectLocalProblems:
    """Tests for detect_local_problems method."""

    def test_detects_empty_sections(self, analyzer):
        """Detecte les sections vides."""
        content = """# Note Title

## Introduction

Some content here.

## References

## Conclusion

Final thoughts.
"""
        problems = analyzer.detect_local_problems(content, {"title": "Test"})

        # Should detect empty "References" section
        empty_section_problems = [
            p for p in problems if p.problem_type == ProblemType.EMPTY_SECTION
        ]
        assert len(empty_section_problems) >= 1
        assert any("References" in p.details for p in empty_section_problems)

    def test_detects_empty_section_at_end(self, analyzer):
        """Detecte les sections vides en fin de document."""
        content = """# Title

## Introduction

Content here.

## Notes
"""
        problems = analyzer.detect_local_problems(content, {"title": "Test"})

        empty_section_problems = [
            p for p in problems if p.problem_type == ProblemType.EMPTY_SECTION
        ]
        assert len(empty_section_problems) >= 1
        assert any("Notes" in p.details for p in empty_section_problems)

    def test_detects_broken_wikilinks(self, analyzer, mock_note_manager):
        """Detecte les wikilinks casses."""
        content = """# Note Title

See [[Note Existante]] and [[Note Inexistante]] for more info.
"""
        # Mock note lookup - only "Note Existante" exists
        mock_note_manager.find_note_by_alias.side_effect = lambda title: (
            MagicMock() if title == "Note Existante" else None
        )

        problems = analyzer.detect_local_problems(content, {"title": "Test"})

        broken_link_problems = [
            p for p in problems if p.problem_type == ProblemType.BROKEN_LINK
        ]
        assert len(broken_link_problems) >= 1
        assert any("Note Inexistante" in p.details for p in broken_link_problems)

    def test_detects_missing_frontmatter_title(self, analyzer):
        """Detecte l'absence de titre dans le frontmatter."""
        content = "# Some content without frontmatter"
        frontmatter = {}  # No title key

        problems = analyzer.detect_local_problems(content, frontmatter)

        missing_fm_problems = [
            p for p in problems if p.problem_type == ProblemType.MISSING_FRONTMATTER
        ]
        assert len(missing_fm_problems) >= 1

    def test_detects_too_short_notes(self, analyzer):
        """Detecte les notes trop courtes."""
        content = "# Title\n\nJuste quelques mots."  # < 50 words
        frontmatter = {"title": "Short Note"}

        problems = analyzer.detect_local_problems(content, frontmatter)

        short_problems = [
            p for p in problems if p.problem_type == ProblemType.TOO_SHORT
        ]
        assert len(short_problems) >= 1

    def test_returns_empty_for_clean_note(self, analyzer, mock_note_manager):
        """Retourne une liste vide pour une note sans problemes."""
        # Note with enough content, valid frontmatter, valid links
        content = """# Clean Note

## Introduction

This is a clean note with plenty of content to meet the minimum word count.
The content is well organized with proper sections and structure.
We have multiple paragraphs to ensure we exceed fifty words total.

## Details

Here we have more content explaining the details of our topic.
This section also has substantial content for completeness.
The note follows all the best practices for PKM.

## References

See [[Note Existante]] for related information.
"""
        frontmatter = {"title": "Clean Note"}
        mock_note_manager.find_note_by_alias.return_value = MagicMock()

        problems = analyzer.detect_local_problems(content, frontmatter)

        # Should have no critical problems (empty sections, broken links, missing fm)
        critical_problems = [
            p for p in problems
            if p.problem_type in (
                ProblemType.EMPTY_SECTION,
                ProblemType.BROKEN_LINK,
                ProblemType.MISSING_FRONTMATTER,
                ProblemType.TOO_SHORT,
            )
        ]
        assert len(critical_problems) == 0

    def test_handles_wikilinks_with_labels(self, analyzer, mock_note_manager):
        """Gere les wikilinks avec labels [[target|label]]."""
        content = "See [[Note Target|alias displayed]] for details."
        frontmatter = {"title": "Test"}
        mock_note_manager.find_note_by_alias.return_value = None

        problems = analyzer.detect_local_problems(content, frontmatter)

        broken_link_problems = [
            p for p in problems if p.problem_type == ProblemType.BROKEN_LINK
        ]
        assert len(broken_link_problems) >= 1
        # Should check "Note Target", not the label
        assert any("Note Target" in p.details for p in broken_link_problems)


class TestDetectSimilarNotes:
    """Tests for detect_similar_notes method."""

    def test_filters_by_threshold(self, analyzer, mock_note_manager):
        """Filtre les notes similaires par seuil."""
        # Mock search_notes returns similarity scores
        mock_note_manager.search_notes.return_value = [
            (MagicMock(note_id="similar-1"), 0.95),
            (MagicMock(note_id="similar-2"), 0.88),
            (MagicMock(note_id="different"), 0.70),
        ]

        result = analyzer.detect_similar_notes("test-note", threshold=0.85)

        # Should only include notes above threshold (0.85)
        assert len(result) == 2
        note_ids = [note_id for note_id, _ in result]
        assert "similar-1" in note_ids
        assert "similar-2" in note_ids
        assert "different" not in note_ids

    def test_excludes_self(self, analyzer, mock_note_manager):
        """Exclut la note elle-meme des resultats."""
        mock_note_manager.search_notes.return_value = [
            (MagicMock(note_id="test-note"), 1.0),  # Self with perfect match
            (MagicMock(note_id="similar"), 0.90),
        ]

        result = analyzer.detect_similar_notes("test-note", threshold=0.85)

        # Should exclude self
        note_ids = [note_id for note_id, _ in result]
        assert "test-note" not in note_ids
        assert "similar" in note_ids

    def test_returns_empty_when_no_similar(self, analyzer, mock_note_manager):
        """Retourne liste vide si pas de notes similaires."""
        mock_note_manager.search_notes.return_value = [
            (MagicMock(note_id="different-1"), 0.50),
            (MagicMock(note_id="different-2"), 0.30),
        ]

        result = analyzer.detect_similar_notes("test-note", threshold=0.85)

        assert len(result) == 0

    def test_handles_search_error(self, analyzer, mock_note_manager):
        """Gere les erreurs de recherche gracieusement."""
        mock_note_manager.search_notes.side_effect = Exception("Search error")

        result = analyzer.detect_similar_notes("test-note", threshold=0.85)

        # Should return empty list on error
        assert result == []


class TestAnalyzeWithAI:
    """Tests for analyze_with_ai method."""

    @pytest.mark.asyncio
    async def test_returns_actions(self, analyzer):
        """Retourne des actions basees sur l'analyse IA."""
        note_id = "test-note"
        note_title = "Test Note"
        content = "Some content"
        problems = [
            DetectedProblem(
                problem_type=ProblemType.EMPTY_SECTION,
                severity=Severity.MEDIUM,
                details="Section vide: ## References",
            )
        ]

        # Mock AI router response
        ai_response = """
{
    "actions": [
        {
            "action_type": "enrichissement",
            "confidence": 0.85,
            "reasoning": "La section References est vide"
        }
    ]
}
"""
        mock_router = MagicMock()
        mock_router.analyze_with_prompt_async = AsyncMock(
            return_value=(ai_response, {"total_tokens": 100})
        )

        with patch("src.sancho.router.get_ai_router", return_value=mock_router):
            actions = await analyzer.analyze_with_ai(
                note_id, note_title, content, problems
            )

        assert len(actions) >= 1
        assert actions[0].action_type == GrimaudActionType.ENRICHISSEMENT
        assert actions[0].note_id == note_id

    @pytest.mark.asyncio
    async def test_handles_ai_error(self, analyzer):
        """Gere les erreurs IA gracieusement."""
        mock_router = MagicMock()
        mock_router.analyze_with_prompt_async = AsyncMock(
            side_effect=Exception("AI error")
        )

        with patch("src.sancho.router.get_ai_router", return_value=mock_router):
            actions = await analyzer.analyze_with_ai(
                "note-id", "Title", "Content", []
            )

        # Should return empty list on error
        assert actions == []

    @pytest.mark.asyncio
    async def test_handles_invalid_json_response(self, analyzer):
        """Gere les reponses JSON invalides."""
        mock_router = MagicMock()
        mock_router.analyze_with_prompt_async = AsyncMock(
            return_value=("Invalid JSON response", {"total_tokens": 50})
        )

        with patch("src.sancho.router.get_ai_router", return_value=mock_router):
            actions = await analyzer.analyze_with_ai(
                "note-id", "Title", "Content", []
            )

        # Should return empty list on parse error
        assert actions == []

    @pytest.mark.asyncio
    async def test_handles_empty_actions_response(self, analyzer):
        """Gere les reponses sans actions."""
        mock_router = MagicMock()
        mock_router.analyze_with_prompt_async = AsyncMock(
            return_value=('{"actions": []}', {"total_tokens": 50})
        )

        with patch("src.sancho.router.get_ai_router", return_value=mock_router):
            actions = await analyzer.analyze_with_ai(
                "note-id", "Title", "Content", []
            )

        assert actions == []
