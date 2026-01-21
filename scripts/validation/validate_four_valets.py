#!/usr/bin/env python3
"""
Validation Script for Four Valets v3.0

Validates the Four Valets pipeline against the 100-email dataset.
Uses mocked AI responses to verify routing and stopping logic.

Metrics tracked:
- Early stop accuracy (ephemeral content detection)
- Routing accuracy (correct valet path)
- Action accuracy (archive/delete decisions)
- Overall pipeline correctness
"""

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.events.universal_event import (
    EventSource,
    EventType,
    PerceivedEvent,
    UrgencyLevel,
    now_utc,
)
from src.sancho.convergence import FourValetsConfig, MultiPassConfig
from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

# Dataset path
DATASET_PATH = Path(__file__).parent.parent.parent / "tests" / "validation" / "dataset" / "validation_100_emails.json"


@dataclass
class ValidationMetrics:
    """Track validation metrics."""

    total: int = 0
    passed: int = 0
    failed: int = 0

    early_stop_correct: int = 0
    early_stop_total: int = 0

    routing_correct: int = 0
    routing_total: int = 0

    action_correct: int = 0
    action_total: int = 0

    failures: list[dict] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total * 100 if self.total > 0 else 0

    @property
    def early_stop_accuracy(self) -> float:
        return self.early_stop_correct / self.early_stop_total * 100 if self.early_stop_total > 0 else 0

    @property
    def routing_accuracy(self) -> float:
        return self.routing_correct / self.routing_total * 100 if self.routing_total > 0 else 0

    @property
    def action_accuracy(self) -> float:
        return self.action_correct / self.action_total * 100 if self.action_total > 0 else 0


def create_event_from_email(email: dict) -> PerceivedEvent:
    """Create a PerceivedEvent from email fixture data."""
    event_data = email["event"]
    now = now_utc()

    urgency_map = {
        "low": UrgencyLevel.LOW,
        "medium": UrgencyLevel.MEDIUM,
        "high": UrgencyLevel.HIGH,
        "critical": UrgencyLevel.CRITICAL,
    }

    type_map = {
        "information": EventType.INFORMATION,
        "action_required": EventType.ACTION_REQUIRED,
        "reminder": EventType.REMINDER,
        "request": EventType.REQUEST,
    }

    return PerceivedEvent(
        event_id=event_data["event_id"],
        source=EventSource.EMAIL,
        source_id=f"email_{event_data['event_id']}",
        occurred_at=now,
        received_at=now,
        title=event_data["title"],
        content=event_data["content"],
        event_type=type_map.get(event_data.get("event_type", "information"), EventType.INFORMATION),
        urgency=urgency_map.get(event_data.get("urgency", "medium"), UrgencyLevel.MEDIUM),
        entities=[],
        topics=[],
        keywords=[],
        from_person=event_data.get("from_person", "unknown@example.com"),
        to_people=event_data.get("to_people", []),
        cc_people=[],
        thread_id=None,
        references=[],
        in_reply_to=None,
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        metadata={},
        perception_confidence=0.8,
        needs_clarification=False,
        clarification_questions=[],
    )


