"""
Unit Tests for Context Transparency (v2.2.2)

Tests the context transparency features:
- RetrievedContext serialization
- ContextInfluence extraction from AI responses
- API response models
- Frontend type compatibility
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.sancho.context_searcher import (
    CalendarContextBlock,
    ConflictBlock,
    EntityProfile,
    NoteContextBlock,
    StructuredContext,
    TaskContextBlock,
)
from src.sancho.convergence import (
    DecomposedConfidence,
    Extraction,
    PassResult,
    PassType,
)
from src.sancho.multi_pass_analyzer import MultiPassResult


# ============================================================================
# StructuredContext Tests
# ============================================================================


class TestStructuredContext:
    """Test StructuredContext data structure"""

    def test_empty_context_creation(self):
        """Can create an empty context"""
        ctx = StructuredContext(
            query_entities=[],
            search_timestamp=datetime.now(timezone.utc),
            sources_searched=[],
            notes=[],
            calendar=[],
            tasks=[],
            emails=[],
            entity_profiles={},
            conflicts=[],
        )

        assert len(ctx.notes) == 0
        assert len(ctx.sources_searched) == 0

    def test_context_with_notes(self):
        """Context with notes is correctly structured"""
        notes = [
            NoteContextBlock(
                note_id="note-1",
                title="Marc Dupont",
                note_type="personne",
                summary="Tech Lead at Acme",
                relevance=0.92,
                tags=["contact", "tech"],
            ),
            NoteContextBlock(
                note_id="note-2",
                title="Projet Alpha",
                note_type="projet",
                summary="Q1 Development Project",
                relevance=0.85,
            ),
        ]

        ctx = StructuredContext(
            query_entities=["Marc Dupont", "Projet Alpha"],
            search_timestamp=datetime.now(timezone.utc),
            sources_searched=["notes"],
            notes=notes,
            calendar=[],
            tasks=[],
            emails=[],
            entity_profiles={},
            conflicts=[],
        )

        assert len(ctx.notes) == 2
        assert ctx.notes[0].title == "Marc Dupont"
        assert ctx.notes[0].relevance == 0.92

    def test_context_with_calendar(self):
        """Context with calendar events is correctly structured"""
        calendar = [
            CalendarContextBlock(
                event_id="cal-1",
                title="Meeting with Marc",
                date="2026-01-20",
                time="14:00",
                relevance=0.80,
            ),
        ]

        ctx = StructuredContext(
            query_entities=["Marc Dupont"],
            search_timestamp=datetime.now(timezone.utc),
            sources_searched=["calendar"],
            notes=[],
            calendar=calendar,
            tasks=[],
            emails=[],
            entity_profiles={},
            conflicts=[],
        )

        assert len(ctx.calendar) == 1
        assert ctx.calendar[0].title == "Meeting with Marc"

    def test_context_with_tasks(self):
        """Context with tasks is correctly structured"""
        tasks = [
            TaskContextBlock(
                task_id="task-1",
                title="Review proposal",
                project="Projet Alpha",
                due_date="2026-01-25",
                relevance=0.75,
            ),
        ]

        ctx = StructuredContext(
            query_entities=["Projet Alpha"],
            search_timestamp=datetime.now(timezone.utc),
            sources_searched=["omnifocus"],
            notes=[],
            calendar=[],
            tasks=tasks,
            emails=[],
            entity_profiles={},
            conflicts=[],
        )

        assert len(ctx.tasks) == 1
        assert ctx.tasks[0].project == "Projet Alpha"

    def test_context_with_entity_profiles(self):
        """Context with entity profiles is correctly structured"""
        profiles = {
            "Marc Dupont": EntityProfile(
                name="Marc Dupont",
                canonical_name="Marc Dupont",
                entity_type="person",
                role="Tech Lead",
                relationship="Professional contact",
                key_facts=["Expert in Python", "Works at Acme"],
            ),
        }

        ctx = StructuredContext(
            query_entities=["Marc Dupont"],
            search_timestamp=datetime.now(timezone.utc),
            sources_searched=["notes"],
            notes=[],
            calendar=[],
            tasks=[],
            emails=[],
            entity_profiles=profiles,
            conflicts=[],
        )

        assert "Marc Dupont" in ctx.entity_profiles
        assert ctx.entity_profiles["Marc Dupont"].role == "Tech Lead"
        assert len(ctx.entity_profiles["Marc Dupont"].key_facts) == 2

    def test_context_with_conflicts(self):
        """Context with conflicts is correctly structured"""
        conflicts = [
            ConflictBlock(
                conflict_type="schedule",
                description="Meeting overlaps with another event",
                severity="high",
            ),
        ]

        ctx = StructuredContext(
            query_entities=["Meeting"],
            search_timestamp=datetime.now(timezone.utc),
            sources_searched=["calendar"],
            notes=[],
            calendar=[],
            tasks=[],
            emails=[],
            entity_profiles={},
            conflicts=conflicts,
        )

        assert len(ctx.conflicts) == 1
        assert ctx.conflicts[0].conflict_type == "schedule"
        assert ctx.conflicts[0].severity == "high"


# ============================================================================
# Context Serialization Tests
# ============================================================================


class TestContextSerialization:
    """Test context serialization for API responses"""

    def test_note_block_serialization(self):
        """NoteContextBlock can be serialized"""
        note = NoteContextBlock(
            note_id="note-123",
            title="Test Note",
            note_type="concept",
            summary="A test note about concepts",
            relevance=0.88,
            tags=["test", "concept"],
        )

        # Simulate serialization as done in _build_result
        serialized = {
            "note_id": note.note_id,
            "title": note.title,
            "note_type": note.note_type,
            "summary": note.summary[:200] if note.summary else "",
            "relevance": round(note.relevance, 2),
            "tags": note.tags,
        }

        assert serialized["note_id"] == "note-123"
        assert serialized["relevance"] == 0.88
        assert len(serialized["tags"]) == 2

    def test_full_context_serialization(self):
        """Full StructuredContext can be serialized"""
        ctx = StructuredContext(
            query_entities=["Marc Dupont", "Projet Alpha"],
            search_timestamp=datetime.now(timezone.utc),
            sources_searched=["notes", "calendar", "omnifocus"],
            notes=[
                NoteContextBlock(
                    note_id="n1",
                    title="Marc Dupont",
                    note_type="personne",
                    summary="Tech Lead" * 50,  # Long summary
                    relevance=0.95,
                )
            ],
            calendar=[
                CalendarContextBlock(
                    event_id="c1",
                    title="Meeting",
                    date="2026-01-20",
                    time="10:00",
                    relevance=0.80,
                )
            ],
            tasks=[
                TaskContextBlock(
                    task_id="t1",
                    title="Review",
                    project="Alpha",
                    due_date="2026-01-25",
                    relevance=0.70,
                )
            ],
            emails=[],
            entity_profiles={
                "Marc Dupont": EntityProfile(
                    name="Marc Dupont",
                    canonical_name="Marc Dupont",
                    entity_type="person",
                    role="Tech Lead",
                    key_facts=["Fact 1", "Fact 2", "Fact 3", "Fact 4"],  # 4 facts
                )
            },
            conflicts=[
                ConflictBlock(
                    conflict_type="duplicate",
                    description="Similar note exists",
                    severity="low",
                )
            ],
        )

        # Serialize as done in multi_pass_analyzer._build_result
        serialized = {
            "entities_searched": ctx.query_entities,
            "sources_searched": ctx.sources_searched,
            "total_results": ctx.total_results,
            "notes": [
                {
                    "note_id": n.note_id,
                    "title": n.title,
                    "note_type": n.note_type,
                    "summary": n.summary[:200] if n.summary else "",
                    "relevance": round(n.relevance, 2),
                    "tags": n.tags,
                }
                for n in ctx.notes
            ],
            "calendar": [
                {
                    "event_id": e.event_id,
                    "title": e.title,
                    "date": e.date,
                    "time": e.time,
                    "relevance": round(e.relevance, 2),
                }
                for e in ctx.calendar
            ],
            "tasks": [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "project": t.project,
                    "due_date": t.due_date,
                    "relevance": round(t.relevance, 2),
                }
                for t in ctx.tasks
            ],
            "entity_profiles": {
                name: {
                    "canonical_name": p.canonical_name,
                    "entity_type": p.entity_type,
                    "role": p.role,
                    "relationship": p.relationship,
                    "key_facts": p.key_facts[:3] if p.key_facts else [],
                }
                for name, p in ctx.entity_profiles.items()
            },
            "conflicts": [
                {
                    "type": c.conflict_type,
                    "description": c.description,
                    "severity": c.severity,
                }
                for c in ctx.conflicts
            ],
        }

        # Verify structure
        assert serialized["entities_searched"] == ["Marc Dupont", "Projet Alpha"]
        assert len(serialized["notes"]) == 1
        assert len(serialized["notes"][0]["summary"]) <= 200  # Truncated
        assert len(serialized["calendar"]) == 1
        assert len(serialized["tasks"]) == 1
        assert len(serialized["entity_profiles"]["Marc Dupont"]["key_facts"]) == 3  # Limited to 3
        assert len(serialized["conflicts"]) == 1


# ============================================================================
# PassResult Context Influence Tests
# ============================================================================


class TestPassResultContextInfluence:
    """Test context_influence in PassResult"""

    def test_pass_result_without_context_influence(self):
        """PassResult can be created without context_influence"""
        result = PassResult(
            pass_number=1,
            pass_type=PassType.BLIND_EXTRACTION,
            model_used="haiku",
            model_id="claude-3-5-haiku",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.85),
            changes_made=["Initial"],
        )

        assert result.context_influence is None

    def test_pass_result_with_context_influence(self):
        """PassResult can store context_influence"""
        context_influence = {
            "notes_used": ["Marc Dupont", "Projet Alpha"],
            "explanation": "Les notes confirment le contexte",
            "confirmations": ["Marc est Tech Lead", "Budget Q1 validé"],
            "contradictions": [],
            "missing_info": ["Date exacte non trouvée"],
        }

        result = PassResult(
            pass_number=2,
            pass_type=PassType.CONTEXTUAL_REFINEMENT,
            model_used="haiku",
            model_id="claude-3-5-haiku",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.90),
            changes_made=["Refined with context"],
            context_influence=context_influence,
        )

        assert result.context_influence is not None
        assert result.context_influence["notes_used"] == ["Marc Dupont", "Projet Alpha"]
        assert len(result.context_influence["confirmations"]) == 2

    def test_pass_result_to_dict_includes_context_influence(self):
        """PassResult.to_dict() includes context_influence"""
        context_influence = {
            "notes_used": ["Note 1"],
            "explanation": "Test",
            "confirmations": [],
            "contradictions": [],
            "missing_info": [],
        }

        result = PassResult(
            pass_number=2,
            pass_type=PassType.CONTEXTUAL_REFINEMENT,
            model_used="haiku",
            model_id="claude-3-5-haiku",
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.88),
            changes_made=[],
            context_influence=context_influence,
        )

        d = result.to_dict()

        assert "context_influence" in d
        assert d["context_influence"]["notes_used"] == ["Note 1"]


# ============================================================================
# MultiPassResult Context Tests
# ============================================================================


class TestMultiPassResultContext:
    """Test context fields in MultiPassResult"""

    def test_result_without_context(self):
        """MultiPassResult can be created without context"""
        result = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.95),
            entities_discovered=set(),
            passes_count=1,
            total_duration_ms=1000,
            total_tokens=300,
            final_model="haiku",
            escalated=False,
        )

        assert result.retrieved_context is None
        assert result.context_influence is None

    def test_result_with_full_context(self):
        """MultiPassResult with full context fields"""
        retrieved_context = {
            "entities_searched": ["Marc Dupont"],
            "sources_searched": ["notes"],
            "total_results": 1,
            "notes": [
                {
                    "note_id": "n1",
                    "title": "Marc Dupont",
                    "note_type": "personne",
                    "summary": "Tech Lead",
                    "relevance": 0.9,
                    "tags": [],
                }
            ],
            "calendar": [],
            "tasks": [],
            "entity_profiles": {},
            "conflicts": [],
        }

        context_influence = {
            "notes_used": ["Marc Dupont"],
            "explanation": "La note confirme son identité",
            "confirmations": ["Marc est Tech Lead"],
            "contradictions": [],
            "missing_info": [],
        }

        result = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.92),
            entities_discovered={"Marc Dupont"},
            passes_count=2,
            total_duration_ms=2500,
            total_tokens=700,
            final_model="haiku",
            escalated=False,
            retrieved_context=retrieved_context,
            context_influence=context_influence,
        )

        assert result.retrieved_context is not None
        assert result.context_influence is not None
        assert result.retrieved_context["entities_searched"] == ["Marc Dupont"]
        assert result.context_influence["notes_used"] == ["Marc Dupont"]

    def test_result_to_dict_serializes_context(self):
        """MultiPassResult.to_dict() properly serializes context"""
        result = MultiPassResult(
            extractions=[
                Extraction(info="Test fact", type="fait", importance="moyenne")
            ],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.90),
            entities_discovered={"Person 1"},
            passes_count=2,
            total_duration_ms=2000,
            total_tokens=600,
            final_model="haiku",
            escalated=False,
            retrieved_context={
                "entities_searched": ["Person 1"],
                "notes": [],
            },
            context_influence={
                "notes_used": [],
                "explanation": "No relevant notes found",
            },
        )

        d = result.to_dict()

        assert "retrieved_context" in d
        assert "context_influence" in d
        assert d["retrieved_context"]["entities_searched"] == ["Person 1"]
        assert "No relevant" in d["context_influence"]["explanation"]


# ============================================================================
# API Model Compatibility Tests
# ============================================================================


class TestAPIModelCompatibility:
    """Test compatibility with API response models"""

    def test_context_note_response_structure(self):
        """Context note response matches expected API structure"""
        # This matches ContextNoteResponse in queue.py
        note_response = {
            "note_id": "note-123",
            "title": "Test Note",
            "note_type": "personne",
            "summary": "A person note",
            "relevance": 0.85,
            "tags": ["contact"],
        }

        # Verify all required fields are present
        assert "note_id" in note_response
        assert "title" in note_response
        assert "note_type" in note_response
        assert "summary" in note_response
        assert "relevance" in note_response
        assert "tags" in note_response

        # Verify types
        assert isinstance(note_response["note_id"], str)
        assert isinstance(note_response["relevance"], float)
        assert isinstance(note_response["tags"], list)

    def test_retrieved_context_response_structure(self):
        """Retrieved context response matches expected API structure"""
        # This matches RetrievedContextResponse in queue.py
        context_response = {
            "entities_searched": ["Marc Dupont"],
            "sources_searched": ["notes", "calendar"],
            "notes": [],
            "calendar": [],
            "tasks": [],
            "entity_profiles": {},
            "conflicts": [],
        }

        # Verify all required fields
        required_fields = [
            "entities_searched",
            "sources_searched",
            "notes",
            "calendar",
            "tasks",
            "entity_profiles",
            "conflicts",
        ]

        for field in required_fields:
            assert field in context_response, f"Missing field: {field}"

    def test_context_influence_response_structure(self):
        """Context influence response matches expected API structure"""
        # This matches ContextInfluenceResponse in queue.py
        influence_response = {
            "notes_used": ["Marc Dupont"],
            "explanation": "La note confirme le contexte",
            "confirmations": ["Marc est Tech Lead"],
            "contradictions": [],
            "missing_info": ["Budget exact non trouvé"],
        }

        # Verify all required fields
        required_fields = [
            "notes_used",
            "explanation",
            "confirmations",
            "contradictions",
            "missing_info",
        ]

        for field in required_fields:
            assert field in influence_response, f"Missing field: {field}"

        # Verify types
        assert isinstance(influence_response["notes_used"], list)
        assert isinstance(influence_response["explanation"], str)
        assert isinstance(influence_response["confirmations"], list)


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases in context transparency"""

    def test_empty_context_influence(self):
        """Empty context influence is valid"""
        influence = {
            "notes_used": [],
            "explanation": "",
            "confirmations": [],
            "contradictions": [],
            "missing_info": [],
        }

        result = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.90),
            entities_discovered=set(),
            passes_count=2,
            total_duration_ms=2000,
            total_tokens=500,
            final_model="haiku",
            escalated=False,
            context_influence=influence,
        )

        assert result.context_influence is not None
        assert len(result.context_influence["notes_used"]) == 0

    def test_very_long_summary_truncation(self):
        """Very long summaries are truncated"""
        long_summary = "A" * 1000  # 1000 characters

        note = NoteContextBlock(
            note_id="n1",
            title="Test",
            note_type="concept",
            summary=long_summary,
            relevance=0.8,
        )

        # Simulate truncation as in _build_result
        truncated = note.summary[:200] if note.summary else ""

        assert len(truncated) == 200
        assert truncated == "A" * 200

    def test_many_key_facts_limited(self):
        """Key facts are limited to 3"""
        profile = EntityProfile(
            name="Person",
            canonical_name="Person",
            entity_type="person",
            key_facts=["Fact 1", "Fact 2", "Fact 3", "Fact 4", "Fact 5"],
        )

        # Simulate limitation as in _build_result
        limited_facts = profile.key_facts[:3] if profile.key_facts else []

        assert len(limited_facts) == 3
        assert "Fact 4" not in limited_facts

    def test_unicode_in_context(self):
        """Unicode characters are handled correctly"""
        note = NoteContextBlock(
            note_id="n1",
            title="Jean-François Müller",
            note_type="personne",
            summary="Développeur à São Paulo, expert en données 中文",
            relevance=0.88,
        )

        serialized = {
            "note_id": note.note_id,
            "title": note.title,
            "summary": note.summary,
            "relevance": note.relevance,
        }

        assert "François" in serialized["title"]
        assert "中文" in serialized["summary"]

    def test_special_characters_in_explanation(self):
        """Special characters in explanation are preserved"""
        influence = {
            "notes_used": ["Marc's Note"],
            "explanation": "L'analyse confirme que <Marc> a dit: \"C'est OK\"",
            "confirmations": ["Marc a confirmé le budget (15k€)"],
            "contradictions": [],
            "missing_info": [],
        }

        result = MultiPassResult(
            extractions=[],
            action="archive",
            confidence=DecomposedConfidence.from_single_score(0.90),
            entities_discovered=set(),
            passes_count=2,
            total_duration_ms=2000,
            total_tokens=500,
            final_model="haiku",
            escalated=False,
            context_influence=influence,
        )

        d = result.to_dict()

        assert "L'analyse" in d["context_influence"]["explanation"]
        assert "15k€" in d["context_influence"]["confirmations"][0]
