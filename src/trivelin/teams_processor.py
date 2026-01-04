"""
Teams Message Processor

Orchestrates Teams message processing through the cognitive pipeline.

Pipeline:
1. Fetch messages from Teams API
2. Normalize to PerceivedEvent
3. Process through CognitivePipeline (if enabled)
4. Execute actions
5. Update state
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.core.config_manager import TeamsConfig, get_config
from src.core.events import PerceivedEvent
from src.core.state_manager import get_state_manager
from src.integrations.microsoft.auth import MicrosoftAuthenticator
from src.integrations.microsoft.graph_client import GraphClient
from src.integrations.microsoft.models import TeamsMessage
from src.integrations.microsoft.teams_client import TeamsClient
from src.integrations.microsoft.teams_normalizer import TeamsNormalizer
from src.monitoring.logger import get_logger
from src.utils import now_utc

logger = get_logger("trivelin.teams_processor")

# Default limit for processing - prevents overwhelming the system
# Items are always processed oldest-first to handle backlog chronologically
DEFAULT_PROCESSING_LIMIT = 20


@dataclass
class TeamsProcessingResult:
    """Result of processing a single Teams message"""

    message_id: str
    success: bool
    skipped: bool = False
    reason: Optional[str] = None
    actions_taken: list[str] = field(default_factory=list)
    confidence: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message_id": self.message_id,
            "success": self.success,
            "skipped": self.skipped,
            "reason": self.reason,
            "actions_taken": self.actions_taken,
            "confidence": self.confidence,
            "error": self.error,
        }


@dataclass
class TeamsProcessingSummary:
    """Summary of a Teams processing batch"""

    total: int
    successful: int
    failed: int
    skipped: int
    results: list[TeamsProcessingResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=now_utc)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": [r.to_dict() for r in self.results],
        }


class TeamsProcessor:
    """
    Teams message processor

    Orchestrates the Teams message processing pipeline:
    1. Fetch messages from TeamsClient
    2. Normalize via TeamsNormalizer
    3. Process via CognitivePipeline (if enabled)
    4. Execute actions via ActionOrchestrator

    Usage:
        processor = TeamsProcessor()
        summary = await processor.poll_and_process()
    """

    def __init__(
        self,
        teams_client: Optional[TeamsClient] = None,
        normalizer: Optional[TeamsNormalizer] = None,
        config: Optional[TeamsConfig] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize Teams processor

        Args:
            teams_client: Optional pre-configured TeamsClient
            normalizer: Optional pre-configured normalizer
            config: Optional Teams configuration
            data_dir: Directory for token cache and state
        """
        self.config = config or get_config().teams
        self.data_dir = data_dir or Path("data")
        self.state_manager = get_state_manager()
        self._last_poll: Optional[datetime] = None

        # Initialize client if not provided
        if teams_client:
            self.teams_client = teams_client
        else:
            self.teams_client = self._create_teams_client()

        # Initialize normalizer
        self.normalizer = normalizer or TeamsNormalizer()

        # Initialize cognitive pipeline if enabled
        self.cognitive_pipeline = None
        processing_config = get_config().processing
        if processing_config.enable_cognitive_reasoning:
            self._init_cognitive_pipeline()

        logger.info(
            "Teams processor initialized",
            extra={
                "cognitive_enabled": self.cognitive_pipeline is not None,
                "poll_interval": self.config.poll_interval_seconds,
            }
        )

    def _create_teams_client(self) -> TeamsClient:
        """Create Teams client from configuration"""
        if not self.config.account:
            raise ValueError(
                "Microsoft account not configured. "
                "Set TEAMS__ACCOUNT__CLIENT_ID and TEAMS__ACCOUNT__TENANT_ID"
            )

        authenticator = MicrosoftAuthenticator(
            config=self.config.account,
            cache_dir=self.data_dir,
        )
        graph_client = GraphClient(authenticator=authenticator)
        return TeamsClient(graph=graph_client)

    def _init_cognitive_pipeline(self) -> None:
        """Initialize the cognitive pipeline"""
        from src.sancho.router import get_ai_router
        from src.trivelin.cognitive_pipeline import CognitivePipeline

        config = get_config()
        ai_router = get_ai_router(config.ai)

        self.cognitive_pipeline = CognitivePipeline(
            ai_router=ai_router,
            config=config.processing,
        )
        logger.info("Cognitive pipeline initialized for Teams processing")

    async def poll_and_process(
        self,
        limit: int = DEFAULT_PROCESSING_LIMIT,
    ) -> TeamsProcessingSummary:
        """
        Poll for new messages and process them

        Args:
            limit: Maximum messages to process (default: 20)

        Returns:
            Summary of processing results
        """
        logger.info("Polling Teams for new messages")

        summary = TeamsProcessingSummary(
            total=0,
            successful=0,
            failed=0,
            skipped=0,
        )

        try:
            # Fetch recent messages
            messages = await self.teams_client.get_recent_messages(
                limit_per_chat=limit or self.config.max_messages_per_poll,
                since=self._last_poll,
                include_chat_context=True,
            )

            # Update last poll time
            self._last_poll = now_utc()

            logger.info(f"Found {len(messages)} messages to process")
            summary.total = len(messages)

            # Process each message
            for message in messages:
                result = await self._process_message(message)
                summary.results.append(result)

                if result.skipped:
                    summary.skipped += 1
                elif result.success:
                    summary.successful += 1
                else:
                    summary.failed += 1

            summary.completed_at = now_utc()

            logger.info(
                f"Processing complete: {summary.successful} successful, "
                f"{summary.failed} failed, {summary.skipped} skipped"
            )

        except Exception as e:
            logger.error(f"Error during Teams polling: {e}")
            raise

        return summary

    async def _process_message(
        self,
        message: TeamsMessage,
    ) -> TeamsProcessingResult:
        """
        Process a single Teams message

        Args:
            message: TeamsMessage to process

        Returns:
            TeamsProcessingResult
        """
        logger.debug(f"Processing message {message.message_id}")

        try:
            # Normalize to PerceivedEvent
            event = self.normalizer.normalize(message)

            # Check if already processed
            if self._is_processed(event.event_id):
                logger.debug(f"Message {message.message_id} already processed")
                return TeamsProcessingResult(
                    message_id=message.message_id,
                    success=True,
                    skipped=True,
                    reason="Already processed",
                )

            # Process through cognitive pipeline if enabled
            if self.cognitive_pipeline:
                pipeline_result = await self._process_with_pipeline(event)

                # Mark as processed
                self._mark_processed(event.event_id, pipeline_result)

                return TeamsProcessingResult(
                    message_id=message.message_id,
                    success=pipeline_result.get("success", True),
                    actions_taken=pipeline_result.get("actions", []),
                    confidence=pipeline_result.get("confidence"),
                )

            # No cognitive pipeline - just log and mark processed
            logger.info(f"Processed message {message.message_id} (no cognitive pipeline)")
            self._mark_processed(event.event_id, {"mode": "basic"})

            return TeamsProcessingResult(
                message_id=message.message_id,
                success=True,
            )

        except Exception as e:
            logger.error(f"Failed to process message {message.message_id}: {e}")
            return TeamsProcessingResult(
                message_id=message.message_id,
                success=False,
                error=str(e),
            )

    async def _process_with_pipeline(
        self,
        event: PerceivedEvent,
    ) -> dict[str, Any]:
        """
        Process event through cognitive pipeline

        Uses the ReasoningEngine to analyze the event and optionally
        plan/execute actions through Planchet/Figaro.

        Returns dict with:
        - success: bool
        - actions: list[str]
        - confidence: float
        - analysis: Optional analysis result
        """
        logger.debug(f"Processing event {event.event_id} through cognitive pipeline")

        try:
            # Access the reasoning engine from the cognitive pipeline
            reasoning_engine = self.cognitive_pipeline.reasoning_engine

            # Run reasoning on the event
            reasoning_result = reasoning_engine.reason(event)

            actions_taken: list[str] = []
            analysis_dict: dict[str, Any] = {}

            # Extract analysis if available
            if reasoning_result.final_analysis:
                analysis = reasoning_result.final_analysis
                analysis_dict = {
                    "action": analysis.action.value,
                    "category": analysis.category.value if analysis.category else None,
                    "summary": analysis.summary,
                    "priority": analysis.priority.value if analysis.priority else None,
                }

                # If confident and auto-execute is enabled, plan and execute
                if reasoning_result.confidence >= self.cognitive_pipeline.config.cognitive_confidence_threshold:
                    # Plan actions
                    action_plan = self.cognitive_pipeline.planning_engine.plan(
                        reasoning_result.working_memory
                    )

                    # Execute if no approval required
                    if action_plan and not action_plan.requires_approval():
                        execution_result = self.cognitive_pipeline.orchestrator.execute_plan(
                            action_plan
                        )
                        actions_taken = [a.action_type for a in execution_result.executed_actions]

            logger.info(
                f"Pipeline processing complete for {event.event_id}",
                extra={
                    "confidence": reasoning_result.confidence,
                    "converged": reasoning_result.converged,
                    "passes": reasoning_result.passes_executed,
                    "actions_taken": len(actions_taken),
                }
            )

            return {
                "success": True,
                "actions": actions_taken,
                "confidence": reasoning_result.confidence,
                "analysis": analysis_dict,
                "passes": reasoning_result.passes_executed,
                "converged": reasoning_result.converged,
            }

        except Exception as e:
            logger.error(f"Pipeline processing failed for {event.event_id}: {e}")
            return {
                "success": False,
                "actions": [],
                "confidence": 0.0,
                "error": str(e),
            }

    def _is_processed(self, event_id: str) -> bool:
        """Check if an event has already been processed"""
        # Use state manager to check
        try:
            state = self.state_manager.get_state()
            processed_ids = state.get("processed_teams_events", set())
            return event_id in processed_ids
        except Exception:
            return False

    def _mark_processed(self, event_id: str, _result: dict[str, Any]) -> None:
        """Mark an event as processed"""
        try:
            state = self.state_manager.get_state()
            processed_ids = state.get("processed_teams_events", set())
            processed_ids.add(event_id)
            self.state_manager.update_state({"processed_teams_events": processed_ids})
        except Exception as e:
            logger.warning(f"Failed to mark event as processed: {e}")

    async def process_single_message(
        self,
        chat_id: str,
        message_id: str,
    ) -> TeamsProcessingResult:
        """
        Process a specific message by ID

        Args:
            chat_id: Chat identifier
            message_id: Message identifier

        Returns:
            TeamsProcessingResult
        """
        logger.info(f"Processing single message {message_id} from chat {chat_id}")

        message = await self.teams_client.get_message(chat_id, message_id)
        return await self._process_message(message)

    def reset_poll_state(self) -> None:
        """Reset poll state to fetch all messages again"""
        self._last_poll = None
        logger.info("Poll state reset - will fetch all messages on next poll")
