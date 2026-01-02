"""
Unit tests for Figaro Action Orchestrator
"""


from src.figaro.actions.base import Action, ActionResult, ExecutionMode, ValidationResult
from src.figaro.orchestrator import ActionOrchestrator
from src.planchet.planning_engine import ActionPlan


# Mock Action for testing
class MockAction(Action):
    def __init__(
        self,
        action_id: str,
        action_type: str,
        should_fail: bool = False,
        validation_error: str = None,
        can_undo_val: bool = True,
        undo_fails: bool = False,
        deps: list = None,
        duration: float = 1.0
    ):
        self._action_id = action_id
        self._action_type = action_type
        self._should_fail = should_fail
        self._validation_error = validation_error
        self._can_undo_val = can_undo_val
        self._undo_fails = undo_fails
        self._deps = deps or []
        self._duration = duration
        self._executed = False
        self._undone = False

    @property
    def action_id(self) -> str:
        return self._action_id

    @property
    def action_type(self) -> str:
        return self._action_type

    def validate(self) -> ValidationResult:
        if self._validation_error:
            return ValidationResult(
                valid=False,
                errors=[self._validation_error]
            )
        return ValidationResult(valid=True)

    def execute(self) -> ActionResult:
        if self._should_fail:
            return ActionResult(
                success=False,
                duration=self._duration,
                error=Exception(f"Execution failed for {self.action_id}"),
                metadata={"action": self}
            )

        self._executed = True
        return ActionResult(
            success=True,
            duration=self._duration,
            output={"action_id": self.action_id},
            metadata={
                "action": self,
                "was_executed": True  # Store state for undo
            }
        )

    def can_undo(self, result: ActionResult) -> bool:
        return self._can_undo_val and result.success

    def undo(self, result: ActionResult) -> bool:
        if self._undo_fails:
            return False
        self._undone = True
        return True

    def dependencies(self) -> list[str]:
        return self._deps

    def estimated_duration(self) -> float:
        return self._duration

    @property
    def was_executed(self) -> bool:
        return self._executed

    @property
    def was_undone(self) -> bool:
        return self._undone


