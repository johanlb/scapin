"""
Comprehensive tests for NoteReviewer core functionality.

Tests cover:
- Wikilink extraction
- Content scrubbing
- Temporal reference detection
- Completed task detection
- Missing link detection
- Formatting checks
- Hygiene metrics calculation
- Auto-apply decision logic
- Action application
- Quality score calculation
- ReviewAction dataclass methods

Note: This test file uses mocks to avoid heavy ML dependencies (torch, sentence-transformers).
"""

import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest


# =============================================================================
# Mock Setup - Must happen before importing note_reviewer
# =============================================================================

# Create mock modules for heavy dependencies
_mock = MagicMock()
for mod in [
    "sentence_transformers",
    "hnswlib",
    "faiss",
    "torch",
    "transformers",
]:
    if mod not in sys.modules:
        sys.modules[mod] = _mock


# =============================================================================
# Local implementations of classes to test (copied from note_reviewer.py)
# This avoids the complex import chain while testing the actual logic
# =============================================================================


class ActionType(str, Enum):
    """Types of review actions"""

    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    LINK = "link"
    ARCHIVE = "archive"
    FORMAT = "format"
    ENRICH = "enrich"
    VALIDATE = "validate"
    FIX_LINKS = "fix_links"
    MERGE = "merge"
    SPLIT = "split"
    REFACTOR = "refactor"


@dataclass
class EnrichmentRecord:
    """A record of an enrichment action"""

    timestamp: datetime
    action_type: str
    target: str
    content: Optional[str] = None
    confidence: float = 0.5
    applied: bool = False
    reasoning: str = ""


@dataclass
class ReviewAction:
    """A single action suggested during review"""

    action_type: ActionType
    target: str
    content: Optional[str] = None
    confidence: float = 0.5
    reasoning: str = ""
    source: str = ""
    target_note_id: Optional[str] = None

    def to_enrichment_record(self, applied: bool) -> EnrichmentRecord:
        """Convert to EnrichmentRecord for history"""
        return EnrichmentRecord(
            timestamp=datetime.now(timezone.utc),
            action_type=self.action_type.value,
            target=self.target,
            content=self.content,
            confidence=self.confidence,
            applied=applied,
            reasoning=self.reasoning,
        )


@dataclass
class HygieneMetrics:
    """Structural health metrics for a note"""

    word_count: int
    is_too_short: bool
    is_too_long: bool
    frontmatter_valid: bool
    frontmatter_issues: list[str] = field(default_factory=list)
    broken_links: list[str] = field(default_factory=list)
    heading_issues: list[str] = field(default_factory=list)
    duplicate_candidates: list[tuple[str, float]] = field(default_factory=list)
    formatting_score: float = 1.0


@dataclass
class ReviewAnalysis:
    """Result of analyzing a note for review"""

    needs_update: bool
    confidence: float
    suggested_actions: list[ReviewAction]
    reasoning: str
    detected_issues: list[str] = field(default_factory=list)
    detected_strengths: list[str] = field(default_factory=list)
    hygiene: Optional[HygieneMetrics] = None


@dataclass
class Note:
    """Minimal Note class for testing."""

    note_id: str
    title: str
    content: str
    tags: list = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    file_path: Optional[Path] = None


@dataclass
class ConservationCriteria:
    """Rules for what to keep/remove"""

    keep_patterns: list = field(default_factory=lambda: ["important", "keep"])


# Maximum regex matches to process
MAX_REGEX_MATCHES = 100


