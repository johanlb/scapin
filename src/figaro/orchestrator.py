"""
Action Orchestrator - DAG-based Execution with Rollback

Executes action plans with dependency resolution and rollback support.
"""

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from src.figaro.actions.base import Action, ActionResult
from src.monitoring.logger import get_logger

# Avoid circular import
if TYPE_CHECKING:
    from src.planchet.planning_engine import ActionPlan

logger = get_logger("figaro.orchestrator")


@dataclass
class ExecutionResult:
    """Result of plan execution"""
    success: bool
    executed_actions: list[ActionResult]
    duration: float
    error: Optional[Exception] = None
    rolled_back: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "executed_count": len(self.executed_actions),
            "successful_count": sum(1 for r in self.executed_actions if r.success),
            "duration": self.duration,
            "rolled_back": self.rolled_back,
            "error": str(self.error) if self.error else None,
            "metadata": self.metadata
        }


class ActionOrchestrator:
    """
    DAG-based Action Orchestrator

    Executes action plans with:
    - Dependency resolution (topological ordering)
    - Parallel execution within levels (optional)
    - Automatic rollback on failure
    - Progress tracking

    Usage:
        orchestrator = ActionOrchestrator()
        result = orchestrator.execute_plan(action_plan)
    """

    def __init__(
        self,
        parallel_execution: bool = False,
        fail_fast: bool = True
    ):
        """
        Initialize orchestrator

        Args:
            parallel_execution: Execute independent actions in parallel
                              (requires thread-safe actions)
            fail_fast: Stop execution on first failure
        """
        self.parallel_execution = parallel_execution
        self.fail_fast = fail_fast
        self._executed_pairs: list[tuple[Action, ActionResult]] = []

        logger.info(
            "Initialized ActionOrchestrator",
            extra={
                "parallel_execution": parallel_execution,
                "fail_fast": fail_fast
            }
        )

    def execute_plan(self, plan: "ActionPlan") -> ExecutionResult:
        """
        Execute action plan

        Args:
            plan: ActionPlan from Planchet

        Returns:
            ExecutionResult with status and results
        """
        start_time = time.time()
        self._executed_pairs = []  # Reset for this execution

        logger.info(
            "Starting plan execution",
            extra={
                "action_count": len(plan.actions),
                "execution_mode": plan.execution_mode,
                "confidence": plan.confidence
            }
        )

        try:
            # Validate all actions first
            validation_errors = self._validate_all(plan.actions)
            if validation_errors:
                error_msg = f"Validation failed: {', '.join(validation_errors)}"
                logger.error(error_msg)
                return self._create_failure_result(
                    error=ValueError(error_msg),
                    start_time=start_time,
                    executed_results=[],
                    rolled_back=False
                )

            # Execute actions in order (already topologically sorted by planner)
            for action in plan.actions:
                logger.debug(f"Executing action: {action.action_id}")

                result = action.execute()

                # Store action-result pair for rollback
                self._executed_pairs.append((action, result))

                if not result.success:
                    logger.error(
                        f"Action failed: {action.action_id}",
                        extra={"error": str(result.error)}
                    )

                    if self.fail_fast:
                        # Rollback all executed actions
                        self._rollback()

                        executed_results = [r for _, r in self._executed_pairs]
                        return self._create_failure_result(
                            error=result.error,
                            start_time=start_time,
                            executed_results=executed_results,
                            rolled_back=True
                        )

            # All actions succeeded
            duration = time.time() - start_time
            executed_results = [r for _, r in self._executed_pairs]

            logger.info(
                "Plan execution completed successfully",
                extra={
                    "executed_count": len(executed_results),
                    "duration": duration
                }
            )

            return ExecutionResult(
                success=True,
                executed_actions=executed_results,
                duration=duration
            )

        except Exception as e:
            logger.error(
                f"Plan execution failed with exception: {e}",
                exc_info=True
            )

            # Rollback on unexpected error
            self._rollback()

            executed_results = [r for _, r in self._executed_pairs]
            return self._create_failure_result(
                error=e,
                start_time=start_time,
                executed_results=executed_results,
                rolled_back=True
            )

    def _validate_all(self, actions: list[Action]) -> list[str]:
        """
        Validate all actions before execution

        Args:
            actions: List of actions to validate

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        for action in actions:
            validation = action.validate()
            if not validation.valid:
                for error in validation.errors:
                    errors.append(f"{action.action_id}: {error}")

        return errors

    def _rollback(self) -> None:
        """
        Rollback executed actions in reverse order

        Uses self._executed_pairs to access both actions and results.
        """
        if not self._executed_pairs:
            return

        logger.warning(
            f"Rolling back {len(self._executed_pairs)} actions",
            extra={"action_count": len(self._executed_pairs)}
        )

        # Rollback in reverse order
        for action, result in reversed(self._executed_pairs):
            if not result.success:
                # Skip failed actions (nothing to rollback)
                logger.debug(f"Skipping rollback for failed action: {action.action_id}")
                continue

            if not action.can_undo(result):
                logger.warning(
                    f"Cannot rollback {action.action_id}: undo not supported"
                )
                continue

            try:
                logger.debug(f"Rolling back: {action.action_id}")
                success = action.undo(result)

                if not success:
                    logger.error(f"Rollback failed for: {action.action_id}")
                else:
                    logger.debug(f"Rolled back: {action.action_id}")

            except Exception as e:
                logger.error(
                    f"Rollback error for {action.action_id}: {e}",
                    exc_info=True
                )

        logger.info("Rollback complete")

    def _create_failure_result(
        self,
        error: Exception,
        start_time: float,
        executed_results: list[ActionResult],
        rolled_back: bool = False
    ) -> ExecutionResult:
        """
        Create a standardized failure ExecutionResult

        Args:
            error: The exception that caused the failure
            start_time: When execution started (for duration calculation)
            executed_results: List of ActionResults from executed actions
            rolled_back: Whether rollback was performed

        Returns:
            ExecutionResult with failure status
        """
        return ExecutionResult(
            success=False,
            executed_actions=executed_results,
            duration=time.time() - start_time,
            error=error,
            rolled_back=rolled_back
        )

    def _build_dag(self, actions: list[Action]) -> dict[int, list[Action]]:
        """
        Build DAG levels for parallel execution

        Returns dictionary mapping level → list of actions at that level.
        Actions at the same level have no dependencies on each other.

        Args:
            actions: List of actions (topologically sorted)

        Returns:
            Dict mapping level (int) to list of actions
        """
        # For now, simple sequential execution (each action in its own level)
        # In future, could analyze dependencies and group independent actions
        return {i: [action] for i, action in enumerate(actions)}

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"ActionOrchestrator("
            f"parallel={self.parallel_execution}, "
            f"fail_fast={self.fail_fast})"
        )
