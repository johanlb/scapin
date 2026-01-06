"""
Cognitive Pipeline - Full Multi-Pass Processing Orchestrator

Connects all cognitive components for intelligent email processing:
1. Trivelin → EmailNormalizer (perception)
2. Sancho → ReasoningEngine (reasoning)
3. Planchet → PlanningEngine (planning)
4. Figaro → ActionOrchestrator (execution)
5. Sganarelle → LearningEngine (learning)

This is the central orchestrator introduced in Phase 1.0 that enables
the full cognitive architecture to be activated via configuration.
"""

import signal
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from src.core.config_manager import ProcessingConfig
from src.core.events import PerceivedEvent
from src.core.events.normalizers.email_normalizer import EmailNormalizer
from src.core.schemas import EmailAnalysis, EmailContent, EmailMetadata
from src.figaro.orchestrator import ActionOrchestrator, ExecutionResult
from src.monitoring.logger import get_logger
from src.planchet.planning_engine import ActionPlan, PlanningEngine
from src.sancho.reasoning_engine import ReasoningEngine, ReasoningResult
from src.sancho.router import AIRouter
from src.sancho.templates import TemplateManager

if TYPE_CHECKING:
    from src.passepartout.context_engine import ContextEngine

logger = get_logger("trivelin.cognitive_pipeline")


# ============================================================================
# TIMEOUT HANDLING
# ============================================================================


class CognitiveTimeoutError(Exception):
    """Raised when cognitive processing exceeds timeout"""
    pass


class _TimeoutHandler:
    """Context manager for timeout handling"""

    def __init__(self, seconds: int, error_message: str = "Processing timed out"):
        self.seconds = seconds
        self.error_message = error_message
        self._old_handler = None

    def _handle_timeout(self, _signum: int, _frame: Any) -> None:
        raise CognitiveTimeoutError(self.error_message)

    def __enter__(self) -> "_TimeoutHandler":
        if self.seconds > 0:
            self._old_handler = signal.signal(signal.SIGALRM, self._handle_timeout)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if self.seconds > 0:
            signal.alarm(0)  # Cancel the alarm
            if self._old_handler is not None:
                signal.signal(signal.SIGALRM, self._old_handler)
        return False  # Don't suppress exceptions


# ============================================================================
# RESULT DATACLASS
# ============================================================================


