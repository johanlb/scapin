"""
Tests for OmniFocus Duplicate Detection

Tests the coherence pass functionality that checks for duplicate tasks
before creating new ones in OmniFocus.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.apple.omnifocus import (
    DuplicateCheckResult,
    OmniFocusClient,
    OmniFocusTask,
)


@pytest.fixture
def client():
    """Create OmniFocus client for testing."""
    return OmniFocusClient(default_project="Inbox")


class TestDuplicateCheckResult:
    """Tests for DuplicateCheckResult dataclass."""

    def test_not_duplicate(self):
        """Test creating a non-duplicate result."""
        result = DuplicateCheckResult(
            is_duplicate=False,
            reason="No similar tasks found"
        )
        assert not result.is_duplicate
        assert result.existing_task is None
        assert result.similarity_score == 0.0

    def test_duplicate_with_task(self):
        """Test creating a duplicate result with existing task."""
        existing = OmniFocusTask(
            task_id="abc123",
            title="Répondre à Marc",
            project="Communications",
        )
        result = DuplicateCheckResult(
            is_duplicate=True,
            existing_task=existing,
            similarity_score=0.95,
            reason="Similar task found"
        )
        assert result.is_duplicate
        assert result.existing_task.title == "Répondre à Marc"
        assert result.similarity_score == 0.95


class TestKeywordExtraction:
    """Tests for keyword extraction from task titles."""

    def test_extract_keywords_basic(self, client):
        """Test basic keyword extraction."""
        keywords = client._extract_keywords("Répondre à Marc Dupont")
        assert "répondre" in keywords
        assert "marc" in keywords
        assert "dupont" in keywords
        # Stop words should be filtered
        assert "à" not in keywords

    def test_extract_keywords_removes_stop_words(self, client):
        """Test that stop words are filtered."""
        keywords = client._extract_keywords("Faire le rapport pour la réunion")
        assert "rapport" in keywords
        assert "réunion" in keywords
        # Stop words should be removed
        assert "le" not in keywords
        assert "pour" not in keywords
        assert "la" not in keywords

    def test_extract_keywords_english(self, client):
        """Test English stop word filtering."""
        keywords = client._extract_keywords("Send the report to the client")
        assert "send" in keywords
        assert "report" in keywords
        assert "client" in keywords
        # Stop words
        assert "the" not in keywords
        assert "to" not in keywords

    def test_extract_keywords_sorted_by_length(self, client):
        """Test keywords are sorted by length (longest first)."""
        keywords = client._extract_keywords("Développement application mobile")
        # Longer words should come first
        assert keywords[0] == "développement"
        assert keywords[1] == "application"
        assert keywords[2] == "mobile"

    def test_extract_keywords_filters_short_words(self, client):
        """Test that very short words are filtered."""
        keywords = client._extract_keywords("Do it by 5pm")
        # Short words (< 3 chars) should be filtered
        assert "do" not in keywords
        assert "it" not in keywords
        assert "by" not in keywords


class TestTokenSimilarity:
    """Tests for token-based similarity calculation."""

    def test_identical_strings(self, client):
        """Test similarity of identical strings."""
        score = client._token_similarity(
            "répondre marc dupont",
            "répondre marc dupont"
        )
        assert score == 1.0

    def test_completely_different(self, client):
        """Test similarity of completely different strings."""
        score = client._token_similarity(
            "répondre marc",
            "envoyer rapport"
        )
        assert score == 0.0

    def test_partial_overlap(self, client):
        """Test similarity with partial overlap."""
        score = client._token_similarity(
            "répondre marc dupont",
            "appeler marc dupont"
        )
        # 2 out of 4 unique tokens overlap
        assert 0.4 < score < 0.6

    def test_empty_string(self, client):
        """Test similarity with empty string."""
        score = client._token_similarity("", "some text")
        assert score == 0.0


class TestCalculateSimilarity:
    """Tests for overall similarity calculation."""

    def test_identical_task(self, client):
        """Test similarity of identical tasks."""
        score = client._calculate_similarity(
            title1="Répondre à Marc",
            title2="Répondre à Marc",
            due1="2026-01-20",
            due2=datetime(2026, 1, 20),
            project1="Communications",
            project2="Communications"
        )
        # Should be ~1.0 (title:0.7*1 + due:0.2*1 + project:0.1*1)
        assert score > 0.95

    def test_same_title_different_date(self, client):
        """Test same title but different due date."""
        score = client._calculate_similarity(
            title1="Répondre à Marc",
            title2="Répondre à Marc",
            due1="2026-01-20",
            due2=datetime(2026, 2, 15),  # Different date
            project1=None,
            project2=None
        )
        # Title match only: 0.7 * 1.0 = 0.7
        assert 0.65 < score < 0.75

    def test_similar_title_same_date(self, client):
        """Test similar title with same due date."""
        score = client._calculate_similarity(
            title1="Répondre à Marc Dupont",
            title2="Répondre à Marc",  # Similar but not identical
            due1="2026-01-20",
            due2=datetime(2026, 1, 20),
            project1=None,
            project2=None
        )
        # Partial title match + date match
        assert 0.5 < score < 0.9

    def test_no_dates(self, client):
        """Test with no due dates."""
        score = client._calculate_similarity(
            title1="Répondre à Marc",
            title2="Répondre à Marc",
            due1=None,
            due2=None,
            project1=None,
            project2=None
        )
        # Title only: 0.7 * 1.0 = 0.7
        assert 0.65 < score < 0.75


class TestCheckDuplicate:
    """Tests for check_duplicate method."""

    @pytest.mark.asyncio
    async def test_omnifocus_not_available(self, client):
        """Test when OmniFocus is not available."""
        client._is_available = False

        result = await client.check_duplicate("Some task")

        assert not result.is_duplicate
        assert "not available" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_no_keywords_extracted(self, client):
        """Test with title that has no meaningful keywords."""
        client._is_available = True

        with patch.object(client, '_extract_keywords', return_value=[]):
            result = await client.check_duplicate("a b c")

        assert not result.is_duplicate
        assert "no keywords" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_no_matches_found(self, client):
        """Test when no similar tasks are found."""
        client._is_available = True

        with patch.object(client, 'search_tasks', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            result = await client.check_duplicate("Nouvelle tâche unique")

        assert not result.is_duplicate
        assert "no similar" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_duplicate_found(self, client):
        """Test when a duplicate is found."""
        client._is_available = True
        existing_task = OmniFocusTask(
            task_id="existing-123",
            title="Répondre à Marc Dupont",
            project="Communications",
            due_date=datetime(2026, 1, 20),
        )

        with patch.object(client, 'search_tasks', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [existing_task]

            result = await client.check_duplicate(
                title="Répondre à Marc Dupont",
                due_date="2026-01-20",
                project="Communications"
            )

        assert result.is_duplicate
        assert result.existing_task is not None
        assert result.existing_task.task_id == "existing-123"
        assert result.similarity_score > 0.8

    @pytest.mark.asyncio
    async def test_similar_but_below_threshold(self, client):
        """Test when task is similar but below threshold."""
        client._is_available = True
        existing_task = OmniFocusTask(
            task_id="existing-123",
            title="Complètement différent",  # Very different title
            project="Autre",
        )

        with patch.object(client, 'search_tasks', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [existing_task]

            result = await client.check_duplicate(
                title="Répondre à Marc",
                similarity_threshold=0.8
            )

        assert not result.is_duplicate


class TestCreateTaskIfNotDuplicate:
    """Tests for create_task_if_not_duplicate method."""

    @pytest.mark.asyncio
    async def test_creates_when_no_duplicate(self, client):
        """Test task is created when no duplicate exists."""
        client._is_available = True

        with patch.object(client, 'check_duplicate', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = DuplicateCheckResult(
                is_duplicate=False,
                reason="No duplicate found"
            )
            with patch.object(client, 'create_task', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = OmniFocusTask(
                    task_id="new-123",
                    title="Nouvelle tâche"
                )

                task, check_result = await client.create_task_if_not_duplicate(
                    title="Nouvelle tâche"
                )

        assert task is not None
        assert task.task_id == "new-123"
        assert not check_result.is_duplicate
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_duplicate(self, client):
        """Test task is NOT created when duplicate exists."""
        client._is_available = True
        existing = OmniFocusTask(task_id="existing-123", title="Tâche existante")

        with patch.object(client, 'check_duplicate', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = DuplicateCheckResult(
                is_duplicate=True,
                existing_task=existing,
                similarity_score=0.95,
                reason="Duplicate found"
            )
            with patch.object(client, 'create_task', new_callable=AsyncMock) as mock_create:
                task, check_result = await client.create_task_if_not_duplicate(
                    title="Tâche existante"
                )

        assert task is None
        assert check_result.is_duplicate
        assert check_result.existing_task.task_id == "existing-123"
        mock_create.assert_not_called()


class TestParseAppleScriptDate:
    """Tests for AppleScript date parsing."""

    def test_iso_format(self, client):
        """Test parsing ISO format date."""
        result = client._parse_applescript_date("2026-01-20 17:00:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 20

    def test_european_format(self, client):
        """Test parsing European format date."""
        result = client._parse_applescript_date("20/01/2026 17:00:00")
        assert result is not None
        assert result.day == 20
        assert result.month == 1

    def test_invalid_format(self, client):
        """Test parsing invalid date format."""
        result = client._parse_applescript_date("not a date")
        assert result is None

    def test_empty_string(self, client):
        """Test parsing empty string."""
        result = client._parse_applescript_date("")
        assert result is None
