import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.getcwd())

from src.core.events.universal_event import PerceivedEvent, EventSource, EventType, UrgencyLevel
from src.sancho.multi_pass_analyzer import MultiPassAnalyzer
from src.sancho.context_searcher import StructuredContext
from src.sancho.convergence import MultiPassConfig


async def verify_four_valets():
    print("🚀 Starting Four Valets Pipeline Verification")

    # 1. Setup Mocks
    mock_router = AsyncMock()
    mock_context_searcher = AsyncMock()

    # Mock Config
    config = MultiPassConfig()
    config.four_valets.enabled = True

    # Mock Context Search Result
    mock_context = StructuredContext(
        query_entities=["Test Person"],
        search_timestamp=datetime.now(timezone.utc),
        sources_searched=["notes"],
        notes=[],
        calendar=[],
        tasks=[],
        emails=[],
        entity_profiles={},
        conflicts=[],
    )
    mock_context_searcher.search_for_entities.return_value = mock_context

    # 2. Define Mock Responses for each Valet

    # Grimaud Response
    grimaud_response = (
        """{
            "action": "flag",
            "confidence": {
                "entity_confidence": 0.8,
                "action_confidence": 0.8,
                "extraction_confidence": 0.8,
                "completeness": 0.8
            },
            "extractions": [{"info": "Meeting request", "type": "event", "importance": "moyenne"}],
            "reasoning": "Looks like a meeting",
            "entities_discovered": ["Test Person"]
        }""",
        {"input_tokens": 100, "output_tokens": 100},
    )

    # Bazin Response
    bazin_response = (
        """{
            "action": "flag",
            "confidence": {
                "entity_confidence": 0.85,
                "action_confidence": 0.85,
                "extraction_confidence": 0.85,
                "completeness": 0.85
            },
            "extractions": [{"info": "Meeting request", "type": "event", "importance": "moyenne"}],
            "reasoning": "Context confirms person exists",
            "entities_discovered": ["Test Person"],
            "changes_made": ["Added context"],
            "context_influence": {"notes_used": ["Note 1"]}
        }""",
        {"input_tokens": 150, "output_tokens": 100},
    )

    # Planchet Response
    planchet_response = (
        """{
            "action": "flag",
            "confidence": {
                "entity_confidence": 0.9,
                "action_confidence": 0.9,
                "extraction_confidence": 0.9,
                "completeness": 0.9
            },
            "extractions": [{"info": "Meeting request", "type": "event", "importance": "moyenne"}],
            "reasoning": "Validated extractions",
            "entities_discovered": ["Test Person"],
            "critique": {
                "extraction_issues": [],
                "action_issues": [],
                "age_concerns": [],
                "contradictions": [],
                "recommendations": ["Check availability"],
                "questions_for_mousqueton": ["Should we auto-accept?"],
                "confidence_assessment": {"can_proceed": true}
            },
            "confidence_assessment": {"can_proceed": true}
        }""",
        {"input_tokens": 200, "output_tokens": 100},
    )

    # Mousqueton Response
    mousqueton_response = (
        """{
            "action": "queue",
            "confidence": {
                "entity_confidence": 0.95,
                "action_confidence": 0.95,
                "extraction_confidence": 0.95,
                "completeness": 0.95
            },
            "extractions": [{"info": "Meeting request verified", "type": "event", "importance": "haute"}],
            "reasoning": "Final decision: queue for review",
            "entities_discovered": ["Test Person"],
            "arbitrage": {
                "planchet_answers": [{"question": "Should we auto-accept?", "answer": "No"}],
                "conflicts_resolved": [],
                "age_decision": {"still_relevant": true}
            },
            "confidence_assessment": {"final_verdict": "confident"}
        }""",
        {"input_tokens": 250, "output_tokens": 100},
    )

    # Set side effects for sequential calls
    mock_router._call_claude = MagicMock(
        side_effect=[grimaud_response, bazin_response, planchet_response, mousqueton_response]
    )

    # 3. Initialize Analyzer
    analyzer = MultiPassAnalyzer(
        ai_router=mock_router, context_searcher=mock_context_searcher, config=config
    )

    # 4. Create Test Event
    now = datetime.now(timezone.utc)
    event = PerceivedEvent(
        event_id="test-event-001",
        source=EventSource.EMAIL,
        source_id="msg-001",
        occurred_at=now,
        received_at=now,
        perceived_at=now,
        title="Project Meeting",
        content="Hello, can we meet tomorrow regarding the project?",
        event_type=EventType.REQUEST,
        urgency=UrgencyLevel.MEDIUM,
        entities=[],
        topics=[],
        keywords=[],
        from_person="Sender Name <sender@example.com>",
        to_people=["me@example.com"],
        cc_people=[],
        thread_id=None,
        references=[],
        in_reply_to=None,
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        metadata={},
        perception_confidence=1.0,
        needs_clarification=False,
        clarification_questions=[],
    )

    # 5. Run Analysis
    print("⏳ Running analysis...")
    try:
        result = await analyzer.analyze(event)

        print("\n✅ Analysis Completed Successfully")
        print(f"Final Action: {result.action}")
        print(f"Passes Count: {result.passes_count}")
        print(f"Stopped At: {result.stopped_at}")

        # Verify Mousqueton specific fields
        if hasattr(result, "arbitrage") and result.arbitrage:
            print("✅ Arbitrage field present")
        else:
            print("❌ Arbitrage field missing")

        if hasattr(result, "confidence_assessment") and result.confidence_assessment:
            print("✅ Confidence Assessment field present")
        else:
            print("❌ Confidence Assessment field missing")

    except Exception as e:
        print(f"\n❌ Analysis Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify_four_valets())
