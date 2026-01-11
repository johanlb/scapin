"""
Tests pour WorkflowV2Config

Ce module teste la configuration du Workflow v2.1.
"""

import pytest
from pydantic import ValidationError

from src.core.config_manager import WorkflowV2Config


class TestWorkflowV2Config:
    """Tests pour la classe WorkflowV2Config"""

    def test_default_values(self):
        """Test que les valeurs par défaut sont correctes"""
        config = WorkflowV2Config()

        # Activation
        assert config.enabled is False

        # Modèles
        assert config.default_model == "haiku"
        assert config.escalation_model == "sonnet"
        assert config.escalation_threshold == 0.7

        # Contexte
        assert config.context_notes_count == 3
        assert config.context_note_max_chars == 300
        assert config.event_content_max_chars == 2000

        # Application
        assert config.auto_apply_threshold == 0.85
        assert config.notify_threshold == 0.7

        # OmniFocus
        assert config.omnifocus_enabled is True
        assert config.omnifocus_default_project == "Inbox"

        # Extraction rules
        assert config.min_extraction_importance == "moyenne"
        assert config.extract_decisions is True
        assert config.extract_engagements is True
        assert config.extract_deadlines is True
        assert config.extract_relations is True
        assert config.extract_facts is True

    def test_custom_values(self):
        """Test avec des valeurs personnalisées"""
        config = WorkflowV2Config(
            enabled=True,
            default_model="sonnet",
            escalation_model="opus",
            escalation_threshold=0.6,
            context_notes_count=5,
            auto_apply_threshold=0.9,
            omnifocus_enabled=False,
            omnifocus_default_project="Scapin",
            extract_relations=False,
        )

        assert config.enabled is True
        assert config.default_model == "sonnet"
        assert config.escalation_model == "opus"
        assert config.escalation_threshold == 0.6
        assert config.context_notes_count == 5
        assert config.auto_apply_threshold == 0.9
        assert config.omnifocus_enabled is False
        assert config.omnifocus_default_project == "Scapin"
        assert config.extract_relations is False

    def test_escalation_threshold_bounds(self):
        """Test que escalation_threshold respecte les bornes"""
        # Valid values
        config_low = WorkflowV2Config(escalation_threshold=0.0)
        assert config_low.escalation_threshold == 0.0

        config_high = WorkflowV2Config(escalation_threshold=1.0)
        assert config_high.escalation_threshold == 1.0

        # Invalid values
        with pytest.raises(ValidationError):
            WorkflowV2Config(escalation_threshold=1.5)

        with pytest.raises(ValidationError):
            WorkflowV2Config(escalation_threshold=-0.1)

    def test_auto_apply_threshold_bounds(self):
        """Test que auto_apply_threshold respecte les bornes"""
        # Valid values
        config_low = WorkflowV2Config(auto_apply_threshold=0.0)
        assert config_low.auto_apply_threshold == 0.0

        config_high = WorkflowV2Config(auto_apply_threshold=1.0)
        assert config_high.auto_apply_threshold == 1.0

        # Invalid values
        with pytest.raises(ValidationError):
            WorkflowV2Config(auto_apply_threshold=1.1)

        with pytest.raises(ValidationError):
            WorkflowV2Config(auto_apply_threshold=-0.5)

    def test_notify_threshold_bounds(self):
        """Test que notify_threshold respecte les bornes"""
        config = WorkflowV2Config(notify_threshold=0.5)
        assert config.notify_threshold == 0.5

        with pytest.raises(ValidationError):
            WorkflowV2Config(notify_threshold=2.0)

    def test_context_notes_count_bounds(self):
        """Test que context_notes_count respecte les bornes"""
        # Valid values
        config_min = WorkflowV2Config(context_notes_count=0)
        assert config_min.context_notes_count == 0

        config_max = WorkflowV2Config(context_notes_count=10)
        assert config_max.context_notes_count == 10

        # Invalid values
        with pytest.raises(ValidationError):
            WorkflowV2Config(context_notes_count=-1)

        with pytest.raises(ValidationError):
            WorkflowV2Config(context_notes_count=11)

    def test_context_note_max_chars_bounds(self):
        """Test que context_note_max_chars respecte les bornes"""
        # Valid values
        config_min = WorkflowV2Config(context_note_max_chars=50)
        assert config_min.context_note_max_chars == 50

        config_max = WorkflowV2Config(context_note_max_chars=1000)
        assert config_max.context_note_max_chars == 1000

        # Invalid values
        with pytest.raises(ValidationError):
            WorkflowV2Config(context_note_max_chars=49)

        with pytest.raises(ValidationError):
            WorkflowV2Config(context_note_max_chars=1001)

    def test_event_content_max_chars_bounds(self):
        """Test que event_content_max_chars respecte les bornes"""
        # Valid values
        config_min = WorkflowV2Config(event_content_max_chars=500)
        assert config_min.event_content_max_chars == 500

        config_max = WorkflowV2Config(event_content_max_chars=10000)
        assert config_max.event_content_max_chars == 10000

        # Invalid values
        with pytest.raises(ValidationError):
            WorkflowV2Config(event_content_max_chars=499)

        with pytest.raises(ValidationError):
            WorkflowV2Config(event_content_max_chars=10001)

    def test_extraction_toggles(self):
        """Test que les toggles d'extraction fonctionnent"""
        # Désactiver toutes les extractions
        config = WorkflowV2Config(
            extract_decisions=False,
            extract_engagements=False,
            extract_deadlines=False,
            extract_relations=False,
            extract_facts=False,
        )

        assert config.extract_decisions is False
        assert config.extract_engagements is False
        assert config.extract_deadlines is False
        assert config.extract_relations is False
        assert config.extract_facts is False

    def test_model_dict_serialization(self):
        """Test que la config peut être sérialisée en dict"""
        config = WorkflowV2Config(enabled=True)
        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert config_dict["enabled"] is True
        assert config_dict["default_model"] == "haiku"
        assert "escalation_threshold" in config_dict

    def test_typical_production_config(self):
        """Test d'une configuration typique de production"""
        config = WorkflowV2Config(
            enabled=True,
            escalation_threshold=0.75,
            auto_apply_threshold=0.90,
            notify_threshold=0.65,
            context_notes_count=5,
            omnifocus_enabled=True,
            omnifocus_default_project="Inbox",
        )

        # Vérifier que c'est une config raisonnable
        assert config.escalation_threshold < config.auto_apply_threshold
        assert config.notify_threshold < config.escalation_threshold
        assert config.context_notes_count >= 3

    def test_minimal_context_config(self):
        """Test configuration sans contexte"""
        config = WorkflowV2Config(
            context_notes_count=0,
            event_content_max_chars=500,
        )

        assert config.context_notes_count == 0
        assert config.event_content_max_chars == 500