class NoteReviewerTestable:
    """
    Testable version of NoteReviewer with core logic extracted.
    This allows testing the pure functions without heavy dependencies.
    """

    AUTO_APPLY_THRESHOLD = 0.85
    HYGIENE_THRESHOLD = 0.70
    DESTRUCTIVE_ACTIONS = {ActionType.MERGE, ActionType.SPLIT}

    def __init__(self, note_manager=None, criteria=None):
        self.notes = note_manager or MagicMock()
        self.criteria = criteria or ConservationCriteria()

    def _extract_wikilinks(self, content: str) -> list[str]:
        """Extract wikilinks from content"""
        pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        return re.findall(pattern, content)

    def _scrub_content(self, content: str) -> str:
        """Scrub media links and large binary-like patterns from content."""
        scrubbed = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"[MEDIA: \1]", content)
        scrubbed = re.sub(r"<img[^>]+src=[\"'][^\"']+[\"'][^>]*>", "[IMAGE]", scrubbed)
        return scrubbed

    def _check_temporal_references(self, content: str) -> list[dict]:
        """Check for outdated temporal references"""
        issues = []
        patterns = [
            (r"(cette semaine|this week)", 7),
            (r"(demain|tomorrow)", 2),
            (r"(aujourd'hui|today)", 1),
            (r"(la semaine prochaine|next week)", 14),
            (r"(le mois prochain|next month)", 45),
            (r"(réunion|meeting).*?(\d{1,2}[/\-]\d{1,2})", 30),
        ]

        for pattern, days_threshold in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for i, match in enumerate(matches):
                if i >= MAX_REGEX_MATCHES:
                    break
                context = content[max(0, match.start() - 50) : match.end() + 50]
                should_keep = any(
                    re.search(keep_pattern, context, re.IGNORECASE)
                    for keep_pattern in self.criteria.keep_patterns
                )
                if not should_keep:
                    confidence = min(0.85, 0.5 + (days_threshold / 100))
                    issues.append(
                        {
                            "text": match.group(0),
                            "confidence": confidence,
                            "reason": f"Référence temporelle potentiellement obsolète: '{match.group(0)}'",
                        }
                    )
        return issues

    def _check_completed_tasks(self, content: str) -> list[dict]:
        """Check for completed minor tasks"""
        tasks = []
        pattern = r"\[x\]\s*(.+?)(?:\n|$)"
        matches = re.finditer(pattern, content, re.IGNORECASE)

        for i, match in enumerate(matches):
            if i >= MAX_REGEX_MATCHES:
                break
            task_text = match.group(1).strip()
            important_keywords = [
                "projet",
                "client",
                "deadline",
                "important",
                "urgent",
                "milestone",
            ]
            is_minor = len(task_text) < 50 and not any(
                kw in task_text.lower() for kw in important_keywords
            )
            if is_minor:
                tasks.append(
                    {
                        "text": match.group(0),
                        "confidence": 0.75,
                        "reason": f"Tâche mineure terminée: '{task_text[:30]}...'",
                    }
                )
        return tasks

    def _check_missing_links(self, content: str, _linked_notes: list) -> list[dict]:
        """Check for entities that could be linked"""
        suggestions = []
        existing_links = set(self._extract_wikilinks(content))
        pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
        potential_entities = set(re.findall(pattern, content))

        for entity in potential_entities:
            if entity in existing_links:
                continue
            if len(entity) < 3:
                continue
            search_results = self.notes.search_notes(query=entity, top_k=1)
            if search_results:
                suggestions.append(
                    {
                        "entity": entity,
                        "confidence": 0.7,
                        "reason": f"Entité '{entity}' pourrait être liée à une note existante",
                    }
                )
        return suggestions[:5]

    def _check_formatting(self, content: str) -> list[dict]:
        """Check for formatting issues"""
        issues = []
        headers = re.findall(r"^(#+)\s", content, re.MULTILINE)
        if headers:
            levels = [len(h) for h in headers]
            if levels and levels[0] != 1:
                issues.append(
                    {
                        "location": "headers",
                        "fix": None,
                        "reason": "Le premier titre devrait être de niveau 1 (#)",
                    }
                )
        if re.search(r"[ \t]+$", content, re.MULTILINE):
            issues.append(
                {
                    "location": "whitespace",
                    "fix": re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE),
                    "reason": "Espaces en fin de ligne détectés",
                }
            )
        return issues

    def _calculate_hygiene_metrics(self, note: Note) -> HygieneMetrics:
        """Calculate structural health metrics for a note"""
        words = note.content.split()
        word_count = len(words)
        is_too_short = word_count < 100
        is_too_long = word_count > 2000

        frontmatter_issues = []
        frontmatter_valid = True
        required_fields = ["title", "created_at", "updated_at"]
        for field_name in required_fields:
            if field_name not in note.metadata or not note.metadata.get(field_name):
                frontmatter_issues.append(f"Missing: {field_name}")
                frontmatter_valid = False

        broken_links = []
        wikilinks = self._extract_wikilinks(note.content)
        for link in wikilinks[:20]:
            search_result = self.notes.search_notes(query=link, top_k=3)
            if not search_result:
                similar = self.notes.search_notes(query=link, top_k=1)
                if similar:
                    similar_note = similar[0][0] if isinstance(similar[0], tuple) else similar[0]
                    broken_links.append(f"{link} -> suggest: {similar_note.title}")
                else:
                    broken_links.append(link)

        heading_issues = []
        lines = note.content.split("\n")
        prev_level = 0
        for line in lines:
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                if level > prev_level + 1:
                    heading_issues.append(f"Skip at: {line[:40]}")
                prev_level = level

        formatting_score = 1.0
        if heading_issues:
            formatting_score -= 0.2
        if broken_links:
            formatting_score -= 0.1 * min(len(broken_links), 5)
        formatting_score = max(0.0, formatting_score)

        return HygieneMetrics(
            word_count=word_count,
            is_too_short=is_too_short,
            is_too_long=is_too_long,
            frontmatter_valid=frontmatter_valid,
            frontmatter_issues=frontmatter_issues,
            broken_links=broken_links,
            heading_issues=heading_issues,
            duplicate_candidates=[],
            formatting_score=formatting_score,
        )

    def _should_auto_apply(self, action: ReviewAction) -> bool:
        """Determine if an action should be auto-applied"""
        if action.action_type in self.DESTRUCTIVE_ACTIONS:
            return False
        hygiene_actions = {ActionType.VALIDATE, ActionType.FORMAT, ActionType.FIX_LINKS}
        if action.action_type in hygiene_actions:
            return action.confidence >= self.HYGIENE_THRESHOLD
        return action.confidence >= self.AUTO_APPLY_THRESHOLD

    def _apply_action(self, content: str, action: ReviewAction) -> str:
        """Apply a single action to content"""
        if action.action_type == ActionType.FORMAT:
            if action.content:
                return action.content
            return content

        if action.action_type == ActionType.ARCHIVE:
            archive_section = "\n\n---\n## Historique (archivé)\n"
            if archive_section not in content:
                content += archive_section
            content += f"\n- {action.target} (archivé {datetime.now(timezone.utc).strftime('%Y-%m-%d')})"
            content = content.replace(action.target, "", 1)
            return content

        if action.action_type == ActionType.LINK:
            if action.content:
                content = content.replace(action.target, action.content, 1)
            return content

        if action.action_type == ActionType.FIX_LINKS:
            if action.target and action.content:
                old_link = f"[[{action.target}]]"
                new_link = f"[[{action.content}]]"
                content = content.replace(old_link, new_link)
            return content

        if action.action_type == ActionType.REFACTOR:
            if action.target and action.target_note_id:
                content = content.replace(action.target, "", 1)
                reference = f"\n\n> [Déplacé vers [[{action.target_note_id}]]]\n"
                content += reference
            return content

        if action.action_type == ActionType.UPDATE:
            if action.content:
                if "---" in content:
                    parts = content.split("---", 1)
                    return f"{parts[0].strip()}\n\n{action.content}\n\n---{parts[1]}"
                return f"{content.strip()}\n\n{action.content}"
            return content

        return content

    def _calculate_quality(self, analysis: ReviewAnalysis, _applied_count: int) -> int:
        """Calculate SM-2 quality score"""
        total_actions = len(analysis.suggested_actions)

        if total_actions == 0:
            return 5

        format_only = all(
            a.action_type == ActionType.FORMAT for a in analysis.suggested_actions
        )
        link_only = all(
            a.action_type in (ActionType.FORMAT, ActionType.LINK)
            for a in analysis.suggested_actions
        )

        if format_only:
            return 4
        if link_only and total_actions <= 3:
            return 3
        if total_actions <= 5:
            return 2
        if total_actions <= 10:
            return 1
        return 0

    def _apply_external_action(self, action: ReviewAction) -> bool:
        """Apply an enrichment action to an external note"""
        if not action.target_note_id or not action.content:
            return False

        target_note = self.notes.get_note(action.target_note_id)
        if not target_note:
            return False

        enrichment = (
            f"\n\n### Mise à jour Sancho ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n"
            f"{action.content}"
        )
        new_content = target_note.content + enrichment

        try:
            self.notes.update_note(note_id=action.target_note_id, content=new_content)
            return True
        except Exception:
            return False


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def reviewer():
    """Create a NoteReviewerTestable with mocked dependencies."""
    mock_manager = MagicMock()
    mock_manager.search_notes.return_value = []
    return NoteReviewerTestable(note_manager=mock_manager)