def create_mock_response(expected: dict) -> str:
    """Create a mock AI response based on expected outcomes."""
    action = expected.get("action", "archive")
    early_stop = expected.get("early_stop", False)
    stopped_at = expected.get("stopped_at", "planchet")
    needs_mousqueton = expected.get("needs_mousqueton", False)

    # Set confidence based on expected behavior
    if early_stop and action == "delete":
        # High confidence for early stop
        confidence = {
            "entity_confidence": 0.98,
            "action_confidence": 0.97,
            "extraction_confidence": 0.96,
            "completeness": 0.99,
        }
    elif stopped_at == "planchet":
        # High confidence for Planchet conclusion
        confidence = {
            "entity_confidence": 0.92,
            "action_confidence": 0.91,
            "extraction_confidence": 0.90,
            "completeness": 0.93,
        }
    elif needs_mousqueton or stopped_at == "mousqueton":
        # Lower confidence to trigger Mousqueton
        confidence = {
            "entity_confidence": 0.75,
            "action_confidence": 0.70,
            "extraction_confidence": 0.72,
            "completeness": 0.68,
        }
    else:
        # Medium confidence
        confidence = {
            "entity_confidence": 0.85,
            "action_confidence": 0.82,
            "extraction_confidence": 0.83,
            "completeness": 0.80,
        }

    # Create extractions based on expected
    extractions = []
    min_extractions = expected.get("min_extractions", 0)
    expected_types = expected.get("expected_types", ["fait"])

    for i in range(min_extractions):
        ext_type = expected_types[i % len(expected_types)]
        extractions.append({
            "info": f"Extraction {i+1} de type {ext_type}",
            "type": ext_type,
            "importance": "moyenne",
        })

    return json.dumps({
        "action": action,
        "confidence": confidence,
        "extractions": extractions,
        "early_stop": early_stop,
        "early_stop_reason": "Contenu éphémère" if early_stop else None,
        "needs_mousqueton": needs_mousqueton,
        "reasoning": f"Analysis for {stopped_at}",
    })


def setup_mock_responses(router, email: dict):
    """Configure mock AI responses for an email."""
    expected = email["expected"]
    stopped_at = expected.get("stopped_at", "planchet")
    early_stop = expected.get("early_stop", False)
    needs_mousqueton = expected.get("needs_mousqueton", False)

    mock_usage = {"input_tokens": 100, "output_tokens": 50}
    responses = []

    # Grimaud response
    grimaud_expected = expected.copy()
    if early_stop:
        grimaud_expected["early_stop"] = True
    else:
        grimaud_expected["early_stop"] = False
        grimaud_expected["needs_mousqueton"] = False
    responses.append(create_mock_response(grimaud_expected))

    # If not early stop, add more passes
    if not early_stop:
        # Bazin response
        bazin_expected = {
            "action": expected.get("action", "archive"),
            "early_stop": False,
            "needs_mousqueton": False,
        }
        responses.append(create_mock_response(bazin_expected))

        # Planchet response
        planchet_expected = expected.copy()
        if stopped_at == "mousqueton" or needs_mousqueton:
            planchet_expected["needs_mousqueton"] = True
        else:
            planchet_expected["needs_mousqueton"] = False
        responses.append(create_mock_response(planchet_expected))

        # Mousqueton response (if needed)
        if stopped_at == "mousqueton" or needs_mousqueton:
            responses.append(create_mock_response(expected))

    # Setup response queue
    router._response_queue = responses
    router._mock_usage = mock_usage

    def _call_claude(*_args, **_kwargs):
        if router._response_queue:
            return (router._response_queue.pop(0), mock_usage)
        return ("{}", mock_usage)

    router._call_claude = MagicMock(side_effect=_call_claude)


def create_mock_analyzer():
    """Create a MultiPassAnalyzer with mocked dependencies."""
    router = MagicMock()
    router._response_queue = []
    router._mock_usage = {"input_tokens": 100, "output_tokens": 50}

    renderer = MagicMock()
    renderer.render_grimaud.return_value = "Grimaud prompt"
    renderer.render_bazin.return_value = "Bazin prompt"
    renderer.render_planchet.return_value = "Planchet prompt"
    renderer.render_mousqueton.return_value = "Mousqueton prompt"
    renderer._get_briefing.return_value = ""

    searcher = AsyncMock()

    config = MultiPassConfig(
        four_valets=FourValetsConfig(
            enabled=True,
            fallback_to_legacy=False,  # Don't fall back for validation
            grimaud_early_stop_confidence=0.95,
            planchet_stop_confidence=0.90,
        )
    )

    return MultiPassAnalyzer(
        ai_router=router,
        template_renderer=renderer,
        context_searcher=searcher,
        config=config,
    ), router


