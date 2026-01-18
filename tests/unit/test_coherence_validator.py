"""
Tests for coherence_validator.py — Coherence Service
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sancho.coherence_validator import CoherenceService
from src.sancho.convergence import Extraction
from src.passepartout.note_manager import NoteManager
from src.sancho.router import AIRouter


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies"""
    return {
        "router": AsyncMock(spec=AIRouter),
        "note_manager": MagicMock(spec=NoteManager),
        "entity_searcher": MagicMock(),  # Type not strict for now
    }


class TestCoherenceService:
    """Tests for CoherenceService"""

    def test_init(self, mock_dependencies):
        """Test initialization"""
        service = CoherenceService(
            ai_router=mock_dependencies["router"],
            note_manager=mock_dependencies["note_manager"],
            entity_searcher=mock_dependencies["entity_searcher"],
        )
        # Verify protected attributes are set
        assert service._ai_router == mock_dependencies["router"]
        assert service._note_manager == mock_dependencies["note_manager"]

    @pytest.mark.asyncio
    async def test_validate_extractions_offloading(self, mock_dependencies):
        """Test that validation offloads heavy tasks to executor"""
        service = CoherenceService(
            ai_router=mock_dependencies["router"],
            note_manager=mock_dependencies["note_manager"],
        )

        # Setup Router Mock Return Value (within valid JSON)
        valid_response = """
        {
            "coherence_summary": {
                "status": "valid",
                "corrected": 0,
                "duplicates_detected": 0
            },
            "corrections": []
        }
        """
        mock_dependencies["router"].analyze_with_prompt_async.return_value = (
            valid_response,
            {"total_tokens": 100},
        )

        extractions = [
            Extraction(
                info="New Info", type="fait", importance="moyenne", note_cible="Existing Note"
            )
        ]

        # Mock run_in_executor to execute immediately but track calls
        async def mock_run_in_executor(executor, func, *args):
            return func(*args)

        with patch.object(
            asyncio.get_running_loop(), "run_in_executor", side_effect=mock_run_in_executor
        ) as mock_exec:
            # Mock internal heavy methods to be tracked
            with patch.object(service, "_load_target_notes") as mock_load:
                mock_load.return_value = {}
                with patch.object(service, "_find_similar_notes") as mock_find:
                    mock_find.return_value = []

                    # Run validation
                    await service.validate_extractions(extractions)

                    # Verify offloading
                    assert mock_exec.call_count >= 1

                    # Inspect what was passed to executor
                    # We look for our mocks being passed (wrapped in partial or direct)
                    found_load = False
                    for call in mock_exec.call_args_list:
                        func_arg = call.args[1]
                        # Unwrap partial if needed
                        if hasattr(func_arg, "func"):
                            func_arg = func_arg.func

                        if func_arg == mock_load:
                            found_load = True

                    assert found_load, "_load_target_notes should be called in executor"