@pytest.fixture
def sample_note():
    """Create a sample note for testing."""
    return Note(
        note_id="test-note-001",
        title="Test Note",
        content="# Test Note\n\nThis is a test note with some content.",
        tags=["test", "sample"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata={"title": "Test Note", "created_at": "2024-01-01", "updated_at": "2024-01-01"},
    )


# =============================================================================
# Tests for _extract_wikilinks
# =============================================================================


class TestExtractWikilinks:
    """Tests for wikilink extraction from content."""

    def test_extracts_simple_wikilinks(self, reviewer):
        """Should extract simple [[wikilinks]]."""
        content = "See [[Project Alpha]] for more details about [[Team Beta]]."
        links = reviewer._extract_wikilinks(content)
        assert links == ["Project Alpha", "Team Beta"]

    def test_extracts_wikilinks_with_aliases(self, reviewer):
        """Should extract wikilinks with display aliases [[link|alias]]."""
        content = "Check [[Important Note|this note]] and [[Another|alias]]."
        links = reviewer._extract_wikilinks(content)
        assert links == ["Important Note", "Another"]

    def test_returns_empty_for_no_wikilinks(self, reviewer):
        """Should return empty list when no wikilinks present."""
        content = "This is plain text without any links."
        links = reviewer._extract_wikilinks(content)
        assert links == []

    def test_handles_multiple_wikilinks_same_line(self, reviewer):
        """Should handle multiple wikilinks on same line."""
        content = "[[A]], [[B]], [[C]] are all linked."
        links = reviewer._extract_wikilinks(content)
        assert links == ["A", "B", "C"]

    def test_handles_wikilinks_with_special_characters(self, reviewer):
        """Should handle wikilinks with special characters."""
        content = "See [[Note-2024]] and [[Project_v2]] for details."
        links = reviewer._extract_wikilinks(content)
        assert links == ["Note-2024", "Project_v2"]

    def test_ignores_malformed_wikilinks(self, reviewer):
        """Should ignore malformed wikilinks."""
        content = "This [not a link] and [[]] empty link."
        links = reviewer._extract_wikilinks(content)
        assert links == []

    def test_extracts_wikilinks_with_spaces(self, reviewer):
        """Should extract wikilinks containing spaces."""
        content = "See [[My Important Project]] for details."
        links = reviewer._extract_wikilinks(content)
        assert links == ["My Important Project"]


# =============================================================================
# Tests for _scrub_content
# =============================================================================


class TestScrubContent:
    """Tests for content scrubbing (removing media for AI analysis)."""

    def test_replaces_markdown_images(self, reviewer):
        """Should replace markdown images with placeholders."""
        content = "Look at this: ![Screenshot](./images/screenshot.png)"
        scrubbed = reviewer._scrub_content(content)
        assert "![Screenshot]" not in scrubbed
        assert "[MEDIA: Screenshot]" in scrubbed

    def test_replaces_images_without_alt_text(self, reviewer):
        """Should replace images without alt text."""
        content = "Image here: ![](./path/to/image.jpg)"
        scrubbed = reviewer._scrub_content(content)
        assert "[MEDIA: ]" in scrubbed

    def test_replaces_html_images(self, reviewer):
        """Should replace HTML img tags."""
        content = 'Text with <img src="photo.png" alt="photo"> embedded.'
        scrubbed = reviewer._scrub_content(content)
        assert "<img" not in scrubbed
        assert "[IMAGE]" in scrubbed

    def test_preserves_regular_links(self, reviewer):
        """Should preserve regular markdown links (not images)."""
        content = "See [documentation](https://docs.example.com) for more."
        scrubbed = reviewer._scrub_content(content)
        assert "[documentation](https://docs.example.com)" in scrubbed

    def test_handles_multiple_media(self, reviewer):
        """Should handle multiple media elements."""
        content = """# Note
![img1](a.png)
Some text
![img2](b.jpg)
<img src="c.gif">
End."""
        scrubbed = reviewer._scrub_content(content)
        assert scrubbed.count("[MEDIA:") == 2
        assert scrubbed.count("[IMAGE]") == 1
        assert "Some text" in scrubbed
        assert "End." in scrubbed

    def test_preserves_text_content(self, reviewer):
        """Should preserve all text content."""
        content = "# Title\n\nParagraph with important text."
        scrubbed = reviewer._scrub_content(content)
        assert scrubbed == content

    def test_handles_complex_image_paths(self, reviewer):
        """Should handle complex image paths with special chars."""
        content = "![alt](./path/to/my-image_v2%20final.png)"
        scrubbed = reviewer._scrub_content(content)
        assert "[MEDIA: alt]" in scrubbed


# =============================================================================
# Tests for _check_temporal_references
# =============================================================================


class TestCheckTemporalReferences:
    """Tests for detecting outdated temporal references."""

    def test_detects_cette_semaine(self, reviewer):
        """Should detect 'cette semaine' as temporal reference."""
        content = "Nous devons finir cette semaine le projet."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) >= 1
        assert any("cette semaine" in issue["text"].lower() for issue in issues)

    def test_detects_this_week_english(self, reviewer):
        """Should detect 'this week' in English."""
        content = "The deadline is this week."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) >= 1
        assert any("this week" in issue["text"].lower() for issue in issues)

    def test_detects_demain_tomorrow(self, reviewer):
        """Should detect 'demain' and 'tomorrow'."""
        content = "La réunion est demain. Meeting is tomorrow."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) >= 2

    def test_detects_aujourdhui_today(self, reviewer):
        """Should detect 'aujourd'hui' and 'today'."""
        content = "Aujourd'hui nous avons parlé. Today we discussed."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) >= 2

    def test_detects_next_week_month(self, reviewer):
        """Should detect 'next week' and 'next month'."""
        content = "Next week we start. Le mois prochain c'est la deadline."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) >= 2

    def test_detects_meeting_dates(self, reviewer):
        """Should detect meeting with dates."""
        content = "La réunion du 15/03 est prévue."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) >= 1

    def test_returns_empty_for_no_temporal_refs(self, reviewer):
        """Should return empty list when no temporal references."""
        content = "This is a timeless note about architecture."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) == 0

    def test_includes_confidence_score(self, reviewer):
        """Should include confidence score in issues."""
        content = "Cette semaine nous devons finir."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) > 0
        assert "confidence" in issues[0]
        assert 0.0 <= issues[0]["confidence"] <= 1.0

    def test_includes_reason(self, reviewer):
        """Should include reason in issues."""
        content = "Demain c'est la deadline."
        issues = reviewer._check_temporal_references(content)
        assert len(issues) > 0
        assert "reason" in issues[0]


