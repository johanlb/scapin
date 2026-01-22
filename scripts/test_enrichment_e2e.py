#!/usr/bin/env python3
"""
Test end-to-end: Enrichments creating/enriching notes.

This script tests the full flow:
1. Find a pending queue item
2. Reanalyze it via QueueService (which persists results)
3. Verify proposed_notes are saved
4. Approve the item (optionally)
5. Verify note creation/enrichment (optionally)
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.core.config_manager import get_config
from src.integrations.storage.queue_storage import QueueStorage
from src.frontin.api.services.queue_service import QueueService


async def test_enrichment_flow(search_term: str = None, approve: bool = False):
    """Test enrichment flow end-to-end."""
    print("🧪 Test E2E: Enrichments → Note Creation")
    print("=" * 60)

    # 1. Load Config and Services
    try:
        config = get_config()
        print(f"✅ Config loaded (Env: {config.environment})")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return

    storage = QueueStorage()
    service = QueueService(storage)

    # 2. Find a pending item
    items = storage.load_queue(status="pending")
    if not items:
        print("⚠️ No pending items in queue")
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
    print(f"\n📝 Selected: {subject}")
    print(f"   ID: {item_id}")

    # Check current analysis
    current_analysis = item.get("analysis", {})
    current_notes = current_analysis.get("proposed_notes", [])
    print(f"\n📊 Current state:")
    print(f"   Action: {current_analysis.get('action', 'none')}")
    print(f"   Proposed notes: {len(current_notes)}")

    # 3. Reanalyze via QueueService
    print("\n⏳ Reanalyzing via QueueService (Four Valets)...")
    try:
        result = await service.reanalyze_item(item_id)
        if not result:
            print("❌ Reanalysis failed")
            return

        print("✅ Reanalysis complete")

        # result is the full item with analysis at first level
        analysis = result.get("analysis", {})
        print(f"   Action: {analysis.get('action', 'unknown')}")
        print(f"   Confidence: {analysis.get('confidence', 0)}%")

        # Check proposed_notes
        proposed_notes = analysis.get("proposed_notes", [])
        proposed_tasks = analysis.get("proposed_tasks", [])

        print(f"\n📦 Proposed enrichments:")
        print(f"   Notes: {len(proposed_notes)}")
        print(f"   Tasks: {len(proposed_tasks)}")

        if proposed_notes:
            print("\n   Notes to create/enrich:")
            for i, note in enumerate(proposed_notes, 1):
                action = note.get("action", "unknown")
                title = note.get("title", "No title")
                note_type = note.get("note_type", "unknown")
                required = "🔴" if note.get("required") else "⚪"
                conf = note.get("confidence", {})
                quality = conf.get("quality", 0) * 100 if isinstance(conf, dict) else 0
                print(f"   {required} [{i}] {action.upper()}: {title}")
                print(f"       Type: {note_type}, Confidence: {quality:.0f}%")
                content = note.get("content_summary", "")[:80]
                print(f"       Content: {content}...")

        if proposed_tasks:
            print("\n   Tasks to create:")
            for i, task in enumerate(proposed_tasks, 1):
                title = task.get("title", "No title")[:60]
                due = task.get("due_date", "No date")
                print(f"   [{i}] {title}... (due: {due})")

        # 4. Verify persistence
        print("\n🔍 Verifying persistence...")
        reloaded = storage.get_item(item_id)
        if reloaded:
            reloaded_notes = reloaded.get("analysis", {}).get("proposed_notes", [])
            print(f"   Persisted proposed_notes: {len(reloaded_notes)}")
            if len(reloaded_notes) == len(proposed_notes):
                print("   ✅ Persistence verified!")
            else:
                print("   ⚠️ Persistence mismatch!")

        # 5. Optionally approve
        if approve and proposed_notes:
            print("\n🎯 Approving item to execute enrichments...")
            action = analysis.get("action", "archive")
            approved = await service.approve_item(item_id, action=action)
            if approved:
                print(f"   ✅ Item approved with action: {action}")
                status = approved.get("enrichment_status", {})
                print(f"   Enrichment status: {status.get('status', 'unknown')}")
                executed = status.get("executed", [])
                failed = status.get("failed", [])
                print(f"   Executed: {executed}")
                print(f"   Failed: {failed}")

                if executed:
                    print("\n   📝 Notes created/enriched:")
                    from src.passepartout.note_manager import get_note_manager
                    note_manager = get_note_manager()
                    for title in executed:
                        note = note_manager.get_note_by_title(title)
                        if note:
                            print(f"      ✅ {note.title} ({note.note_id})")
                        else:
                            # Try partial match
                            for summary in note_manager.get_notes_summary()[:50]:
                                if title.lower() in summary.get("title", "").lower():
                                    print(f"      ✅ {summary['title']} (partial match)")
                                    break
                            else:
                                print(f"      ⚠️ {title} (not found - may be prefix matched)")
            else:
                print("   ❌ Approval failed")
        elif not approve:
            print("\n💡 Run with --approve flag to execute enrichments")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    # Usage: python script.py [search_term] [--approve]
    search_term = None
    approve = False

    for arg in sys.argv[1:]:
        if arg == "--approve":
            approve = True
        elif not arg.startswith("-"):
            search_term = arg

    asyncio.run(test_enrichment_flow(search_term, approve))
