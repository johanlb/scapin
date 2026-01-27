"""
End-to-End Tests for Four Valets v3.0 Pipeline

These tests verify the complete Four Valets pipeline using realistic
email fixtures. They mock the AI responses but test the full routing,
stopping logic, and result aggregation.

Test categories:
- Early stop tests (OTP, spam, newsletters)
- Full pipeline tests (business emails, urgent deadlines)
- Context integration tests (personal, project updates)
- Arbitrage tests (conflicting information)
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.events.universal_event import (
    EventSource,
    EventType,
    PerceivedEvent,
    UrgencyLevel,
    now_utc,
)
from src.sancho.convergence import (
    FourValetsConfig,
    MultiPassConfig,
)
from src.sancho.multi_pass_analyzer import MultiPassAnalyzer

# ============================================================================
# Fixtures Directory
# ============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "emails"


def load_email_fixture(name: str) -> dict:
    """Load an email fixture by name."""
    fixture_path = FIXTURES_DIR / f"{name}.json"
    with open(fixture_path) as f:
        return json.load(f)


def create_event_from_fixture(fixture: dict) -> PerceivedEvent:
    """Create a PerceivedEvent from fixture data."""
    event_data = fixture["event"]
    now = now_utc()

    # Map string urgency to enum
    urgency_map = {
        "low": UrgencyLevel.LOW,
        "medium": UrgencyLevel.MEDIUM,
        "high": UrgencyLevel.HIGH,
        "critical": UrgencyLevel.CRITICAL,
    }

    # Map string event_type to enum
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


# ============================================================================
# Mock Response Generators
# ============================================================================


def create_grimaud_early_stop_response(action: str = "delete", reason: str = "ephemeral") -> str:
    """Create a Grimaud response that triggers early stop."""
    return json.dumps({
        "action": action,
        "confidence": {
            "entity_confidence": 0.98,
            "action_confidence": 0.97,
            "extraction_confidence": 0.96,
            "completeness": 0.99,
        },
        "extractions": [],
        "early_stop": True,
        "early_stop_reason": reason,
        "needs_mousqueton": False,
        "reasoning": f"Contenu éphémère détecté: {reason}",
    })


def create_grimaud_continue_response(extractions: list[dict] | None = None) -> str:
    """Create a Grimaud response that continues to Bazin."""
    return json.dumps({
        "action": "archive",
        "confidence": {
            "entity_confidence": 0.85,
            "action_confidence": 0.80,
            "extraction_confidence": 0.82,
            "completeness": 0.78,
        },
        "extractions": extractions or [
            {"info": "Fait extrait par Grimaud", "type": "fait", "importance": "moyenne"}
        ],
        "early_stop": False,
        "needs_mousqueton": False,
        "reasoning": "Extraction initiale, contexte nécessaire",
    })


def create_bazin_response(notes_used: list[str] | None = None) -> str:
    """Create a Bazin response with context enrichment."""
    return json.dumps({
        "action": "archive",
        "confidence": {
            "entity_confidence": 0.88,
            "action_confidence": 0.85,
            "extraction_confidence": 0.87,
            "completeness": 0.84,
        },
        "extractions": [
            {"info": "Fait enrichi par Bazin", "type": "fait", "importance": "moyenne", "note_cible": "Note Test"}
        ],
        "notes_used": notes_used or [],
        "notes_ignored": [],
        "context_quality": "good",
        "reasoning": "Contexte intégré avec succès",
    })


def create_planchet_conclude_response(extractions: list[dict] | None = None) -> str:
    """Create a Planchet response that concludes without Mousqueton."""
    return json.dumps({
        "action": "archive",
        "confidence": {
            "entity_confidence": 0.92,
            "action_confidence": 0.91,
            "extraction_confidence": 0.90,
            "completeness": 0.93,
        },
        "extractions": extractions or [
            {"info": "Fait validé par Planchet", "type": "fait", "importance": "moyenne", "note_cible": "Note Test"}
        ],
        "needs_mousqueton": False,
        "critique": "Analyse cohérente, pas de conflit détecté",
        "reasoning": "Validation complète",
    })


def create_planchet_escalate_response() -> str:
    """Create a Planchet response that escalates to Mousqueton."""
    return json.dumps({
        "action": "archive",
        "confidence": {
            "entity_confidence": 0.75,
            "action_confidence": 0.70,
            "extraction_confidence": 0.72,
            "completeness": 0.68,
        },
        "extractions": [
            {"info": "Fait à arbitrer", "type": "decision", "importance": "haute"}
        ],
        "needs_mousqueton": True,
        "critique": "Conflit détecté entre les sources",
        "reasoning": "Arbitrage nécessaire",
    })


def create_mousqueton_response(extractions: list[dict] | None = None) -> str:
    """Create a Mousqueton arbitrage response."""
    return json.dumps({
        "action": "archive",
        "confidence": {
            "entity_confidence": 0.95,
            "action_confidence": 0.94,
            "extraction_confidence": 0.93,
            "completeness": 0.96,
        },
        "extractions": extractions or [
            {"info": "Décision arbitrée par Mousqueton", "type": "decision", "importance": "haute", "note_cible": "Note Test"}
        ],
        "arbitrage_decision": "Date confirmée: 4 février",
        "reasoning": "Arbitrage final effectué",
    })


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_ai_router():
    """Create a mock AI router that returns (response_str, usage) tuples."""
    router = MagicMock()
    # Mock usage stats
    mock_usage = {"input_tokens": 100, "output_tokens": 50}
    router._mock_usage = mock_usage
    router._response_queue = []
    router._default_response = "{}"

    # Setup _call_claude to return (response_str, usage) tuple
    def _call_claude(*args, **kwargs):
        # Get the next response from the queue if set
        if router._response_queue:
            response_str = router._response_queue.pop(0)
        else:
            response_str = router._default_response
        return (response_str, mock_usage)

    router._call_claude = MagicMock(side_effect=_call_claude)
    # Also setup _call_claude_with_cache with same behavior
    router._call_claude_with_cache = MagicMock(side_effect=_call_claude)
    return router


def setup_ai_responses(router, responses: list):
    """Helper to set up a sequence of AI response strings on the mock router.

    Args:
        router: The mock AI router
        responses: List of response content strings (JSON strings)
    """
    # Extract content string from MagicMock objects if needed
    response_strings = []
    for r in responses:
        if hasattr(r, 'content'):
            response_strings.append(r.content)
        else:
            response_strings.append(str(r))
    router._response_queue = response_strings


@pytest.fixture
def mock_template_renderer():
    """Create a mock template renderer with Four Valets methods."""
    renderer = MagicMock()
    renderer.render_grimaud.return_value = "Grimaud prompt"
    renderer.render_bazin.return_value = "Bazin prompt"
    renderer.render_planchet.return_value = "Planchet prompt"
    renderer.render_mousqueton.return_value = "Mousqueton prompt"
    renderer._get_briefing.return_value = ""
    return renderer


@pytest.fixture
def mock_context_searcher():
    """Create a mock context searcher."""
    from datetime import datetime, timezone

    from src.sancho.context_searcher import NoteContextBlock, StructuredContext

    searcher = AsyncMock()

    async def mock_search(*args, **kwargs):
        return StructuredContext(
            query_entities=[],
            search_timestamp=datetime.now(timezone.utc),
            sources_searched=["notes"],
            notes=[
                NoteContextBlock(
                    note_id="note-001",
                    title="Projet Alpha",
                    note_type="projet",
                    summary="Projet de développement logiciel",
                    relevance=0.85,
                )
            ],
            calendar=[],
            tasks=[],
            emails=[],
            entity_profiles={},
            conflicts=[],
        )

    searcher.search_for_entities.side_effect = mock_search
    return searcher


@pytest.fixture
def four_valets_config():
    """Create a FourValetsConfig for E2E tests."""
    return FourValetsConfig(
        enabled=True,
        fallback_to_legacy=True,
        grimaud_early_stop_confidence=0.95,
        planchet_stop_confidence=0.90,
    )


@pytest.fixture
def multi_pass_config(four_valets_config):
    """Create a MultiPassConfig with Four Valets enabled."""
    return MultiPassConfig(
        four_valets=four_valets_config,
    )


# ============================================================================
# E2E Tests: Early Stop Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_otp_email_early_stop(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test that OTP emails trigger early stop at Grimaud."""
    # Load fixture
    fixture = load_email_fixture("otp_boursobank")
    event = create_event_from_fixture(fixture)

    # Configure mock to return early stop response
    mock_response = MagicMock()
    mock_response.content = create_grimaud_early_stop_response(
        action="delete",
        reason="Code OTP - contenu éphémère"
    )
    mock_response.model_id = "claude-3-5-haiku-20241022"
    setup_ai_responses(mock_ai_router, [mock_response])

    # Create analyzer
    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    # Run analysis
    result = await analyzer.analyze(event)

    # Verify early stop
    assert result.stopped_at == "grimaud"
    assert result.action == "delete"
    assert len(result.pass_history) == 1
    assert result.pass_history[0].early_stop is True
    assert mock_ai_router._call_claude_with_cache.call_count == 1  # Only Grimaud called