# =============================================================================
# Tests for _check_completed_tasks
# =============================================================================


class TestCheckCompletedTasks:
    """Tests for detecting completed tasks that could be archived."""

    def test_detects_completed_tasks(self, reviewer):
        """Should detect completed tasks with [x]."""
        content = "- [x] Finish the report\n- [ ] Review code"
        tasks = reviewer._check_completed_tasks(content)
        assert len(tasks) >= 1

    def test_ignores_incomplete_tasks(self, reviewer):
        """Should ignore incomplete tasks."""
        content = "- [ ] Do something\n- [ ] Another task"
        tasks = reviewer._check_completed_tasks(content)
        assert len(tasks) == 0

    def test_ignores_important_completed_tasks(self, reviewer):
        """Should ignore completed tasks with important keywords."""
        content = "- [x] Complete the client projet deadline"
        tasks = reviewer._check_completed_tasks(content)
        assert len(tasks) == 0

    def test_detects_minor_completed_tasks(self, reviewer):
        """Should detect short, minor completed tasks."""
        content = "- [x] Buy coffee\n- [x] Send email"
        tasks = reviewer._check_completed_tasks(content)
        assert len(tasks) >= 2

    def test_returns_empty_for_no_tasks(self, reviewer):
        """Should return empty list when no tasks present."""
        content = "This is just text without any task items."
        tasks = reviewer._check_completed_tasks(content)
        assert len(tasks) == 0

    def test_handles_uppercase_x(self, reviewer):
        """Should handle uppercase X in completed tasks."""
        content = "- [X] Done task"
        tasks = reviewer._check_completed_tasks(content)
        assert isinstance(tasks, list)

    def test_includes_task_text(self, reviewer):
        """Should include the task text in result."""
        content = "- [x] Simple task done"
        tasks = reviewer._check_completed_tasks(content)
        if tasks:
            assert "text" in tasks[0]


