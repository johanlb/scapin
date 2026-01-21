import asyncio
import sys
import os
from datetime import datetime
import json

# Add src to path
sys.path.append(os.getcwd())

from src.core.config_manager import get_config
from src.integrations.storage.queue_storage import QueueStorage
from src.sancho.multi_pass_analyzer import MultiPassAnalyzer
from src.core.events.universal_event import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
    Entity,
)


async def test_live_reanalysis():
    print("🚀 Starting Live Four Valets Test on Queue Item")

    # 1. Load Config
    try:
        config = get_config()
        print(f"✅ Config loaded (Env: {config.environment})")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return

    # 2. Access Queue
    storage = QueueStorage()
    items = storage.load_queue(status="pending")

    if not items:
        print("⚠️ No pending items in queue to test with.")
        return

    # Select the first item
    item = items[0]
    item_id = item["id"]
    subject = item["metadata"]["subject"]
    print(f"📝 Selected Item: {subject} (ID: {item_id})")

    # 3. Construct PerceivedEvent from Queue Item
    # We need to map the queue item structure back to a PerceivedEvent
    # This is a bit manual but necessary for the analyzer

    metadata = item["metadata"]
    content = item.get("content", {})

    # Parse date
    try:
        occurred_at = datetime.fromisoformat(metadata.get("date"))
    except:
        occurred_at = datetime.now()

    event = PerceivedEvent(
        event_id=item_id,
        source=EventSource.EMAIL,
        source_id=metadata.get("message_id", "unknown"),
        occurred_at=occurred_at,
        received_at=datetime.now(),  # Approximate
        perceived_at=datetime.now(),
        title=metadata.get("subject", "No Subject"),
        content=content.get("full_text") or content.get("preview") or "No content",
        event_type=EventType.INFORMATION,
        urgency=UrgencyLevel.LOW,
        entities=[],
        topics=[],
        keywords=[],
        from_person=metadata.get("from_address", "unknown"),
        to_people=[],
        cc_people=[],
        thread_id=None,
        references=[],
        in_reply_to=None,
        has_attachments=metadata.get("has_attachments", False),
        attachment_count=len(metadata.get("attachments", [])),
        attachment_types=[],
        urls=[],
        metadata=metadata,
        perception_confidence=1.0,
        needs_clarification=False,
        clarification_questions=[],
    )

    print("✅ Event constructed")

    # 4. Initialize Analyzer
    # Note: We rely on default dependency injection
    analyzer = MultiPassAnalyzer()

    # 5. Run Analysis
    print("\n⏳ Running Four Valets analysis...")
    try:
        result = await analyzer.analyze(event)

        print("\n✅ Analysis Completed Successfully")
        print("-" * 50)
        print(f"Action: {result.action}")
        print(f"Confidence: {result.confidence.overall}%")
        print(f"Stopped At: {result.stopped_at}")

        if result.stopped_at == "mousqueton":
            print("\n🎭 Mousqueton Details:")
            print(f"Arbitrage: {json.dumps(result.arbitrage, indent=2, ensure_ascii=False)}")
            print(
                f"Confidence Assessment: {json.dumps(result.confidence_assessment, indent=2, ensure_ascii=False)}"
            )
        elif result.stopped_at == "planchet":
            print("\n🧐 Planchet Details:")
            print(f"Critique: {json.dumps(result.critique, indent=2, ensure_ascii=False)}")

        print("-" * 50)

    except Exception as e:
        print(f"\n❌ Analysis Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_live_reanalysis())