@pytest.mark.asyncio
async def test_e2e_spam_email_early_stop(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test that spam emails trigger early stop at Grimaud."""
    fixture = load_email_fixture("spam_promo")
    event = create_event_from_fixture(fixture)

    mock_response = MagicMock()
    mock_response.content = create_grimaud_early_stop_response(
        action="delete",
        reason="Spam promotionnel détecté"
    )
    mock_response.model_id = "claude-3-5-haiku-20241022"
    setup_ai_responses(mock_ai_router, [mock_response])

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "grimaud"
    assert result.action == "delete"
    assert result.pass_history[0].early_stop is True


@pytest.mark.asyncio
async def test_e2e_newsletter_early_stop(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test that newsletters trigger early stop at Grimaud with delete action.

    Note: Early stop requires action='delete' AND high confidence (>95%).
    Newsletters with archive action will go through the full pipeline.
    """
    fixture = load_email_fixture("newsletter_techcrunch")
    event = create_event_from_fixture(fixture)

    # For early stop, action must be "delete" (not archive)
    mock_response = MagicMock()
    mock_response.content = create_grimaud_early_stop_response(
        action="delete",
        reason="Newsletter sans valeur extractible"
    )
    mock_response.model_id = "claude-3-5-haiku-20241022"
    setup_ai_responses(mock_ai_router, [mock_response])

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "grimaud"
    assert result.action == "delete"
    assert len(result.pass_history) == 1


@pytest.mark.asyncio
async def test_e2e_calendar_reminder_early_stop(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test that calendar reminders trigger early stop."""
    fixture = load_email_fixture("calendar_reminder")
    event = create_event_from_fixture(fixture)

    mock_response = MagicMock()
    mock_response.content = create_grimaud_early_stop_response(
        action="delete",
        reason="Rappel calendrier automatique"
    )
    mock_response.model_id = "claude-3-5-haiku-20241022"
    setup_ai_responses(mock_ai_router, [mock_response])

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "grimaud"
    assert result.action == "delete"


# ============================================================================
# E2E Tests: Full Pipeline (Planchet Conclusion)
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_business_meeting_full_pipeline(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test business meeting goes through full pipeline to Planchet."""
    fixture = load_email_fixture("business_meeting_invite")
    event = create_event_from_fixture(fixture)

    # Configure responses for Grimaud -> Bazin -> Planchet
    responses = [
        # Grimaud: continue
        MagicMock(
            content=create_grimaud_continue_response([
                {"info": "Réunion budget Q1 le 25 janvier", "type": "evenement", "importance": "haute"}
            ]),
            model_id="claude-3-5-haiku-20241022"
        ),
        # Bazin: enrich with context
        MagicMock(
            content=create_bazin_response(notes_used=["Sophie Martin", "Projet Alpha"]),
            model_id="claude-3-5-haiku-20241022"
        ),
        # Planchet: conclude
        MagicMock(
            content=create_planchet_conclude_response([
                {"info": "Réunion budget Q1", "type": "evenement", "importance": "haute", "calendar": True},
                {"info": "Date: 25 janvier 14h", "type": "deadline", "importance": "haute"}
            ]),
            model_id="claude-3-5-haiku-20241022"
        ),
    ]
    setup_ai_responses(mock_ai_router, responses)

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "planchet"
    assert result.action == "archive"
    assert len(result.pass_history) == 3  # Grimaud, Bazin, Planchet
    assert mock_ai_router._call_claude_with_cache.call_count == 3


@pytest.mark.asyncio
async def test_e2e_invoice_full_pipeline(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test invoice email goes through to Planchet with financial extractions."""
    fixture = load_email_fixture("invoice_supplier")
    event = create_event_from_fixture(fixture)

    responses = [
        MagicMock(
            content=create_grimaud_continue_response([
                {"info": "Facture CloudHost 531,60€", "type": "montant", "importance": "haute"}
            ]),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_bazin_response(),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_planchet_conclude_response([
                {"info": "Facture 531,60€ TTC", "type": "montant", "importance": "haute"},
                {"info": "Échéance: 15 février 2026", "type": "deadline", "importance": "haute", "omnifocus": True}
            ]),
            model_id="claude-3-5-haiku-20241022"
        ),
    ]
    setup_ai_responses(mock_ai_router, responses)

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "planchet"
    assert len(result.pass_history) == 3


@pytest.mark.asyncio
async def test_e2e_project_update_with_context(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test project update goes through full pipeline to Planchet."""
    fixture = load_email_fixture("project_update")
    event = create_event_from_fixture(fixture)

    responses = [
        MagicMock(
            content=create_grimaud_continue_response([
                {"info": "Projet Alpha: module auth 100%", "type": "fait", "importance": "moyenne"}
            ]),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_bazin_response(notes_used=["Projet Alpha", "Thomas Leclerc"]),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_planchet_conclude_response([
                {"info": "Module auth terminé", "type": "fait", "importance": "moyenne", "note_cible": "Projet Alpha"},
                {"info": "Jalon 31 janvier: MVP", "type": "deadline", "importance": "haute", "note_cible": "Projet Alpha"},
                {"info": "Budget restant: 12 500€", "type": "montant", "importance": "moyenne", "note_cible": "Projet Alpha"}
            ]),
            model_id="claude-3-5-haiku-20241022"
        ),
    ]
    setup_ai_responses(mock_ai_router, responses)

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "planchet"
    assert len(result.pass_history) == 3
    # Note: context_searcher is not directly called in Four Valets pipeline
    # Context is retrieved via template_renderer.render_bazin


# ============================================================================
# E2E Tests: Mousqueton Arbitrage
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_urgent_deadline_mousqueton(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test urgent deadline escalates to Mousqueton for high stakes."""
    fixture = load_email_fixture("urgent_deadline")
    event = create_event_from_fixture(fixture)

    responses = [
        MagicMock(
            content=create_grimaud_continue_response([
                {"info": "Contrat Nexus 45k€ deadline vendredi", "type": "deadline", "importance": "haute"}
            ]),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_bazin_response(notes_used=["Marc Dupont", "Nexus Inc"]),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_planchet_escalate_response(),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_mousqueton_response([
                {"info": "Contrat Nexus: signer avant vendredi 17h", "type": "engagement", "importance": "haute", "omnifocus": True},
                {"info": "Montant: 45 000€", "type": "montant", "importance": "haute"}
            ]),
            model_id="claude-3-5-sonnet-20241022"
        ),
    ]
    setup_ai_responses(mock_ai_router, responses)

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "mousqueton"
    assert len(result.pass_history) == 4  # All four valets
    assert mock_ai_router._call_claude_with_cache.call_count == 4


@pytest.mark.asyncio
async def test_e2e_conflict_requires_mousqueton(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test conflicting information requires Mousqueton arbitrage."""
    fixture = load_email_fixture("conflict_decision")
    event = create_event_from_fixture(fixture)

    responses = [
        MagicMock(
            content=create_grimaud_continue_response([
                {"info": "Date livraison: 28 janvier ou 4 février?", "type": "fait", "importance": "haute"}
            ]),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_bazin_response(notes_used=["Marie", "Thomas", "Projet Beta"]),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_planchet_escalate_response(),
            model_id="claude-3-5-haiku-20241022"
        ),
        MagicMock(
            content=create_mousqueton_response([
                {"info": "Date confirmée: 4 février (retard fournisseur)", "type": "decision", "importance": "haute"},
                {"info": "Budget validé: 32k€ (comité)", "type": "decision", "importance": "haute"}
            ]),
            model_id="claude-3-5-sonnet-20241022"
        ),
    ]
    setup_ai_responses(mock_ai_router, responses)

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "mousqueton"
    assert len(result.pass_history) == 4
    # Verify Planchet flagged need for Mousqueton
    planchet_pass = result.pass_history[2]
    assert planchet_pass.needs_mousqueton is True


# ============================================================================
# E2E Tests: Edge Cases
# ============================================================================


@pytest.mark.skip(reason="Legacy fallback removed - Four Valets is always used")
@pytest.mark.asyncio
async def test_e2e_fallback_to_legacy_on_error(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test fallback to legacy pipeline when Four Valets fails."""
    fixture = load_email_fixture("business_meeting_invite")
    event = create_event_from_fixture(fixture)

    # Create a sequence: first call raises exception, second returns response string
    call_count = [0]
    mock_usage = {"input_tokens": 100, "output_tokens": 50}

    # Legacy response must be a string, not a MagicMock
    legacy_response_str = json.dumps({
        "action": "archive",
        "confidence": {
            "entity_confidence": 0.85,
            "action_confidence": 0.85,
            "extraction_confidence": 0.85,
            "completeness": 0.85,
        },
        "extractions": [{"info": "Test", "type": "fait", "importance": "moyenne"}],
        "reasoning": "Legacy analysis"
    })

    def _call_claude_with_error(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("API Error")
        return (legacy_response_str, mock_usage)

    mock_ai_router._call_claude = MagicMock(side_effect=_call_claude_with_error)
    mock_ai_router._call_claude_with_cache = MagicMock(side_effect=_call_claude_with_error)

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    # Should not raise, should fall back to legacy
    result = await analyzer.analyze(event)

    # Verify fallback occurred
    assert result.four_valets_mode is False
    assert result.stopped_at is None  # Legacy doesn't use stopped_at


@pytest.mark.asyncio
async def test_e2e_shipping_notification_no_extraction(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test shipping notifications are deleted without extraction.

    Note: Early stop requires action='delete' AND high confidence (>95%).
    """
    fixture = load_email_fixture("shipping_notification")
    event = create_event_from_fixture(fixture)

    mock_response = MagicMock()
    mock_response.content = create_grimaud_early_stop_response(
        action="delete",
        reason="Notification de livraison - information temporaire"
    )
    mock_response.model_id = "claude-3-5-haiku-20241022"
    setup_ai_responses(mock_ai_router, [mock_response])

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    result = await analyzer.analyze(event)

    assert result.stopped_at == "grimaud"
    assert result.action == "delete"
    assert len(result.extractions) == 0


# ============================================================================
# E2E Tests: Validation
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_all_fixtures_load_correctly():
    """Verify all email fixtures can be loaded and converted to events."""
    fixture_files = list(FIXTURES_DIR.glob("*.json"))
    assert len(fixture_files) >= 12, f"Expected at least 12 fixtures, found {len(fixture_files)}"

    for fixture_file in fixture_files:
        fixture = load_email_fixture(fixture_file.stem)
        event = create_event_from_fixture(fixture)

        # Verify basic event properties
        assert event.event_id is not None
        assert event.title is not None
        assert event.content is not None
        assert event.from_person is not None

        # Verify fixture has expected outcomes
        assert "expected" in fixture
        assert "action" in fixture["expected"]


@pytest.mark.asyncio
async def test_e2e_four_valets_mode_detection(mock_ai_router, mock_template_renderer, mock_context_searcher, multi_pass_config):
    """Test that four_valets_mode is correctly reported in results."""
    fixture = load_email_fixture("otp_boursobank")
    event = create_event_from_fixture(fixture)

    # Test Four Valets mode
    mock_response = MagicMock()
    mock_response.content = create_grimaud_early_stop_response()
    mock_response.model_id = "claude-3-5-haiku-20241022"
    setup_ai_responses(mock_ai_router, [mock_response])

    analyzer = MultiPassAnalyzer(
        ai_router=mock_ai_router,
        template_renderer=mock_template_renderer,
        context_searcher=mock_context_searcher,
        config=multi_pass_config,
    )

    # Four Valets is now always used
    result = await analyzer.analyze(event)
    assert result.four_valets_mode is True