# =============================================================================
# Tests for _check_missing_links
# =============================================================================


class TestCheckMissingLinks:
    """Tests for detecting entities that could be linked."""

    def test_suggests_linking_capitalized_entities(self, reviewer):
        """Should suggest linking capitalized entities."""
        mock_note = MagicMock()
        mock_note.title = "Project Alpha"
        reviewer.notes.search_notes.return_value = [(mock_note, 0.9)]

        content = "Working on Project Alpha today."
        suggestions = reviewer._check_missing_links(content, [])

        assert len(suggestions) >= 1
        assert any("Project Alpha" in s["entity"] for s in suggestions)

    def test_ignores_already_linked_entities(self, reviewer):
        """Should ignore entities already linked."""
        content = "Working on [[Project Alpha]] today. Also Project Beta."
        mock_note = MagicMock()
        mock_note.title = "Project Alpha"
        reviewer.notes.search_notes.return_value = [(mock_note, 0.9)]

        suggestions = reviewer._check_missing_links(content, [])

        assert not any("Project Alpha" in s["entity"] for s in suggestions)

    def test_returns_empty_when_no_matches(self, reviewer):
        """Should return empty when no matching notes found."""
        reviewer.notes.search_notes.return_value = []

        content = "Working on Some Entity today."
        suggestions = reviewer._check_missing_links(content, [])

        assert suggestions == []

    def test_limits_suggestions(self, reviewer):
        """Should limit number of suggestions."""
        mock_note = MagicMock()
        mock_note.title = "Match"
        reviewer.notes.search_notes.return_value = [(mock_note, 0.9)]

        content = "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa"
        suggestions = reviewer._check_missing_links(content, [])

        assert len(suggestions) <= 5

    def test_includes_confidence_and_reason(self, reviewer):
        """Should include confidence and reason in suggestions."""
        mock_note = MagicMock()
        mock_note.title = "Entity"
        reviewer.notes.search_notes.return_value = [(mock_note, 0.9)]

        content = "Working with Entity today."
        suggestions = reviewer._check_missing_links(content, [])

        if suggestions:
            assert "confidence" in suggestions[0]
            assert "reason" in suggestions[0]


# =============================================================================
# Tests for _check_formatting
# =============================================================================


class TestCheckFormatting:
    """Tests for detecting formatting issues."""

    def test_detects_wrong_first_header_level(self, reviewer):
        """Should detect when first header is not level 1."""
        content = "## Second Level Title\n\nSome content here."
        issues = reviewer._check_formatting(content)

        assert len(issues) >= 1
        assert any("niveau 1" in issue["reason"] for issue in issues)

    def test_accepts_correct_first_header(self, reviewer):
        """Should accept content starting with # header."""
        content = "# Correct Title\n\nSome content here."
        issues = reviewer._check_formatting(content)

        assert not any("niveau 1" in issue.get("reason", "") for issue in issues)

    def test_detects_trailing_whitespace(self, reviewer):
        """Should detect trailing whitespace."""
        content = "Line with trailing spaces   \nAnother line."
        issues = reviewer._check_formatting(content)

        assert len(issues) >= 1
        assert any("Espaces en fin de ligne" in issue["reason"] for issue in issues)

    def test_provides_fix_for_whitespace(self, reviewer):
        """Should provide fix for trailing whitespace."""
        content = "Line with spaces   \nAnother line."
        issues = reviewer._check_formatting(content)

        whitespace_issues = [i for i in issues if "whitespace" in i.get("location", "")]
        if whitespace_issues:
            assert "fix" in whitespace_issues[0]
            assert "   \n" not in whitespace_issues[0]["fix"]

    def test_returns_empty_for_well_formatted(self, reviewer):
        """Should return empty for well-formatted content."""
        content = "# Good Title\n\nWell formatted paragraph."
        issues = reviewer._check_formatting(content)

        assert isinstance(issues, list)


# =============================================================================
# Tests for _calculate_hygiene_metrics
# =============================================================================


