import asyncio
import sys
import os
from dataclasses import asdict
from datetime import datetime, timezone
import json

# Add src to path
sys.path.append(os.getcwd())

from src.core.config_manager import get_config
from src.integrations.storage.queue_storage import QueueStorage
from src.sancho.multi_pass_analyzer import create_multi_pass_analyzer
from src.core.events.universal_event import (
    PerceivedEvent,
    EventSource,
    EventType,
    UrgencyLevel,
    Entity,
)


async def test_live_reanalysis(search_term: str = None, status: str = "pending"):
    print("🚀 Starting Live Four Valets Test on Queue Item")
    print(f"   Searching in status: {status}")

    # 1. Load Config
    try:
        config = get_config()
        print(f"✅ Config loaded (Env: {config.environment})")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return

    # 2. Access Queue
    storage = QueueStorage()
    items = storage.load_queue(status=status)

    if not items:
        print(f"⚠️ No {status} items in queue to test with.")
        return

    # Select item by search term or first item
    item = None
    if search_term:
        search_lower = search_term.lower()
        for candidate in items:
            subject = candidate.get("metadata", {}).get("subject", "").lower()
            from_addr = candidate.get("metadata", {}).get("from_address", "").lower()
            if search_lower in subject or search_lower in from_addr:
                item = candidate
                break
        if not item:
            print(f"⚠️ No item found matching '{search_term}'. Available items:")
            for i, it in enumerate(items[:10]):
                print(f"  {i+1}. {it['metadata'].get('subject', 'No subject')}")
            return
    else:
        item = items[0]
    item_id = item["id"]
    subject = item["metadata"]["subject"]
    print(f"📝 Selected Item: {subject} (ID: {item_id})")

    # 3. Construct PerceivedEvent from Queue Item
    # We need to map the queue item structure back to a PerceivedEvent
    # This is a bit manual but necessary for the analyzer

    metadata = item["metadata"]
    content = item.get("content", {})

    # Parse date (ensure timezone-aware)
    try:
        occurred_at = datetime.fromisoformat(metadata.get("date").replace("Z", "+00:00"))
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    except:
        occurred_at = datetime.now(timezone.utc)

    event = PerceivedEvent(
        event_id=item_id,
        source=EventSource.EMAIL,
        source_id=metadata.get("message_id", "unknown"),
        occurred_at=occurred_at,
        received_at=datetime.now(timezone.utc),  # Approximate
        perceived_at=datetime.now(timezone.utc),
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
    # Note: We rely on default dependency injection via factory function
    analyzer = create_multi_pass_analyzer()

    # 5. Run Analysis
    print("\n⏳ Running Four Valets analysis...")
    try:
        result = await analyzer.analyze(event)

        print("\n✅ Analysis Completed Successfully")
        print("-" * 50)
        print(f"Action: {result.action}")
        overall_pct = result.confidence.overall * 100 if result.confidence.overall <= 1 else result.confidence.overall
        print(f"Confidence: {overall_pct:.0f}%")
        print(f"Stopped At: {result.stopped_at}")

        # Display extractions
        if result.extractions:
            print(f"\n📦 Extractions ({len(result.extractions)}):")
            for i, ext in enumerate(result.extractions, 1):
                # Convert dataclass to dict
                try:
                    ext_dict = asdict(ext)
                except TypeError:
                    # Fallback for Pydantic models
                    ext_dict = ext.model_dump() if hasattr(ext, 'model_dump') else vars(ext)
                print(f"\n  [{i}] {ext_dict.get('type', 'unknown').upper()} - {ext_dict.get('importance', 'unknown')}")
                info = ext_dict.get('info', 'N/A') or 'N/A'
                print(f"      Info: {info[:120]}...")
                print(f"      Note cible: {ext_dict.get('note_cible', 'N/A')}")
                print(f"      Date: {ext_dict.get('date', 'N/A')}")
                conf = ext_dict.get('confidence', {})
                if isinstance(conf, dict):
                    quality = conf.get('quality', 0) * 100
                    print(f"      Confidence: {quality:.0f}%")
                print(f"      OmniFocus: {ext_dict.get('omnifocus', False)}")

        if result.stopped_at == "mousqueton":
            print("\n🎭 Mousqueton Details:")
            print(f"Arbitrage: {json.dumps(result.arbitrage, indent=2, ensure_ascii=False)}")
            print(
                f"Confidence Assessment: {json.dumps(result.confidence_assessment, indent=2, ensure_ascii=False)}"
            )
        elif result.stopped_at == "planchet":
            print("\n🧐 Planchet Details:")
            print(f"Critique: {json.dumps(result.critique, indent=2, ensure_ascii=False)}")

        # Display strategic questions (v3.1)
        if result.strategic_questions:
            print(f"\n❓ Strategic Questions ({len(result.strategic_questions)}):")
            for i, sq in enumerate(result.strategic_questions, 1):
                print(f"\n  [{i}] {sq.get('question', 'N/A')}")
                print(f"      Target note: {sq.get('target_note', 'N/A')}")
                print(f"      Category: {sq.get('category', 'N/A')}")
                print(f"      Source: {sq.get('source', 'N/A')}")
                if sq.get('context'):
                    print(f"      Context: {sq.get('context')}")

        print("-" * 50)

    except Exception as e:
        print(f"\n❌ Analysis Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Accept optional search term and status as arguments
    # Usage: python script.py [search_term] [status]
    # Example: python script.py nautil approved
    search_term = sys.argv[1] if len(sys.argv) > 1 else None
    status = sys.argv[2] if len(sys.argv) > 2 else "pending"
    asyncio.run(test_live_reanalysis(search_term, status))
