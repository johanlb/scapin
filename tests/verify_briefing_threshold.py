import asyncio
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Mock heavy dependencies
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["pydantic_settings"] = MagicMock()
sys.modules["git"] = MagicMock()
sys.modules["git.exc"] = MagicMock()
sys.modules["git.repo"] = MagicMock()
sys.modules["gitdb"] = MagicMock()
sys.modules["gitdb.exc"] = MagicMock()
sys.modules["faiss"] = MagicMock()
sys.modules["msal"] = MagicMock()

# Mock config
mock_config_manager = MagicMock()


class MockAIConfig:
    rate_limit_per_minute = 60
    anthropic_api_key = "sk-test"
    confidence_threshold = 0.8


mock_config_manager.AIConfig = MockAIConfig
sys.modules["src.core.config_manager"] = mock_config_manager

# Imports après les mocks sys.modules (intentionnel)
from src.core.schemas import NoteAnalysis  # noqa: E402
from src.passepartout.note_manager import Note  # noqa: E402
from src.passepartout.note_metadata import NoteMetadata  # noqa: E402
from src.passepartout.note_types import NoteType  # noqa: E402
from src.passepartout.retouche_reviewer import RetoucheReviewer  # noqa: E402


class TestThresholdPolicy(unittest.TestCase):
    def setUp(self):
        self.note_manager = MagicMock()
        self.metadata_store = MagicMock()
        self.scheduler = MagicMock()
        self.ai_router = MagicMock()

        self.reviewer = RetoucheReviewer(
            note_manager=self.note_manager,
            metadata_store=self.metadata_store,
            scheduler=self.scheduler,
            ai_router=self.ai_router,
        )
        # Default threshold is 0.90
        self.reviewer.AUTO_APPLY_THRESHOLD = 0.90

    async def test_thresholds(self):
        """Test different threshold scenarios for Briefing vs Normal notes"""

        # Setup source note
        source_note = Note(
            note_id="meeting-1",
            title="Meeting note",
            content="Content",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        source_metadata = NoteMetadata(note_id="meeting-1", note_type=NoteType.REUNION)

        # Setup target notes (Profile and a random note)
        profile_note = Note(
            note_id="Profile",
            title="Profile",
            content="",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        other_note = Note(
            note_id="Other",
            title="Other",
            content="",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.note_manager.get_note.side_effect = lambda nid: {
            "meeting-1": source_note,
            "Profile": profile_note,
            "Other": other_note,
        }.get(nid)
        self.metadata_store.get.return_value = source_metadata

        # SCENARIO 1: Briefing Update with 86% confidence -> Should be APPLIED
        mock_analysis_1 = MagicMock(spec=NoteAnalysis)
        mock_analysis_1.confidence = 0.86
        mock_analysis_1.proposed_notes = [
            {"title": "Profile", "target_note_id": "Profile", "content": "New Job"}
        ]
        mock_analysis_1.proposed_tasks = []
        self.ai_router.analyze_note.return_value = mock_analysis_1

        result_1 = await self.reviewer.review_note("meeting-1")
        self.assertEqual(
            len(result_1.applied_actions), 1, "Briefing update at 86% should be applied"
        )
        self.assertEqual(len(result_1.pending_actions), 0)

        # SCENARIO 2: Briefing Update with 80% confidence -> Should be PENDING
        mock_analysis_2 = MagicMock(spec=NoteAnalysis)
        mock_analysis_2.confidence = 0.80
        mock_analysis_2.proposed_notes = [
            {"title": "Profile", "target_note_id": "Profile", "content": "New Hobby"}
        ]
        mock_analysis_2.proposed_tasks = []
        self.ai_router.analyze_note.return_value = mock_analysis_2

        result_2 = await self.reviewer.review_note("meeting-1")
        self.assertEqual(
            len(result_2.applied_actions), 0, "Briefing update at 80% should be pending"
        )
        self.assertEqual(len(result_2.pending_actions), 1)

        # SCENARIO 3: Normal Update with 86% confidence -> Should be PENDING (threshold 90%)
        mock_analysis_3 = MagicMock(spec=NoteAnalysis)
        mock_analysis_3.confidence = 0.86
        mock_analysis_3.proposed_notes = [{"title": "Enrichment", "content": "Bonus info"}]
        mock_analysis_3.proposed_tasks = []
        self.ai_router.analyze_note.return_value = mock_analysis_3

        result_3 = await self.reviewer.review_note("meeting-1")
        self.assertEqual(
            len(result_3.applied_actions),
            0,
            "Normal update at 86% should be pending (threshold 90%)",
        )
        self.assertEqual(len(result_3.pending_actions), 1)

        # SCENARIO 4: Normal Update with 91% confidence -> Should be APPLIED
        mock_analysis_4 = MagicMock(spec=NoteAnalysis)
        mock_analysis_4.confidence = 0.91
        mock_analysis_4.proposed_notes = [{"title": "Enrichment", "content": "Super info"}]
        mock_analysis_4.proposed_tasks = []
        self.ai_router.analyze_note.return_value = mock_analysis_4

        result_4 = await self.reviewer.review_note("meeting-1")
        self.assertEqual(len(result_4.applied_actions), 1, "Normal update at 91% should be applied")

        print("✅ All threshold logic verified!")


if __name__ == "__main__":

    async def run_tests():
        test = TestThresholdPolicy()
        test.setUp()
        await test.test_thresholds()
        print("✅ Threshold tests passed!")

    asyncio.run(run_tests())