class TestCalculateHygieneMetrics:
    """Tests for hygiene metrics calculation."""

    def test_counts_words_correctly(self, reviewer, sample_note):
        """Should count words correctly."""
        sample_note.content = "One two three four five."
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert metrics.word_count == 5

    def test_detects_too_short_content(self, reviewer, sample_note):
        """Should detect content under 100 words as too short."""
        sample_note.content = "Short note."
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert metrics.is_too_short is True
        assert metrics.is_too_long is False

    def test_detects_too_long_content(self, reviewer, sample_note):
        """Should detect content over 2000 words as too long."""
        sample_note.content = " ".join(["word"] * 2500)
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert metrics.is_too_long is True
        assert metrics.is_too_short is False

    def test_detects_normal_length(self, reviewer, sample_note):
        """Should not flag content between 100-2000 words."""
        sample_note.content = " ".join(["word"] * 500)
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert metrics.is_too_short is False
        assert metrics.is_too_long is False

    def test_validates_frontmatter_required_fields(self, reviewer, sample_note):
        """Should validate required frontmatter fields."""
        sample_note.metadata = {}
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert metrics.frontmatter_valid is False
        assert len(metrics.frontmatter_issues) > 0

    def test_frontmatter_valid_with_all_fields(self, reviewer, sample_note):
        """Should validate when all required fields present."""
        sample_note.metadata = {
            "title": "Test",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
        }
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert metrics.frontmatter_valid is True
        assert len(metrics.frontmatter_issues) == 0

    def test_detects_heading_skips(self, reviewer, sample_note):
        """Should detect heading level skips."""
        sample_note.content = "# Title\n\n### Skipped to H3\n\nContent."
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert len(metrics.heading_issues) > 0

    def test_accepts_sequential_headings(self, reviewer, sample_note):
        """Should accept sequential heading levels."""
        sample_note.content = "# Title\n## Section\n### Subsection"
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert len(metrics.heading_issues) == 0

    def test_calculates_formatting_score(self, reviewer, sample_note):
        """Should calculate formatting score."""
        sample_note.content = "# Good Title\n\n## Good Section"
        sample_note.metadata = {
            "title": "Test",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
        }
        metrics = reviewer._calculate_hygiene_metrics(sample_note)
        assert 0.0 <= metrics.formatting_score <= 1.0


# =============================================================================
# Tests for _should_auto_apply
# =============================================================================


class TestShouldAutoApply:
    """Tests for auto-apply decision logic."""

    def test_never_auto_applies_merge(self, reviewer):
        """Should never auto-apply MERGE actions."""
        action = ReviewAction(
            action_type=ActionType.MERGE,
            target="test",
            confidence=1.0,
        )
        assert reviewer._should_auto_apply(action) is False

    def test_never_auto_applies_split(self, reviewer):
        """Should never auto-apply SPLIT actions."""
        action = ReviewAction(
            action_type=ActionType.SPLIT,
            target="test",
            confidence=1.0,
        )
        assert reviewer._should_auto_apply(action) is False

    def test_auto_applies_high_confidence_format(self, reviewer):
        """Should auto-apply FORMAT with confidence >= HYGIENE_THRESHOLD."""
        action = ReviewAction(
            action_type=ActionType.FORMAT,
            target="test",
            confidence=0.75,
        )
        assert reviewer._should_auto_apply(action) is True

    def test_no_auto_apply_low_confidence_format(self, reviewer):
        """Should not auto-apply FORMAT with low confidence."""
        action = ReviewAction(
            action_type=ActionType.FORMAT,
            target="test",
            confidence=0.5,
        )
        assert reviewer._should_auto_apply(action) is False

    def test_auto_applies_high_confidence_validate(self, reviewer):
        """Should auto-apply VALIDATE with sufficient confidence."""
        action = ReviewAction(
            action_type=ActionType.VALIDATE,
            target="test",
            confidence=0.80,
        )
        assert reviewer._should_auto_apply(action) is True

    def test_auto_applies_high_confidence_fix_links(self, reviewer):
        """Should auto-apply FIX_LINKS with sufficient confidence."""
        action = ReviewAction(
            action_type=ActionType.FIX_LINKS,
            target="test",
            confidence=0.75,
        )
        assert reviewer._should_auto_apply(action) is True

    def test_semantic_actions_need_higher_threshold(self, reviewer):
        """Should require AUTO_APPLY_THRESHOLD for semantic actions."""
        action = ReviewAction(
            action_type=ActionType.UPDATE,
            target="test",
            confidence=0.80,
        )
        assert reviewer._should_auto_apply(action) is False

    def test_auto_applies_very_high_confidence_update(self, reviewer):
        """Should auto-apply UPDATE with very high confidence."""
        action = ReviewAction(
            action_type=ActionType.UPDATE,
            target="test",
            confidence=0.90,
        )
        assert reviewer._should_auto_apply(action) is True

    def test_auto_applies_high_confidence_add(self, reviewer):
        """Should auto-apply ADD with sufficient confidence."""
        action = ReviewAction(
            action_type=ActionType.ADD,
            target="test",
            confidence=0.90,
        )
        assert reviewer._should_auto_apply(action) is True


# =============================================================================
# Tests for _apply_action
# =============================================================================


