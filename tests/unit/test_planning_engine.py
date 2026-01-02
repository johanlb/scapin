"""
Unit tests for Planchet Planning Engine
"""

from datetime import datetime

from src.core.events.universal_event import (
    EventSource,
    EventType,
    PerceivedEvent,
    UrgencyLevel,
    now_utc,
)
from src.core.memory.working_memory import Hypothesis, WorkingMemory
from src.figaro.actions.base import Action, ActionResult, ExecutionMode, ValidationResult
from src.planchet.planning_engine import PlanningEngine, RiskLevel


# Helper function to create test PerceivedEvent
def create_test_event(
    title: str = "Test Event",
    content: str = "Test content",
    event_type: EventType = EventType.INFORMATION,
    entities: list = None
) -> PerceivedEvent:
    """Create a valid PerceivedEvent for testing"""
    now = now_utc()
    return PerceivedEvent(
        event_id=f"test-{datetime.now().timestamp()}",
        source=EventSource.EMAIL,
        source_id="test-source-123",
        occurred_at=now,
        received_at=now,
        title=title,
        content=content,
        event_type=event_type,
        urgency=UrgencyLevel.MEDIUM,
        entities=entities or [],
        topics=[],
        keywords=[],
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


# Helper function to create test Hypothesis
def create_test_hypothesis(
    hyp_id: str = "h1",
    description: str = "Archive this email",
    confidence: float = 0.95
) -> Hypothesis:
    """Create a valid Hypothesis for testing"""
    return Hypothesis(
        id=hyp_id,
        description=description,
        confidence=confidence,
        supporting_evidence=["Test evidence"],
        contradicting_evidence=[]
    )


# Mock Action for testing
class MockAction(Action):
    def __init__(self, action_id: str, action_type: str, can_undo_val: bool = True, deps: list = None):
        self._action_id = action_id
        self._action_type = action_type
        self._can_undo_val = can_undo_val
        self._deps = deps or []

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return self._action_type

    def validate(self) -> ValidationResult:
        return ValidationResult(valid=True, errors=[], warnings=[])

    def execute(self) -> ActionResult:
        return ActionResult(success=True, duration=1.0, metadata={"action": self})

    def supports_undo(self) -> bool:
        return self._can_undo_val

    def can_undo(self, result: ActionResult) -> bool:
        return self._can_undo_val and result.success

    def undo(self, result: ActionResult) -> bool:
        return True

    def dependencies(self) -> list[str]:
        return self._deps

    def estimated_duration(self) -> float:
        return 1.0


class TestPlanningEngine:
    """Test PlanningEngine functionality"""

    def test_init(self):
        """Test planning engine initialization"""
        engine = PlanningEngine()

        assert engine.auto_approve_threshold == 0.95
        assert engine.risk_tolerance == RiskLevel.MEDIUM

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters"""
        engine = PlanningEngine(
            auto_approve_threshold=0.90,
            risk_tolerance=RiskLevel.LOW
        )

        assert engine.auto_approve_threshold == 0.90
        assert engine.risk_tolerance == RiskLevel.LOW

    def test_plan_with_no_hypothesis(self):
        """Test planning with empty working memory"""
        # Create empty working memory
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)

        engine = PlanningEngine()
        plan = engine.plan(wm)

        assert plan is not None
        assert len(plan.actions) == 0
        assert plan.execution_mode == ExecutionMode.MANUAL
        assert plan.confidence == 0.0

    def test_plan_with_hypothesis_no_actions(self):
        """Test planning with hypothesis but no provided actions"""
        # Create working memory with hypothesis
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")

        hypothesis = create_test_hypothesis(
            hyp_id="h1",
            description="Archive this email",
            confidence=0.95
        )
        wm.add_hypothesis(hypothesis)
        wm.complete_reasoning_pass()

        engine = PlanningEngine()
        plan = engine.plan(wm)

        assert plan is not None
        assert len(plan.actions) == 0  # No actions generated automatically
        assert plan.execution_mode == ExecutionMode.MANUAL

    def test_plan_with_provided_actions(self):
        """Test planning with provided actions"""
        # Create working memory
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")

        hypothesis = create_test_hypothesis(
            hyp_id="h1",
            description="Archive this email",
            confidence=0.96
        )
        wm.add_hypothesis(hypothesis)
        wm.update_confidence(0.96)
        wm.complete_reasoning_pass()

        # Provide actions
        actions = [
            MockAction("action1", "archive_email", can_undo_val=True)
        ]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        assert plan is not None
        assert len(plan.actions) == 1
        assert plan.actions[0].action_id == "action1"
        assert plan.confidence == 0.96
        assert plan.execution_mode == ExecutionMode.AUTO  # High confidence + low risk

    def test_dependency_resolution_simple(self):
        """Test dependency resolution with linear dependencies"""
        # Create working memory
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(create_test_hypothesis(
            hyp_id="h1",
            description="Test",
            confidence=0.95
        ))
        wm.update_confidence(0.95)
        wm.complete_reasoning_pass()

        # Create actions with dependencies: action3 depends on action2, action2 depends on action1
        actions = [
            MockAction("action3", "step3", deps=["action2"]),
            MockAction("action1", "step1", deps=[]),
            MockAction("action2", "step2", deps=["action1"]),
        ]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        # Check topological ordering
        assert len(plan.actions) == 3
        assert plan.actions[0].action_id == "action1"
        assert plan.actions[1].action_id == "action2"
        assert plan.actions[2].action_id == "action3"

    def test_dependency_resolution_complex(self):
        """Test dependency resolution with complex DAG"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(create_test_hypothesis(
            hyp_id="h1",
            description="Test",
            confidence=0.95
        ))
        wm.update_confidence(0.95)
        wm.complete_reasoning_pass()

        # Diamond dependency: action4 depends on action2 and action3,
        # both of which depend on action1
        actions = [
            MockAction("action4", "final", deps=["action2", "action3"]),
            MockAction("action2", "step2", deps=["action1"]),
            MockAction("action3", "step3", deps=["action1"]),
            MockAction("action1", "initial", deps=[]),
        ]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        assert len(plan.actions) == 4
        # action1 must be first
        assert plan.actions[0].action_id == "action1"
        # action4 must be last
        assert plan.actions[3].action_id == "action4"
        # action2 and action3 in middle (order doesn't matter)
        middle_ids = {plan.actions[1].action_id, plan.actions[2].action_id}
        assert middle_ids == {"action2", "action3"}

    def test_risk_assessment_low_risk(self):
        """Test risk assessment for undoable actions"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(create_test_hypothesis(
            hyp_id="h1",
            description="Test",
            confidence=0.95
        ))
        wm.update_confidence(0.95)
        wm.complete_reasoning_pass()

        actions = [MockAction("action1", "archive", can_undo_val=True)]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        assert len(plan.risks) == 1
        assert plan.risks[0].risk_level == RiskLevel.LOW
        assert plan.risks[0].reversible is True

    def test_risk_assessment_medium_risk(self):
        """Test risk assessment for non-undoable actions"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(create_test_hypothesis(
            hyp_id="h1",
            description="Test",
            confidence=0.95
        ))
        wm.update_confidence(0.95)
        wm.complete_reasoning_pass()

        actions = [MockAction("action1", "delete", can_undo_val=False)]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        assert len(plan.risks) == 1
        assert plan.risks[0].risk_level == RiskLevel.MEDIUM
        assert plan.risks[0].reversible is False

    def test_execution_mode_auto(self):
        """Test AUTO execution mode with high confidence and low risk"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(Hypothesis(
            id="h1",
            description="Test",
            confidence=0.96  # Above threshold
        ))
        wm.update_confidence(0.96)
        wm.complete_reasoning_pass()

        actions = [MockAction("action1", "archive", can_undo_val=True)]

        engine = PlanningEngine(auto_approve_threshold=0.95)
        plan = engine.plan(wm, available_actions=actions)

        assert plan.execution_mode == ExecutionMode.AUTO

    def test_execution_mode_review_low_confidence(self):
        """Test REVIEW mode with low confidence"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(Hypothesis(
            id="h1",
            description="Test",
            confidence=0.80  # Below threshold
        ))
        wm.update_confidence(0.80)
        wm.complete_reasoning_pass()

        actions = [MockAction("action1", "archive", can_undo_val=True)]

        engine = PlanningEngine(auto_approve_threshold=0.95)
        plan = engine.plan(wm, available_actions=actions)

        assert plan.execution_mode == ExecutionMode.REVIEW

    def test_execution_mode_review_high_risk(self):
        """Test REVIEW mode with high risk even with high confidence"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(Hypothesis(
            id="h1",
            description="Test",
            confidence=0.96  # High confidence
        ))
        wm.update_confidence(0.96)
        wm.complete_reasoning_pass()

        actions = [MockAction("action1", "delete_permanently", can_undo_val=False)]

        # Set risk tolerance to LOW - even MEDIUM risk should trigger review
        engine = PlanningEngine(
            auto_approve_threshold=0.95,
            risk_tolerance=RiskLevel.LOW
        )
        plan = engine.plan(wm, available_actions=actions)

        assert plan.execution_mode == ExecutionMode.REVIEW

    def test_estimated_duration(self):
        """Test total estimated duration calculation"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(create_test_hypothesis(
            hyp_id="h1",
            description="Test",
            confidence=0.95
        ))
        wm.update_confidence(0.95)
        wm.complete_reasoning_pass()

        actions = [
            MockAction("action1", "step1"),  # 1.0 seconds
            MockAction("action2", "step2"),  # 1.0 seconds
            MockAction("action3", "step3"),  # 1.0 seconds
        ]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        assert plan.estimated_duration == 3.0

    def test_plan_metadata(self):
        """Test plan metadata contains expected fields"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(create_test_hypothesis(
            hyp_id="h1",
            description="Test",
            confidence=0.95
        ))
        wm.update_confidence(0.95)
        wm.complete_reasoning_pass()

        actions = [MockAction("action1", "archive")]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        assert "hypothesis_id" in plan.metadata
        assert plan.metadata["hypothesis_id"] == "h1"
        assert "planning_duration" in plan.metadata
        assert "action_count" in plan.metadata
        assert plan.metadata["action_count"] == 1

    def test_plan_to_dict(self):
        """Test ActionPlan to_dict serialization"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(create_test_hypothesis(
            hyp_id="h1",
            description="Test",
            confidence=0.95
        ))
        wm.update_confidence(0.95)
        wm.complete_reasoning_pass()

        actions = [MockAction("action1", "archive")]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        plan_dict = plan.to_dict()

        assert "actions" in plan_dict
        assert "execution_mode" in plan_dict
        assert "risks" in plan_dict
        assert "rationale" in plan_dict
        assert "estimated_duration" in plan_dict
        assert "confidence" in plan_dict
        assert "metadata" in plan_dict

        assert len(plan_dict["actions"]) == 1
        assert plan_dict["actions"][0]["id"] == "action1"
        assert plan_dict["actions"][0]["type"] == "archive"

    def test_requires_approval(self):
        """Test ActionPlan requires_approval logic"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(Hypothesis(
            id="h1",
            description="Test",
            confidence=0.80  # Low confidence
        ))
        wm.update_confidence(0.80)
        wm.complete_reasoning_pass()

        actions = [MockAction("action1", "archive")]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        # REVIEW mode requires approval
        assert plan.execution_mode == ExecutionMode.REVIEW
        assert plan.requires_approval() is True

    def test_get_action_by_id(self):
        """Test ActionPlan get_action_by_id"""
        event = create_test_event(
            title="Test Email",
            content="Test email",
            event_type=EventType.INFORMATION
        )
        wm = WorkingMemory(event)
        wm.start_reasoning_pass(1, "test")
        wm.add_hypothesis(create_test_hypothesis(
            hyp_id="h1",
            description="Test",
            confidence=0.95
        ))
        wm.update_confidence(0.95)
        wm.complete_reasoning_pass()

        actions = [
            MockAction("action1", "step1"),
            MockAction("action2", "step2"),
        ]

        engine = PlanningEngine()
        plan = engine.plan(wm, available_actions=actions)

        action = plan.get_action_by_id("action2")
        assert action is not None
        assert action.action_id == "action2"

        missing = plan.get_action_by_id("action999")
        assert missing is None
