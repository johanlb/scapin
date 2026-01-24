"""
AutoFetch Manager (SC-20)

Manages automatic background fetching of emails to keep the review queue populated.

Key features:
- Startup fetch: if queue < startup_threshold (default 20)
- Runtime fetch: if queue < low_threshold (default 5) after approve/reject
- Per-source cooldowns to avoid hammering external services
- WebSocket events for UI feedback
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from src.core.config_manager import get_config
from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.frontin.api.services.queue_service import QueueService
    from src.integrations.email.models import EmailContent, EmailMetadata

logger = get_logger("autofetch_manager")


class FetchSource(str, Enum):
    """Sources that can be auto-fetched."""

    EMAIL = "email"
    TEAMS = "teams"
    CALENDAR = "calendar"


class AutoFetchManager:
    """
    Singleton manager for automatic background fetching.

    Usage:
        manager = AutoFetchManager.get_instance()
        await manager.check_and_fetch_if_needed(is_startup=True)
    """

    _instance: AutoFetchManager | None = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        """Initialize the manager. Use get_instance() instead."""
        self._last_fetch: dict[FetchSource, datetime] = {}
        self._fetch_in_progress: dict[FetchSource, bool] = dict.fromkeys(FetchSource, False)
        self._debounce_task: asyncio.Task | None = None
        self._debounce_delay = 2.0  # seconds

    @classmethod
    async def get_instance(cls) -> AutoFetchManager:
        """Get or create singleton instance (thread-safe)."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    logger.info("AutoFetchManager initialized")
        return cls._instance

    def _get_cooldown(self, source: FetchSource) -> timedelta:
        """Get cooldown duration for a source."""
        config = get_config().autofetch
        cooldowns = {
            FetchSource.EMAIL: timedelta(minutes=config.email_cooldown_minutes),
            FetchSource.TEAMS: timedelta(minutes=config.teams_cooldown_minutes),
            FetchSource.CALENDAR: timedelta(minutes=config.calendar_cooldown_minutes),
        }
        return cooldowns.get(source, timedelta(minutes=2))

    def is_source_eligible(self, source: FetchSource) -> bool:
        """
        Check if a source is eligible for fetching.

        Returns True if:
        - Not currently fetching
        - Cooldown period has passed since last fetch
        """
        if self._fetch_in_progress.get(source, False):
            logger.debug(f"Source {source.value} already fetching")
            return False

        last_fetch = self._last_fetch.get(source)
        if last_fetch is None:
            return True

        cooldown = self._get_cooldown(source)
        elapsed = datetime.now() - last_fetch
        eligible = elapsed >= cooldown

        if not eligible:
            remaining = (cooldown - elapsed).total_seconds()
            logger.debug(
                f"Source {source.value} in cooldown, {remaining:.0f}s remaining"
            )

        return eligible

    async def check_and_fetch_if_needed(
        self,
        is_startup: bool = False,
        queue_service: QueueService | None = None,
    ) -> dict:
        """
        Check queue status and fetch if needed.

        Args:
            is_startup: True if called at server startup (uses startup_threshold)
            queue_service: Optional queue service (will be fetched if not provided)

        Returns:
            Dict with fetch results
        """
        config = get_config()

        if not config.autofetch.enabled:
            logger.debug("AutoFetch disabled")
            return {"status": "disabled", "fetched": 0}

        # Get queue service
        if queue_service is None:
            from src.frontin.api.services.queue_service import get_queue_service

            queue_service = get_queue_service()

        # Get current queue stats
        stats = await asyncio.to_thread(queue_service._storage.get_stats)
        pending_count = stats.get("by_state", {}).get("awaiting_review", 0)
        analyzing_count = stats.get("by_state", {}).get("analyzing", 0)
        active_count = pending_count + analyzing_count

        # Determine threshold
        threshold = (
            config.autofetch.startup_threshold
            if is_startup
            else config.autofetch.low_threshold
        )

        logger.info(
            f"AutoFetch check: {active_count} active items, threshold={threshold}, "
            f"is_startup={is_startup}"
        )

        if active_count >= threshold:
            return {
                "status": "sufficient",
                "active_count": active_count,
                "threshold": threshold,
                "fetched": 0,
            }

        # Fetch from eligible sources
        total_fetched = 0
        results = {}

        # Email fetch
        if self.is_source_eligible(FetchSource.EMAIL):
            count = await self._fetch_emails(queue_service, config.autofetch.fetch_limit)
            results["email"] = count
            total_fetched += count

        # TODO: Add Teams and Calendar fetching when integrated
        # if self.is_source_eligible(FetchSource.TEAMS):
        #     count = await self._fetch_teams(queue_service, config.autofetch.fetch_limit)
        #     results["teams"] = count
        #     total_fetched += count

        return {
            "status": "fetched" if total_fetched > 0 else "no_new_items",
            "active_count": active_count,
            "threshold": threshold,
            "fetched": total_fetched,
            "by_source": results,
        }

    async def _fetch_emails(
        self,
        queue_service: QueueService,
        limit: int,
    ) -> int:
        """
        Fetch emails and add to queue.

        Returns:
            Number of items added to queue
        """
        from src.frontin.api.websocket.queue_events import QueueEventEmitter

        self._fetch_in_progress[FetchSource.EMAIL] = True
        event_emitter = QueueEventEmitter()

        try:
            # Emit fetch started event
            await event_emitter.emit_fetch_started(FetchSource.EMAIL.value)

            config = get_config()

            from src.integrations.email.imap_client import IMAPClient

            imap_client = IMAPClient(config.email)
            items_created = 0

            with imap_client.connect():
                emails = imap_client.fetch_emails(
                    folder=config.email.get_default_account().inbox_folder,
                    limit=limit,
                    unprocessed_only=True,
                )

                items_to_analyze: list[tuple[str, EmailMetadata, EmailContent]] = []

                for metadata, content in emails:
                    item_id = await queue_service.create_analyzing_item(
                        metadata=metadata,
                        content_preview=content.preview or "",
                        account_id="default",
                        html_body=content.html,
                        full_text=content.plain_text,
                    )

                    if item_id:
                        items_to_analyze.append((item_id, metadata, content))
                        items_created += 1

            # Start background analysis if items were created
            if items_to_analyze:
                asyncio.create_task(
                    self._analyze_items_background(items_to_analyze, queue_service)
                )

            self._last_fetch[FetchSource.EMAIL] = datetime.now()

            # Emit fetch completed event
            await event_emitter.emit_fetch_completed(
                FetchSource.EMAIL.value, items_created
            )

            logger.info(
                f"AutoFetch email: {items_created} items created",
                extra={"source": "email", "count": items_created},
            )

            return items_created

        except Exception as e:
            logger.error(f"AutoFetch email failed: {e}", exc_info=True)
            return 0

        finally:
            self._fetch_in_progress[FetchSource.EMAIL] = False

    async def _analyze_items_background(
        self,
        items: list[tuple[str, EmailMetadata, EmailContent]],
        queue_service: QueueService,
    ) -> None:
        """Run analysis on items in background."""
        from src.core.schemas import EmailAction, EmailAnalysis, EmailCategory
        from src.trivelin.v2_processor import V2EmailProcessor

        config = get_config()
        v2_processor = V2EmailProcessor(config)

        for item_id, metadata, content in items:
            try:
                # Create event for V2 processor
                event = v2_processor._email_to_event(metadata, content)

                # Run analysis
                result = await v2_processor.process_event(event)

                if result.success and result.analysis:
                    # Convert to EmailAnalysis
                    analysis = EmailAnalysis(
                        action=result.analysis.action,
                        category=EmailCategory.WORK,  # TODO: extract from result
                        confidence=int(result.analysis.effective_confidence * 100),
                        reasoning=result.analysis.raisonnement or "",
                    )

                    # Build multi-pass data
                    multi_pass_data = None
                    if result.multi_pass_result:
                        multi_pass_data = self._build_multi_pass_data(
                            result.multi_pass_result
                        )

                    # Update queue item with analysis
                    await queue_service.complete_analysis(
                        item_id=item_id,
                        analysis=analysis,
                        multi_pass_data=multi_pass_data,
                    )

                    logger.debug(
                        f"Analysis complete for {item_id}: {analysis.action.value} "
                        f"({analysis.confidence}%)"
                    )
                else:
                    # Analysis failed - create fallback
                    fallback = EmailAnalysis(
                        action=EmailAction.QUEUE,
                        category=EmailCategory.OTHER,
                        confidence=0,
                        reasoning=f"AutoFetch analysis failed: {result.error or 'unknown'}",
                    )
                    await queue_service.complete_analysis(
                        item_id=item_id,
                        analysis=fallback,
                    )

            except Exception as e:
                logger.error(f"Background analysis failed for {item_id}: {e}")
                # Don't fail silently - mark item as failed
                try:
                    fallback = EmailAnalysis(
                        action=EmailAction.QUEUE,
                        category=EmailCategory.OTHER,
                        confidence=0,
                        reasoning=f"Analysis error: {e}",
                    )
                    await queue_service.complete_analysis(
                        item_id=item_id,
                        analysis=fallback,
                    )
                except Exception:
                    pass

    def _build_multi_pass_data(self, multi_pass_result) -> dict | None:
        """Build multi-pass metadata for storage."""
        if not multi_pass_result or not hasattr(multi_pass_result, "pass_history"):
            return None

        if not multi_pass_result.pass_history:
            return None

        pass_history = []
        models_used = []

        for i, pass_result in enumerate(multi_pass_result.pass_history):
            model = getattr(pass_result, "model_used", "unknown")
            models_used.append(model)

            pass_type = getattr(pass_result, "pass_type", None)
            pass_type_value = (
                pass_type.value if hasattr(pass_type, "value") else str(pass_type)
            )

            confidence_after = getattr(pass_result, "confidence", None)
            if confidence_after and hasattr(confidence_after, "overall"):
                confidence_after = confidence_after.overall
            elif not isinstance(confidence_after, (int, float)):
                confidence_after = 0.0

            pass_history.append(
                {
                    "pass_number": i + 1,
                    "model": model,
                    "pass_type": pass_type_value,
                    "duration_ms": getattr(pass_result, "duration_ms", 0),
                    "tokens": getattr(pass_result, "tokens_used", 0),
                    "confidence_after": confidence_after,
                }
            )

        return {
            "passes_count": len(pass_history),
            "final_model": models_used[-1] if models_used else "unknown",
            "models_used": models_used,
            "escalated": len(set(models_used)) > 1,
            "stop_reason": getattr(multi_pass_result, "stop_reason", "unknown"),
            "pass_history": pass_history,
        }

    async def on_item_processed(self, queue_service: QueueService | None = None) -> None:
        """
        Called after an item is approved/rejected.

        Uses debouncing to avoid multiple fetches in quick succession.
        """
        config = get_config()

        if not config.autofetch.enabled:
            return

        # Cancel existing debounce task if any
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        # Schedule new debounced check
        self._debounce_task = asyncio.create_task(
            self._debounced_check(queue_service)
        )

    async def _debounced_check(self, queue_service: QueueService | None) -> None:
        """Wait for debounce delay then check if fetch needed."""
        try:
            await asyncio.sleep(self._debounce_delay)
            await self.check_and_fetch_if_needed(
                is_startup=False, queue_service=queue_service
            )
        except asyncio.CancelledError:
            pass  # Debounce cancelled, newer check scheduled


# Convenience function
async def get_autofetch_manager() -> AutoFetchManager:
    """Get the AutoFetchManager singleton."""
    return await AutoFetchManager.get_instance()