@dataclass
class CognitivePipelineResult:
    """
    Result of cognitive pipeline processing

    Contains all outputs from the pipeline stages plus metadata
    for debugging and learning.
    """
    # Core outputs
    success: bool
    analysis: Optional[EmailAnalysis]  # Final email analysis (for compatibility)
    event: Optional[PerceivedEvent] = None  # Normalized event
    reasoning_result: Optional[ReasoningResult] = None  # Full reasoning trace
    action_plan: Optional[ActionPlan] = None  # Planned actions
    execution_result: Optional[ExecutionResult] = None  # Execution outcome

    # Status flags
    needs_review: bool = False  # Below confidence threshold
    used_fallback: bool = False  # Fell back to legacy mode
    timed_out: bool = False  # Hit timeout

    # Metrics
    total_duration_seconds: float = 0.0
    stage_durations: dict[str, float] = field(default_factory=dict)

    # Error tracking
    error: Optional[str] = None
    error_stage: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization"""
        return {
            "success": self.success,
            "has_analysis": self.analysis is not None,
            "needs_review": self.needs_review,
            "used_fallback": self.used_fallback,
            "timed_out": self.timed_out,
            "total_duration_seconds": self.total_duration_seconds,
            "stage_durations": self.stage_durations,
            "error": self.error,
            "error_stage": self.error_stage,
            "confidence": self.analysis.confidence if self.analysis else None,
            "action": self.analysis.action.value if self.analysis else None,
        }


# ============================================================================
# COGNITIVE PIPELINE
# ============================================================================


class CognitivePipeline:
    """
    Full Cognitive Pipeline Orchestrator

    Coordinates all valet modules for intelligent email processing:
    - Perception (EmailNormalizer)
    - Reasoning (ReasoningEngine/Sancho)
    - Planning (PlanningEngine/Planchet)
    - Execution (ActionOrchestrator/Figaro)
    - Learning (LearningEngine/Sganarelle) [optional]

    Design Philosophy:
    - Quality over speed (10-20s acceptable for good decisions)
    - Fail-safe with fallback to legacy mode
    - Full observability (all stages logged)
    - Configuration-driven activation

    Example:
        >>> pipeline = CognitivePipeline(ai_router, config)
        >>> result = pipeline.process(metadata, content)
        >>> if result.success:
        ...     print(f"Action: {result.analysis.action}")
    """

    def __init__(
        self,
        ai_router: AIRouter,
        config: Optional[ProcessingConfig] = None,
        template_manager: Optional[TemplateManager] = None,
        context_engine: Optional["ContextEngine"] = None,
        planning_engine: Optional[PlanningEngine] = None,
        orchestrator: Optional[ActionOrchestrator] = None,
        learning_engine: Optional[Any] = None,  # Avoid circular import
    ):
        """
        Initialize cognitive pipeline

        Args:
            ai_router: AI router for LLM calls
            config: Processing configuration (uses defaults if None)
            template_manager: Template manager for prompts
            context_engine: Passepartout context engine for knowledge base retrieval
            planning_engine: Planchet planning engine
            orchestrator: Figaro action orchestrator
            learning_engine: Sganarelle learning engine (optional)
        """
        self.ai_router = ai_router
        self.config = config or ProcessingConfig()
        self.template_manager = template_manager
        self.context_engine = context_engine

        # Initialize reasoning engine (Sancho) with context engine
        self.reasoning_engine = ReasoningEngine(
            ai_router=ai_router,
            template_manager=template_manager,
            context_engine=context_engine,
            max_iterations=self.config.cognitive_max_passes,
            confidence_threshold=self.config.cognitive_confidence_threshold,
            enable_context=context_engine is not None,
            context_top_k=self.config.context_top_k,
            context_min_relevance=self.config.context_min_relevance,
        )

        # Initialize planning engine (Planchet)
        self.planning_engine = planning_engine or PlanningEngine()

        # Initialize orchestrator (Figaro)
        self.orchestrator = orchestrator or ActionOrchestrator()

        # Learning engine is optional (Sganarelle)
        self.learning_engine = learning_engine

        logger.info(
            "CognitivePipeline initialized",
            extra={
                "confidence_threshold": self.config.cognitive_confidence_threshold,
                "timeout_seconds": self.config.cognitive_timeout_seconds,
                "max_passes": self.config.cognitive_max_passes,
                "fallback_enabled": self.config.fallback_on_failure,
                "learning_enabled": learning_engine is not None,
                "context_enabled": context_engine is not None,
            }
        )

    def process(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        auto_execute: bool = False
    ) -> CognitivePipelineResult:
        """
        Process email through full cognitive pipeline

        Stages:
        1. Normalize → PerceivedEvent
        2. Reason → ReasoningResult (multi-pass with confidence convergence)
        3. Plan → ActionPlan (if auto_execute and confident)
        4. Execute → ExecutionResult (if auto_execute and confident)
        5. Learn → Update models (if learning_engine configured)

        Args:
            metadata: Email metadata
            content: Email content
            auto_execute: Whether to execute planned actions automatically

        Returns:
            CognitivePipelineResult with all outputs and metrics
        """
        start_time = time.time()
        stage_durations: dict[str, float] = {}

        try:
            # Apply timeout wrapper
            with _TimeoutHandler(
                self.config.cognitive_timeout_seconds,
                f"Cognitive processing exceeded {self.config.cognitive_timeout_seconds}s timeout"
            ):
                return self._process_internal(
                    metadata, content, auto_execute, start_time, stage_durations
                )

        except CognitiveTimeoutError as e:
            logger.warning(
                "Cognitive processing timed out",
                extra={
                    "email_id": metadata.id,
                    "timeout_seconds": self.config.cognitive_timeout_seconds,
                }
            )
            return CognitivePipelineResult(
                success=False,
                analysis=None,
                timed_out=True,
                total_duration_seconds=time.time() - start_time,
                stage_durations=stage_durations,
                error=str(e),
                error_stage="timeout",
            )

        except Exception as e:
            logger.error(
                "Cognitive pipeline error",
                extra={
                    "email_id": metadata.id,
                    "error": str(e),
                },
                exc_info=True
            )
            return CognitivePipelineResult(
                success=False,
                analysis=None,
                total_duration_seconds=time.time() - start_time,
                stage_durations=stage_durations,
                error=str(e),
                error_stage="unknown",
            )

    def _process_internal(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        auto_execute: bool,
        start_time: float,
        stage_durations: dict[str, float]
    ) -> CognitivePipelineResult:
        """Internal processing logic (without timeout wrapper)"""

        # ----------------------------------------------------------------
        # Stage 1: Normalize (Trivelin)
        # ----------------------------------------------------------------
        stage_start = time.time()
        try:
            event = EmailNormalizer.normalize(metadata, content)
            stage_durations["normalize"] = time.time() - stage_start
            logger.debug(
                "Normalization complete",
                extra={
                    "email_id": metadata.id,
                    "event_type": event.event_type.value,
                    "duration_ms": stage_durations["normalize"] * 1000,
                }
            )
        except Exception as e:
            logger.error(f"Normalization failed: {e}", exc_info=True)
            return CognitivePipelineResult(
                success=False,
                analysis=None,
                total_duration_seconds=time.time() - start_time,
                stage_durations=stage_durations,
                error=str(e),
                error_stage="normalize",
            )

        # ----------------------------------------------------------------
        # Stage 2: Reason (Sancho)
        # ----------------------------------------------------------------
        stage_start = time.time()
        try:
            reasoning_result = self.reasoning_engine.reason(event)
            stage_durations["reason"] = time.time() - stage_start
            logger.debug(
                "Reasoning complete",
                extra={
                    "email_id": metadata.id,
                    "confidence": reasoning_result.confidence,
                    "passes": reasoning_result.passes_executed,
                    "converged": reasoning_result.converged,
                    "duration_ms": stage_durations["reason"] * 1000,
                }
            )
        except Exception as e:
            logger.error(f"Reasoning failed: {e}", exc_info=True)
            return CognitivePipelineResult(
                success=False,
                analysis=None,
                event=event,
                total_duration_seconds=time.time() - start_time,
                stage_durations=stage_durations,
                error=str(e),
                error_stage="reason",
            )

        # Check confidence threshold
        needs_review = reasoning_result.confidence < self.config.cognitive_confidence_threshold
        analysis = reasoning_result.final_analysis

        # If no analysis from reasoning, fail
        if not analysis:
            logger.warning(
                "Reasoning produced no analysis",
                extra={"email_id": metadata.id}
            )
            return CognitivePipelineResult(
                success=False,
                analysis=None,
                event=event,
                reasoning_result=reasoning_result,
                needs_review=True,
                total_duration_seconds=time.time() - start_time,
                stage_durations=stage_durations,
                error="Reasoning produced no analysis",
                error_stage="reason",
            )

        # ----------------------------------------------------------------
        # Stage 3: Plan (Planchet) - Only if auto_execute and confident
        # ----------------------------------------------------------------
        action_plan: Optional[ActionPlan] = None
        execution_result: Optional[ExecutionResult] = None

        if auto_execute and not needs_review:
            stage_start = time.time()
            try:
                action_plan = self.planning_engine.plan(reasoning_result.working_memory)
                stage_durations["plan"] = time.time() - stage_start
                logger.debug(
                    "Planning complete",
                    extra={
                        "email_id": metadata.id,
                        "action_count": len(action_plan.actions),
                        "requires_approval": action_plan.requires_approval(),
                        "duration_ms": stage_durations["plan"] * 1000,
                    }
                )
            except Exception as e:
                logger.error(f"Planning failed: {e}", exc_info=True)
                # Planning failure is non-fatal, continue with analysis
                stage_durations["plan"] = time.time() - stage_start

            # ----------------------------------------------------------------
            # Stage 4: Execute (Figaro) - Only if plan exists and approved
            # ----------------------------------------------------------------
            if action_plan and not action_plan.requires_approval():
                stage_start = time.time()
                try:
                    execution_result = self.orchestrator.execute_plan(action_plan)
                    stage_durations["execute"] = time.time() - stage_start
                    logger.debug(
                        "Execution complete",
                        extra={
                            "email_id": metadata.id,
                            "success": execution_result.success,
                            "executed_count": len(execution_result.executed_actions),
                            "duration_ms": stage_durations["execute"] * 1000,
                        }
                    )
                except Exception as e:
                    logger.error(f"Execution failed: {e}", exc_info=True)
                    stage_durations["execute"] = time.time() - stage_start

        # ----------------------------------------------------------------
        # Stage 5: Learn (Sganarelle) - Optional
        # ----------------------------------------------------------------
        if self.learning_engine:
            stage_start = time.time()
            try:
                # Determine execution success
                exec_success = (
                    execution_result.success
                    if execution_result
                    else False
                )

                # Get actions from plan or empty list
                actions = action_plan.actions if action_plan else []

                self.learning_engine.learn(
                    event=event,
                    working_memory=reasoning_result.working_memory,
                    actions=actions,
                    execution_success=exec_success,
                    user_feedback=None,  # No feedback during processing
                )
                stage_durations["learn"] = time.time() - stage_start
                logger.debug(
                    "Learning complete",
                    extra={
                        "email_id": metadata.id,
                        "duration_ms": stage_durations["learn"] * 1000,
                    }
                )
            except Exception as e:
                logger.error(f"Learning failed: {e}", exc_info=True)
                # Learning failure is non-fatal
                stage_durations["learn"] = time.time() - stage_start

        # ----------------------------------------------------------------
        # Build result
        # ----------------------------------------------------------------
        total_duration = time.time() - start_time

        logger.info(
            "Cognitive pipeline complete",
            extra={
                "email_id": metadata.id,
                "success": True,
                "confidence": analysis.confidence,
                "action": analysis.action.value,
                "needs_review": needs_review,
                "total_duration_seconds": total_duration,
                "stage_durations": stage_durations,
            }
        )

        return CognitivePipelineResult(
            success=True,
            analysis=analysis,
            event=event,
            reasoning_result=reasoning_result,
            action_plan=action_plan,
            execution_result=execution_result,
            needs_review=needs_review,
            used_fallback=False,
            timed_out=False,
            total_duration_seconds=total_duration,
            stage_durations=stage_durations,
        )
