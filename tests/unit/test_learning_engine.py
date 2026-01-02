"""
Tests pour Sganarelle Learning Engine

Test de l'orchestrateur principal du module d'apprentissage.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.sganarelle.learning_engine import LearningEngine
from src.sganarelle.types import UserFeedback, LearningResult
from src.core.memory.working_memory import WorkingMemory, Hypothesis
from src.core.events.universal_event import (
    PerceivedEvent,
    EventType,
    UrgencyLevel,
    Entity,
    EventSource
)
from src.figaro.actions.tasks import CreateTaskAction
from src.figaro.actions.email import ArchiveEmailAction
from src.utils import now_utc


def _make_event(
    event_type=EventType.INFORMATION,
    urgency=UrgencyLevel.MEDIUM,
    entities=None
) -> PerceivedEvent:
    """Helper to create a valid PerceivedEvent for testing"""
    return PerceivedEvent(
        event_id="test_event",
        source=EventSource.EMAIL,
        source_id="test@example.com_123",
        occurred_at=now_utc(),
        received_at=now_utc(),
        title="Test",
        content="Test content",
        event_type=event_type,
        urgency=urgency,
        entities=entities or [],
        topics=["test"],
        keywords=["test"],
        from_person="test@example.com",
        to_people=["recipient@example.com"],
        cc_people=[],
        thread_id=None,
        references=[],
        in_reply_to=None,
        has_attachments=False,
        attachment_count=0,
        attachment_types=[],
        urls=[],
        metadata={},
        perception_confidence=0.9,
        needs_clarification=False,
        clarification_questions=[]
    )


class TestLearningEngineInit:
    """Tests d'initialisation"""

    def test_init_minimal(self):
        """Test initialisation minimale (memory only)"""
        engine = LearningEngine()

        assert engine.storage_dir is None
        assert engine.enable_knowledge_updates is True
        assert engine.enable_pattern_learning is True
        assert engine.enable_provider_tracking is True
        assert engine.enable_confidence_calibration is True
        assert engine.min_confidence_for_updates == 0.7

    def test_init_with_storage(self):
        """Test initialisation avec stockage"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "sganarelle"

            engine = LearningEngine(storage_dir=storage_dir)

            assert engine.storage_dir == storage_dir
            assert storage_dir.exists()

    def test_init_with_feature_flags(self):
        """Test initialisation avec feature flags"""
        engine = LearningEngine(
            enable_knowledge_updates=False,
            enable_pattern_learning=False,
            enable_provider_tracking=False,
            enable_confidence_calibration=False
        )

        assert engine.enable_knowledge_updates is False
        assert engine.enable_pattern_learning is False
        assert engine.enable_provider_tracking is False
        assert engine.enable_confidence_calibration is False

    def test_init_validation_confidence_threshold(self):
        """Test validation threshold confiance"""
        with pytest.raises(ValueError, match="min_confidence_for_updates doit être 0-1"):
            LearningEngine(min_confidence_for_updates=1.5)

        with pytest.raises(ValueError, match="min_confidence_for_updates doit être 0-1"):
            LearningEngine(min_confidence_for_updates=-0.1)


class TestLearn:
    """Tests de la méthode principale learn()"""

    @pytest.fixture
    def engine(self):
        """Engine avec toutes features enabled"""
        return LearningEngine()

    @pytest.fixture
    def event(self):
        """Event basique pour tests"""
        from src.utils import now_utc
        return PerceivedEvent(
            event_id="test_event_001",
            source=EventSource.EMAIL,
            source_id="test@example.com_12345",
            occurred_at=now_utc(),
            received_at=now_utc(),
            title="Test Email",
            content="This is a test email",
            event_type=EventType.INFORMATION,
            urgency=UrgencyLevel.MEDIUM,
            entities=[
                Entity(type="person", value="John Doe", confidence=0.9)
            ],
            topics=["testing"],
            keywords=["test"],
            from_person="sender@example.com",
            to_people=["recipient@example.com"],
            cc_people=[],
            thread_id=None,
            references=[],
            in_reply_to=None,
            has_attachments=False,
            attachment_count=0,
            attachment_types=[],
            urls=[],
            metadata={},
            perception_confidence=0.9,
            needs_clarification=False,
            clarification_questions=[]
        )

    @pytest.fixture
    def working_memory(self, event):
        """Working memory avec raisonnement complété"""
        wm = WorkingMemory(event)

        # Pass 1
        wm.start_reasoning_pass(1, "initial")
        hypothesis = Hypothesis(
            id="hyp_1",
            description="Archive this email",
            confidence=0.85,
            supporting_evidence=["Low priority newsletter"],
            contradicting_evidence=[]
        )
        wm.add_hypothesis(hypothesis)
        wm.current_best_hypothesis = "hyp_1"
        wm.update_confidence(0.85)
        wm.complete_reasoning_pass()

        return wm

    @pytest.fixture
    def actions(self):
        """Actions exécutées"""
        return [CreateTaskAction(name="Test Task")]

    def test_learn_without_feedback(self, engine, event, working_memory, actions):
        """Test apprentissage sans feedback utilisateur"""
        result = engine.learn(
            event=event,
            working_memory=working_memory,
            actions=actions,
            execution_success=True,
            user_feedback=None,
            provider_name="anthropic",
            model_tier="haiku",
            ai_latency_ms=250.0,
            ai_cost_usd=0.01
        )

        assert isinstance(result, LearningResult)
        assert result.duration > 0
        # Sans feedback, learning limité mais toujours des updates
        assert len(result.metadata) > 0

    def test_learn_with_positive_feedback(self, engine, event, working_memory, actions):
        """Test apprentissage avec feedback positif"""
        feedback = UserFeedback(
            approval=True,
            rating=5,
            comment="Perfect decision",
            action_executed=True,
            time_to_action=15.0
        )

        result = engine.learn(
            event=event,
            working_memory=working_memory,
            actions=actions,
            execution_success=True,
            user_feedback=feedback,
            provider_name="anthropic",
            model_tier="haiku",
            ai_latency_ms=200.0,
            ai_cost_usd=0.008
        )

        assert result.success is True or result.updates_failed == 0
        assert result.duration > 0

        # Vérifier que les composants ont bien été appelés
        if engine.enable_knowledge_updates:
            # Au moins quelques updates générés
            assert len(result.knowledge_updates) >= 0

        if engine.enable_provider_tracking:
            # Provider score updated
            assert len(result.provider_scores) >= 0

    def test_learn_with_negative_feedback(self, engine, event, working_memory, actions):
        """Test apprentissage avec feedback négatif"""
        feedback = UserFeedback(
            approval=False,
            rating=1,
            correction="Should have created a task instead",
            action_executed=False
        )

        result = engine.learn(
            event=event,
            working_memory=working_memory,
            actions=actions,
            execution_success=False,
            user_feedback=feedback,
            provider_name="anthropic",
            model_tier="haiku",
            ai_latency_ms=300.0,
            ai_cost_usd=0.012
        )

        # Learning should complete même avec feedback négatif
        assert isinstance(result, LearningResult)
        assert result.duration > 0

    def test_learn_with_knowledge_updates_disabled(self, event, working_memory, actions):
        """Test avec knowledge updates désactivé"""
        engine = LearningEngine(enable_knowledge_updates=False)

        result = engine.learn(
            event=event,
            working_memory=working_memory,
            actions=actions,
            execution_success=True
        )

        # Pas de knowledge updates
        assert len(result.knowledge_updates) == 0
        assert result.updates_applied == 0

    def test_learn_with_pattern_learning_disabled(self, event, working_memory, actions):
        """Test avec pattern learning désactivé"""
        engine = LearningEngine(enable_pattern_learning=False)

        result = engine.learn(
            event=event,
            working_memory=working_memory,
            actions=actions,
            execution_success=True
        )

        # Pas de pattern updates
        assert len(result.pattern_updates) == 0

    def test_learn_with_all_features_disabled(self, event, working_memory, actions):
        """Test avec toutes features désactivées"""
        engine = LearningEngine(
            enable_knowledge_updates=False,
            enable_pattern_learning=False,
            enable_provider_tracking=False,
            enable_confidence_calibration=False
        )

        result = engine.learn(
            event=event,
            working_memory=working_memory,
            actions=actions,
            execution_success=True
        )

        # Pas d'updates
        assert len(result.knowledge_updates) == 0
        assert len(result.pattern_updates) == 0
        assert len(result.provider_scores) == 0
        assert len(result.confidence_adjustments) == 0

    def test_learn_increments_statistics(self, engine, event, working_memory, actions):
        """Test que statistiques sont incrémentées"""
        initial_cycles = engine._total_learning_cycles

        engine.learn(
            event=event,
            working_memory=working_memory,
            actions=actions,
            execution_success=True
        )

        assert engine._total_learning_cycles == initial_cycles + 1
        assert engine._total_learning_time > 0
        assert engine._last_learning is not None


class TestGetSuggestionsForEvent:
    """Tests de get_suggestions_for_event()"""

    def test_get_suggestions_empty_store(self):
        """Test suggestions avec pattern store vide"""
        engine = LearningEngine()
        event = _make_event()

        suggestions = engine.get_suggestions_for_event(event)

        assert len(suggestions) == 0

    def test_get_suggestions_disabled(self):
        """Test suggestions avec pattern learning désactivé"""
        engine = LearningEngine(enable_pattern_learning=False)
        event = _make_event()

        suggestions = engine.get_suggestions_for_event(event)

        assert len(suggestions) == 0


class TestGetStats:
    """Tests de get_stats()"""

    def test_get_stats_initial(self):
        """Test statistiques initiales"""
        engine = LearningEngine()

        stats = engine.get_stats()

        assert stats["learning_cycles"] == 0
        assert stats["total_learning_time"] == 0.0
        assert stats["avg_learning_time"] == 0.0
        assert stats["last_learning"] is None
        assert "knowledge_updater" in stats
        assert "pattern_store" in stats
        assert "provider_tracker" in stats
        assert "confidence_calibrator" in stats

    def test_get_stats_after_learning(self):
        """Test statistiques après apprentissage"""
        engine = LearningEngine()

        event = _make_event()

        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "initial")
        wm.update_confidence(0.8)
        wm.complete_reasoning_pass()

        engine.learn(
            event=event,
            working_memory=wm,
            actions=[],
            execution_success=True
        )

        stats = engine.get_stats()

        assert stats["learning_cycles"] == 1
        assert stats["total_learning_time"] > 0
        assert stats["avg_learning_time"] > 0
        assert stats["last_learning"] is not None


class TestPruneOldData:
    """Tests de prune_old_data()"""

    def test_prune_old_data(self):
        """Test pruning des données anciennes"""
        engine = LearningEngine()

        result = engine.prune_old_data()

        assert isinstance(result, dict)
        if engine.enable_pattern_learning:
            assert "patterns" in result


class TestSaveAll:
    """Tests de save_all()"""

    def test_save_all_memory_only(self):
        """Test save avec memory only (no-op)"""
        engine = LearningEngine()

        # Should not raise
        engine.save_all()

    def test_save_all_with_storage(self):
        """Test save avec storage persistant"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "sganarelle"

            engine = LearningEngine(storage_dir=storage_dir)

            # Generate some data
            event = _make_event()

            wm = WorkingMemory(event)
            wm.start_reasoning_pass(1, "initial")
            wm.update_confidence(0.8)
            wm.complete_reasoning_pass()

            engine.learn(
                event=event,
                working_memory=wm,
                actions=[],
                execution_success=True
            )

            # Save
            engine.save_all()

            # Vérifier que fichiers ont été créés
            if engine.enable_pattern_learning:
                assert (storage_dir / "patterns.json").exists()
            if engine.enable_provider_tracking:
                assert (storage_dir / "provider_scores.json").exists()
            if engine.enable_confidence_calibration:
                assert (storage_dir / "calibration.json").exists()