async def validate_email(email: dict, analyzer: MultiPassAnalyzer, router, metrics: ValidationMetrics) -> bool:
    """Validate a single email against expected outcomes."""
    expected = email["expected"]
    event = create_event_from_email(email)

    # Setup mock responses
    setup_mock_responses(router, email)

    try:
        # Run analysis
        result = await analyzer.analyze(event, use_four_valets=True)

        # Track metrics
        metrics.total += 1
        metrics.routing_total += 1
        metrics.action_total += 1

        # Check early stop
        if expected.get("early_stop", False):
            metrics.early_stop_total += 1
            if result.stopped_at == "grimaud" and len(result.pass_history) == 1:
                metrics.early_stop_correct += 1

        # Check routing (stopped_at)
        expected_stopped = expected.get("stopped_at", "planchet")
        if result.stopped_at == expected_stopped:
            metrics.routing_correct += 1
        else:
            # Allow some flexibility for mousqueton vs planchet
            if expected_stopped == "planchet" and result.stopped_at == "mousqueton":
                # Escalation is acceptable
                metrics.routing_correct += 1

        # Check action
        expected_action = expected.get("action", "archive")
        if result.action == expected_action:
            metrics.action_correct += 1

        # Overall pass/fail
        passed = True

        # Critical failures
        if expected.get("early_stop") and result.stopped_at != "grimaud":
            passed = False

        if not expected.get("early_stop") and result.stopped_at == "grimaud":
            passed = False

        if passed:
            metrics.passed += 1
        else:
            metrics.failed += 1
            metrics.failures.append({
                "index": email.get("index"),
                "id": email.get("id"),
                "category": email.get("category"),
                "expected_stopped": expected_stopped,
                "actual_stopped": result.stopped_at,
                "expected_action": expected_action,
                "actual_action": result.action,
            })

        return passed

    except Exception as e:
        metrics.total += 1
        metrics.failed += 1
        metrics.failures.append({
            "index": email.get("index"),
            "id": email.get("id"),
            "category": email.get("category"),
            "error": str(e),
        })
        return False


async def run_validation():
    """Run validation on the full dataset."""
    print("=" * 60)
    print("Four Valets v3.0 Validation")
    print("=" * 60)
    print()

    # Load dataset
    print(f"Loading dataset from: {DATASET_PATH}")
    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} emails")
    print()

    # Create analyzer
    analyzer, router = create_mock_analyzer()

    # Run validation
    metrics = ValidationMetrics()

    print("Running validation...")
    print("-" * 40)

    for i, email in enumerate(dataset):
        passed = await validate_email(email, analyzer, router, metrics)
        status = "✓" if passed else "✗"
        category = email.get("category", "unknown")
        print(f"  [{i+1:3d}/100] {status} {category:12s} - {email['event']['event_id']}")

    print("-" * 40)
    print()

    # Print results
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print()

    print(f"Total emails:        {metrics.total}")
    print(f"Passed:              {metrics.passed}")
    print(f"Failed:              {metrics.failed}")
    print(f"Pass rate:           {metrics.pass_rate:.1f}%")
    print()

    print("Detailed Metrics:")
    print(f"  Early stop accuracy:  {metrics.early_stop_accuracy:.1f}% ({metrics.early_stop_correct}/{metrics.early_stop_total})")
    print(f"  Routing accuracy:     {metrics.routing_accuracy:.1f}% ({metrics.routing_correct}/{metrics.routing_total})")
    print(f"  Action accuracy:      {metrics.action_accuracy:.1f}% ({metrics.action_correct}/{metrics.action_total})")
    print()

    # Print failures if any
    if metrics.failures:
        print("Failures:")
        for failure in metrics.failures[:10]:  # Show first 10
            if "error" in failure:
                print(f"  - [{failure.get('index')}] {failure.get('category')}: ERROR - {failure.get('error')}")
            else:
                print(f"  - [{failure.get('index')}] {failure.get('category')}: expected {failure.get('expected_stopped')}, got {failure.get('actual_stopped')}")

        if len(metrics.failures) > 10:
            print(f"  ... and {len(metrics.failures) - 10} more failures")

    print()

    # Summary
    if metrics.pass_rate >= 90:
        print("✓ VALIDATION PASSED (≥90% accuracy)")
        return 0
    else:
        print("✗ VALIDATION FAILED (<90% accuracy)")
        return 1


def main():
    """Main entry point."""
    exit_code = asyncio.run(run_validation())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