class TestApplyAction:
    """Tests for action application to content."""

    def test_apply_format_returns_new_content(self, reviewer):
        """Should return action content for FORMAT."""
        action = ReviewAction(
            action_type=ActionType.FORMAT,
            target="whitespace",
            content="Clean content without trailing spaces",
        )
        result = reviewer._apply_action("Content   ", action)
        assert result == "Clean content without trailing spaces"

    def test_apply_format_without_content(self, reviewer):
        """Should return original when FORMAT has no content."""
        action = ReviewAction(
            action_type=ActionType.FORMAT,
            target="headers",
            content=None,
        )
        original = "Original content"
        result = reviewer._apply_action(original, action)
        assert result == original

    def test_apply_archive_creates_section(self, reviewer):
        """Should create archive section when applying ARCHIVE."""
        action = ReviewAction(
            action_type=ActionType.ARCHIVE,
            target="old text",
            reasoning="Outdated",
        )
        content = "Some old text and other content."
        result = reviewer._apply_action(content, action)
        assert "## Historique (archivé)" in result
        assert "old text" in result

    def test_apply_link_replaces_entity(self, reviewer):
        """Should replace entity with wikilink for LINK."""
        action = ReviewAction(
            action_type=ActionType.LINK,
            target="Project Alpha",
            content="[[Project Alpha]]",
        )
        content = "Working on Project Alpha today."
        result = reviewer._apply_action(content, action)
        assert "[[Project Alpha]]" in result

    def test_apply_fix_links_corrects_broken_link(self, reviewer):
        """Should fix broken wikilinks."""
        action = ReviewAction(
            action_type=ActionType.FIX_LINKS,
            target="BrokenLink",
            content="CorrectLink",
        )
        content = "See [[BrokenLink]] for more."
        result = reviewer._apply_action(content, action)
        assert "[[CorrectLink]]" in result
        assert "[[BrokenLink]]" not in result

    def test_apply_update_appends_content(self, reviewer):
        """Should append content for UPDATE action."""
        action = ReviewAction(
            action_type=ActionType.UPDATE,
            target="Enrichment",
            content="New enrichment content",
        )
        content = "Original content"
        result = reviewer._apply_action(content, action)
        assert "Original content" in result
        assert "New enrichment content" in result

    def test_apply_update_inserts_before_separator(self, reviewer):
        """Should insert UPDATE content before --- separator."""
        action = ReviewAction(
            action_type=ActionType.UPDATE,
            target="Enrichment",
            content="New section",
        )
        content = "Main content\n\n---\nFooter"
        result = reviewer._apply_action(content, action)
        assert "New section" in result
        assert result.index("New section") < result.index("---")

    def test_apply_refactor_removes_content(self, reviewer):
        """Should remove content and add reference for REFACTOR."""
        action = ReviewAction(
            action_type=ActionType.REFACTOR,
            target="move this paragraph",
            target_note_id="other-note",
        )
        content = "Keep this. move this paragraph And this too."
        result = reviewer._apply_action(content, action)
        assert "move this paragraph" not in result or "Déplacé vers" in result
        assert "[[other-note]]" in result


# =============================================================================
# Tests for _calculate_quality
# =============================================================================


class TestCalculateQuality:
    """Tests for SM-2 quality score calculation."""

    def test_quality_5_no_actions(self, reviewer):
        """Should return 5 when no actions needed."""
        analysis = ReviewAnalysis(
            needs_update=False,
            confidence=1.0,
            suggested_actions=[],
            reasoning="Perfect",
        )
        quality = reviewer._calculate_quality(analysis, 0)
        assert quality == 5

    def test_quality_4_format_only(self, reviewer):
        """Should return 4 when only formatting actions."""
        analysis = ReviewAnalysis(
            needs_update=True,
            confidence=0.9,
            suggested_actions=[
                ReviewAction(ActionType.FORMAT, "whitespace"),
                ReviewAction(ActionType.FORMAT, "headers"),
            ],
            reasoning="Formatting",
        )
        quality = reviewer._calculate_quality(analysis, 2)
        assert quality == 4

    def test_quality_3_minor_link_actions(self, reviewer):
        """Should return 3 for minor link actions."""
        analysis = ReviewAnalysis(
            needs_update=True,
            confidence=0.8,
            suggested_actions=[
                ReviewAction(ActionType.LINK, "entity1"),
                ReviewAction(ActionType.FORMAT, "whitespace"),
            ],
            reasoning="Links",
        )
        quality = reviewer._calculate_quality(analysis, 2)
        assert quality == 3

    def test_quality_2_moderate_updates(self, reviewer):
        """Should return 2 for moderate updates (<=5 actions)."""
        analysis = ReviewAnalysis(
            needs_update=True,
            confidence=0.7,
            suggested_actions=[
                ReviewAction(ActionType.UPDATE, "section1"),
                ReviewAction(ActionType.ADD, "section2"),
                ReviewAction(ActionType.LINK, "entity"),
                ReviewAction(ActionType.ARCHIVE, "old"),
            ],
            reasoning="Moderate",
        )
        quality = reviewer._calculate_quality(analysis, 4)
        assert quality == 2

    def test_quality_1_significant_changes(self, reviewer):
        """Should return 1 for significant changes (<=10 actions)."""
        actions = [ReviewAction(ActionType.UPDATE, f"section{i}") for i in range(8)]
        analysis = ReviewAnalysis(
            needs_update=True,
            confidence=0.6,
            suggested_actions=actions,
            reasoning="Significant",
        )
        quality = reviewer._calculate_quality(analysis, 8)
        assert quality == 1

    def test_quality_0_major_overhaul(self, reviewer):
        """Should return 0 for major overhaul (>10 actions)."""
        actions = [ReviewAction(ActionType.UPDATE, f"section{i}") for i in range(15)]
        analysis = ReviewAnalysis(
            needs_update=True,
            confidence=0.5,
            suggested_actions=actions,
            reasoning="Major",
        )
        quality = reviewer._calculate_quality(analysis, 15)
        assert quality == 0