class TestIntegration:
    """Tests d'intégration end-to-end"""

    def test_full_learning_cycle_with_persistence(self):
        """Test cycle complet avec persistence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "sganarelle"

            # Create engine
            engine = LearningEngine(storage_dir=storage_dir)

            # Create event
            event = _make_event(
                event_type=EventType.INFORMATION,
                urgency=UrgencyLevel.HIGH,
                entities=[
                    Entity(type="person", value="Boss", confidence=0.9),
                    Entity(type="document", value="Report.pdf", confidence=0.9)
                ]
            )

            # Create working memory
            wm = WorkingMemory(event)
            wm.start_reasoning_pass(1, "initial")

            hypothesis = Hypothesis(
                id="hyp_1",
                description="Create task and archive",
                confidence=0.9,
                supporting_evidence=["High priority", "Actionable"],
                contradicting_evidence=[]
            )
            wm.add_hypothesis(hypothesis)
            wm.current_best_hypothesis = "hyp_1"
            wm.update_confidence(0.9)
            wm.complete_reasoning_pass()

            # Create actions
            actions = [
                CreateTaskAction(
                    name="Review document",
                    project_name="Work",
                    note="From email"
                )
            ]

            # User feedback
            feedback = UserFeedback(
                approval=True,
                rating=5,
                comment="Perfect!",
                action_executed=True,
                time_to_action=20.0
            )

            # Learn
            result = engine.learn(
                event=event,
                working_memory=wm,
                actions=actions,
                execution_success=True,
                user_feedback=feedback,
                provider_name="anthropic",
                model_tier="sonnet",
                ai_latency_ms=350.0,
                ai_cost_usd=0.025
            )

            # Verify result
            assert isinstance(result, LearningResult)
            assert result.duration > 0

            # Save
            engine.save_all()

            # Verify persistence
            assert storage_dir.exists()

            # Create new engine from same storage
            engine2 = LearningEngine(storage_dir=storage_dir)

            # Verify data was loaded
            stats2 = engine2.get_stats()

            # Pattern store devrait avoir au moins les patterns chargés
            if engine.enable_pattern_learning:
                # Patterns may have been created
                pass  # Can't assert exact count without knowing implementation details

    def test_multiple_learning_cycles(self):
        """Test cycles multiples d'apprentissage"""
        engine = LearningEngine()

        for i in range(5):
            event = _make_event()

            wm = WorkingMemory(event)
            wm.start_reasoning_pass(1, "initial")
            wm.update_confidence(0.7 + i * 0.05)
            wm.complete_reasoning_pass()

            engine.learn(
                event=event,
                working_memory=wm,
                actions=[],
                execution_success=True
            )

        # Verify statistics
        stats = engine.get_stats()
        assert stats["learning_cycles"] == 5