class TestActionOrchestrator:
    """Test ActionOrchestrator functionality"""

    def test_init(self):
        """Test orchestrator initialization"""
        orch = ActionOrchestrator()

        assert orch.parallel_execution is False
        assert orch.fail_fast is True

    def test_init_with_params(self):
        """Test initialization with custom parameters"""
        orch = ActionOrchestrator(
            parallel_execution=True,
            fail_fast=False
        )

        assert orch.parallel_execution is True
        assert orch.fail_fast is False

    def test_execute_empty_plan(self):
        """Test executing empty plan"""
        plan = ActionPlan(
            actions=[],
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="No actions needed",
            estimated_duration=0.0,
            confidence=1.0
        )

        orch = ActionOrchestrator()
        result = orch.execute_plan(plan)

        assert result.success is True
        assert len(result.executed_actions) == 0
        assert result.rolled_back is False

    def test_execute_single_action_success(self):
        """Test executing single action successfully"""
        action = MockAction("action1", "test")
        plan = ActionPlan(
            actions=[action],
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=1.0,
            confidence=0.95
        )

        orch = ActionOrchestrator()
        result = orch.execute_plan(plan)

        assert result.success is True
        assert len(result.executed_actions) == 1
        assert result.executed_actions[0].success is True
        assert action.was_executed is True
        assert result.rolled_back is False

    def test_execute_multiple_actions_success(self):
        """Test executing multiple actions successfully"""
        actions = [
            MockAction("action1", "step1"),
            MockAction("action2", "step2"),
            MockAction("action3", "step3")
        ]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=3.0,
            confidence=0.95
        )

        orch = ActionOrchestrator()
        result = orch.execute_plan(plan)

        assert result.success is True
        assert len(result.executed_actions) == 3
        assert all(r.success for r in result.executed_actions)
        assert all(a.was_executed for a in actions)
        assert result.rolled_back is False

    def test_execute_action_failure_with_rollback(self):
        """Test action failure triggers rollback"""
        actions = [
            MockAction("action1", "step1"),  # Success
            MockAction("action2", "step2", should_fail=True),  # Fail
            MockAction("action3", "step3"),  # Should not execute
        ]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=3.0,
            confidence=0.95
        )

        orch = ActionOrchestrator(fail_fast=True)
        result = orch.execute_plan(plan)

        assert result.success is False
        assert len(result.executed_actions) == 2  # action1 + failed action2
        assert result.executed_actions[0].success is True
        assert result.executed_actions[1].success is False
        assert result.rolled_back is True

        # action1 should be undone
        assert actions[0].was_undone is True
        # action2 failed, so no undo
        assert actions[1].was_undone is False
        # action3 never executed
        assert actions[2].was_executed is False

    def test_validation_failure(self):
        """Test validation failure prevents execution"""
        actions = [
            MockAction("action1", "step1", validation_error="Invalid action")
        ]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=1.0,
            confidence=0.95
        )

        orch = ActionOrchestrator()
        result = orch.execute_plan(plan)

        assert result.success is False
        assert len(result.executed_actions) == 0
        assert result.error is not None
        assert "Validation failed" in str(result.error)

    def test_rollback_non_undoable_action(self):
        """Test rollback skips non-undoable actions"""
        actions = [
            MockAction("action1", "step1", can_undo_val=False),  # Not undoable
            MockAction("action2", "step2", should_fail=True),  # Fail
        ]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=2.0,
            confidence=0.95
        )

        orch = ActionOrchestrator(fail_fast=True)
        result = orch.execute_plan(plan)

        assert result.success is False
        assert result.rolled_back is True
        # action1 cannot be undone
        assert actions[0].was_undone is False

    def test_rollback_undo_failure(self):
        """Test rollback continues even if undo fails"""
        actions = [
            MockAction("action1", "step1", undo_fails=True),  # Undo will fail
            MockAction("action2", "step2", should_fail=True),  # Execution fails
        ]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=2.0,
            confidence=0.95
        )

        orch = ActionOrchestrator(fail_fast=True)
        result = orch.execute_plan(plan)

        assert result.success is False
        assert result.rolled_back is True
        # Rollback attempted but failed
        assert actions[0].was_undone is False

    def test_fail_fast_false(self):
        """Test fail_fast=False continues after failure"""
        actions = [
            MockAction("action1", "step1"),  # Success
            MockAction("action2", "step2", should_fail=True),  # Fail
            MockAction("action3", "step3"),  # Should still execute
        ]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=3.0,
            confidence=0.95
        )

        orch = ActionOrchestrator(fail_fast=False)
        result = orch.execute_plan(plan)

        # All actions executed despite failure
        assert len(result.executed_actions) == 3
        assert result.executed_actions[0].success is True
        assert result.executed_actions[1].success is False
        assert result.executed_actions[2].success is True

        # No rollback when fail_fast=False
        assert result.rolled_back is False

    def test_exception_during_execution(self):
        """Test unexpected exception triggers rollback"""
        class BadAction(MockAction):
            def execute(self):
                raise RuntimeError("Unexpected error")

        actions = [
            MockAction("action1", "step1"),
            BadAction("action2", "step2"),
        ]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=2.0,
            confidence=0.95
        )

        orch = ActionOrchestrator()
        result = orch.execute_plan(plan)

        assert result.success is False
        assert result.error is not None
        assert "Unexpected error" in str(result.error)
        assert result.rolled_back is True

        # action1 should be rolled back
        assert actions[0].was_undone is True

    def test_result_to_dict(self):
        """Test ExecutionResult to_dict serialization"""
        actions = [MockAction("action1", "test")]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=1.0,
            confidence=0.95
        )

        orch = ActionOrchestrator()
        result = orch.execute_plan(plan)

        result_dict = result.to_dict()

        assert "success" in result_dict
        assert "executed_count" in result_dict
        assert "successful_count" in result_dict
        assert "duration" in result_dict
        assert "rolled_back" in result_dict
        assert "error" in result_dict
        assert "metadata" in result_dict

        assert result_dict["success"] is True
        assert result_dict["executed_count"] == 1
        assert result_dict["successful_count"] == 1
        assert result_dict["rolled_back"] is False

    def test_orchestrator_repr(self):
        """Test orchestrator string representation"""
        orch = ActionOrchestrator(parallel_execution=True, fail_fast=False)

        repr_str = repr(orch)

        assert "ActionOrchestrator" in repr_str
        assert "parallel=True" in repr_str
        assert "fail_fast=False" in repr_str

    def test_duration_tracking(self):
        """Test execution duration is tracked"""
        actions = [
            MockAction("action1", "step1", duration=0.5),
            MockAction("action2", "step2", duration=0.3),
        ]
        plan = ActionPlan(
            actions=actions,
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=0.8,
            confidence=0.95
        )

        orch = ActionOrchestrator()
        result = orch.execute_plan(plan)

        assert result.success is True
        assert result.duration > 0
        # Check that action durations are tracked correctly
        action_durations = sum(r.duration for r in result.executed_actions)
        assert action_durations == 0.8  # 0.5 + 0.3
        # Real execution time is much faster since actions don't actually sleep
        assert result.duration < 1.0  # Should complete in under 1 second

    def test_metadata_preservation(self):
        """Test action metadata is preserved in results"""
        action = MockAction("action1", "test")
        plan = ActionPlan(
            actions=[action],
            execution_mode=ExecutionMode.AUTO,
            risks=[],
            rationale="Test",
            estimated_duration=1.0,
            confidence=0.95
        )

        orch = ActionOrchestrator()
        result = orch.execute_plan(plan)

        assert len(result.executed_actions) == 1
        action_result = result.executed_actions[0]

        # Metadata should contain reference to action
        assert "action" in action_result.metadata
        assert action_result.metadata["action"] == action