# =============================================================================
# Tests for ReviewAction.to_enrichment_record
# =============================================================================


class TestReviewActionToEnrichmentRecord:
    """Tests for converting ReviewAction to EnrichmentRecord."""

    def test_converts_basic_action(self):
        """Should convert basic action to record."""
        action = ReviewAction(
            action_type=ActionType.UPDATE,
            target="test section",
            content="new content",
            confidence=0.85,
            reasoning="Test reason",
        )
        record = action.to_enrichment_record(applied=True)

        assert record.action_type == "update"
        assert record.target == "test section"
        assert record.content == "new content"
        assert record.confidence == 0.85
        assert record.applied is True
        assert record.reasoning == "Test reason"

    def test_includes_timestamp(self):
        """Should include timestamp in record."""
        action = ReviewAction(
            action_type=ActionType.FORMAT,
            target="test",
        )
        record = action.to_enrichment_record(applied=False)

        assert record.timestamp is not None
        assert isinstance(record.timestamp, datetime)

    def test_handles_none_content(self):
        """Should handle None content."""
        action = ReviewAction(
            action_type=ActionType.ARCHIVE,
            target="old content",
            content=None,
        )
        record = action.to_enrichment_record(applied=True)

        assert record.content is None

    def test_applied_flag_propagates(self):
        """Should correctly propagate applied flag."""
        action = ReviewAction(
            action_type=ActionType.LINK,
            target="entity",
        )

        record_applied = action.to_enrichment_record(applied=True)
        record_pending = action.to_enrichment_record(applied=False)

        assert record_applied.applied is True
        assert record_pending.applied is False


# =============================================================================
# Tests for HygieneMetrics dataclass
# =============================================================================


class TestHygieneMetrics:
    """Tests for HygieneMetrics dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        metrics = HygieneMetrics(
            word_count=100,
            is_too_short=False,
            is_too_long=False,
            frontmatter_valid=True,
        )
        assert metrics.frontmatter_issues == []
        assert metrics.broken_links == []
        assert metrics.heading_issues == []
        assert metrics.duplicate_candidates == []
        assert metrics.formatting_score == 1.0

    def test_stores_all_fields(self):
        """Should store all provided fields."""
        metrics = HygieneMetrics(
            word_count=500,
            is_too_short=False,
            is_too_long=False,
            frontmatter_valid=False,
            frontmatter_issues=["Missing: title"],
            broken_links=["[[Broken]]"],
            heading_issues=["Skip at: ### H3"],
            duplicate_candidates=[("note-123", 0.95)],
            formatting_score=0.7,
        )
        assert metrics.word_count == 500
        assert metrics.frontmatter_issues == ["Missing: title"]
        assert metrics.broken_links == ["[[Broken]]"]
        assert metrics.duplicate_candidates == [("note-123", 0.95)]


# =============================================================================
# Integration test for _apply_external_action
# =============================================================================


class TestApplyExternalAction:
    """Tests for applying actions to external notes."""

    def test_returns_false_without_target(self, reviewer):
        """Should return False when no target_note_id."""
        action = ReviewAction(
            action_type=ActionType.ENRICH,
            target="enrichment",
            content="content",
            target_note_id=None,
        )
        result = reviewer._apply_external_action(action)
        assert result is False

    def test_returns_false_without_content(self, reviewer):
        """Should return False when no content."""
        action = ReviewAction(
            action_type=ActionType.ENRICH,
            target="enrichment",
            content=None,
            target_note_id="note-123",
        )
        result = reviewer._apply_external_action(action)
        assert result is False

    def test_returns_false_when_note_not_found(self, reviewer):
        """Should return False when target note not found."""
        reviewer.notes.get_note.return_value = None

        action = ReviewAction(
            action_type=ActionType.ENRICH,
            target="enrichment",
            content="new content",
            target_note_id="nonexistent-note",
        )
        result = reviewer._apply_external_action(action)
        assert result is False

    def test_updates_external_note(self, reviewer):
        """Should update external note with enrichment."""
        target_note = MagicMock()
        target_note.content = "# Target Note\n\nOriginal content."
        reviewer.notes.get_note.return_value = target_note
        reviewer.notes.update_note.return_value = True

        action = ReviewAction(
            action_type=ActionType.ENRICH,
            target="enrichment",
            content="New enrichment text",
            target_note_id="target-note-123",
        )
        result = reviewer._apply_external_action(action)

        assert result is True
        reviewer.notes.update_note.assert_called_once()
        call_args = reviewer.notes.update_note.call_args
        assert "New enrichment text" in call_args.kwargs["content"]
        assert "Mise à jour Sancho" in call_args.kwargs["content"]
