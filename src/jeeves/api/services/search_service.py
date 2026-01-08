"""
Search Service

Global search across all content types: notes, emails, calendar, teams.
"""

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.core.config_manager import ScapinConfig
from src.integrations.storage.queue_storage import QueueStorage
from src.jeeves.api.models.search import (
    CalendarSearchResultItem,
    CrossSourceResultItem,
    CrossSourceSearchRequest,
    CrossSourceSearchResponse,
    EmailSearchResultItem,
    GlobalSearchResponse,
    NoteSearchResultItem,
    RecentSearchesResponse,
    RecentSearchItem,
    SearchResultCounts,
    SearchResultsByType,
    SearchResultType,
    TeamsSearchResultItem,
)
from src.monitoring.logger import get_logger
from src.passepartout.note_manager import NoteManager

logger = get_logger("jeeves.api.services.search")


def _highlight_matches(text: str, query: str, context_chars: int = 50) -> str:
    """
    Create excerpt with highlighted matches

    Args:
        text: Full text to search in
        query: Search query
        context_chars: Characters to show around match

    Returns:
        Excerpt with match context
    """
    if not text or not query:
        return text[:200] if text else ""

    # Simple word matching
    words = query.lower().split()
    text_lower = text.lower()

    # Find first match position
    first_match = -1
    for word in words:
        pos = text_lower.find(word)
        if pos != -1 and (first_match == -1 or pos < first_match):
            first_match = pos

    if first_match == -1:
        # No match found, return beginning
        return text[:200] + "..." if len(text) > 200 else text

    # Extract context around match
    start = max(0, first_match - context_chars)
    end = min(len(text), first_match + context_chars + len(query))

    excerpt = text[start:end]
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt = excerpt + "..."

    return excerpt


def _text_match_score(text: str, query: str) -> float:
    """
    Calculate simple text match score

    Args:
        text: Text to search in
        query: Search query

    Returns:
        Score between 0 and 1
    """
    if not text or not query:
        return 0.0

    text_lower = text.lower()
    query_lower = query.lower()
    words = query_lower.split()

    if not words:
        return 0.0

    # Count matching words
    matches = sum(1 for word in words if word in text_lower)
    word_score = matches / len(words)

    # Bonus for exact phrase match
    phrase_bonus = 0.2 if query_lower in text_lower else 0.0

    # Bonus for match at beginning
    start_bonus = 0.1 if text_lower.startswith(query_lower) else 0.0

    return min(1.0, word_score + phrase_bonus + start_bonus)


@dataclass
class SearchService:
    """
    Global search service across all content types

    Searches:
    - Notes: Semantic search via vector store
    - Emails: Text search in queue storage
    - Calendar: Text search in cached events (when available)
    - Teams: Text search in cached messages (when available)
    """

    config: ScapinConfig
    _note_manager: NoteManager | None = field(default=None, init=False)
    _queue_storage: QueueStorage | None = field(default=None, init=False)
    _recent_searches: list[RecentSearchItem] = field(default_factory=list, init=False)
    _max_recent_searches: int = field(default=50, init=False)

    def _get_note_manager(self) -> NoteManager:
        """Get or create NoteManager instance"""
        if self._note_manager is None:
            notes_dir = getattr(self.config, "notes_dir", None)
            if notes_dir is None:
                notes_dir = Path.home() / "Documents" / "Notes"
            else:
                notes_dir = Path(notes_dir)
            self._note_manager = NoteManager(notes_dir, auto_index=True)
        return self._note_manager

    def _get_queue_storage(self) -> QueueStorage:
        """Get or create QueueStorage instance"""
        if self._queue_storage is None:
            self._queue_storage = QueueStorage()
        return self._queue_storage

    def _add_recent_search(self, query: str, result_count: int) -> None:
        """Track recent search query"""
        item = RecentSearchItem(
            query=query,
            timestamp=datetime.now(timezone.utc),
            result_count=result_count,
        )
        self._recent_searches.insert(0, item)
        # Limit size
        if len(self._recent_searches) > self._max_recent_searches:
            self._recent_searches = self._recent_searches[: self._max_recent_searches]

    async def search(
        self,
        query: str,
        types: list[SearchResultType] | None = None,
        limit_per_type: int = 10,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> GlobalSearchResponse:
        """
        Global search across all content types

        Args:
            query: Search query
            types: Filter by content types (None = all types)
            limit_per_type: Maximum results per type
            date_from: Filter results after this date
            date_to: Filter results before this date

        Returns:
            GlobalSearchResponse with results from all types
        """
        start_time = time.time()
        logger.info(f"Global search: '{query}' (types={types}, limit={limit_per_type})")

        # Default to all types
        if types is None:
            types = list(SearchResultType)

        results = SearchResultsByType()
        counts = SearchResultCounts()

        # Search each type
        if SearchResultType.NOTE in types:
            notes_results = await self._search_notes(query, limit_per_type, date_from, date_to)
            results.notes = notes_results
            counts.notes = len(notes_results)

        if SearchResultType.EMAIL in types:
            email_results = await self._search_emails(query, limit_per_type, date_from, date_to)
            results.emails = email_results
            counts.emails = len(email_results)

        if SearchResultType.CALENDAR in types:
            calendar_results = await self._search_calendar(
                query, limit_per_type, date_from, date_to
            )
            results.calendar = calendar_results
            counts.calendar = len(calendar_results)

        if SearchResultType.TEAMS in types:
            teams_results = await self._search_teams(query, limit_per_type, date_from, date_to)
            results.teams = teams_results
            counts.teams = len(teams_results)

        total = counts.notes + counts.emails + counts.calendar + counts.teams
        search_time_ms = (time.time() - start_time) * 1000

        # Track recent search
        self._add_recent_search(query, total)

        logger.info(
            f"Search completed: {total} results in {search_time_ms:.1f}ms",
            extra={"query": query, "total": total, "counts": counts.model_dump()},
        )

        return GlobalSearchResponse(
            query=query,
            results=results,
            total=total,
            counts=counts,
            search_time_ms=search_time_ms,
        )

    async def _search_notes(
        self,
        query: str,
        limit: int,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[NoteSearchResultItem]:
        """Search notes using semantic search"""
        try:
            manager = self._get_note_manager()
            results = manager.search_notes(query=query, top_k=limit, return_scores=True)

            items = []
            for note, score in results:  # type: ignore
                # Apply date filters
                if date_from and note.updated_at < date_from:
                    continue
                if date_to and note.updated_at > date_to:
                    continue

                # Generate excerpt with highlights
                excerpt = _highlight_matches(note.content, query)
                # Clean markdown for excerpt
                excerpt = re.sub(r"^#+\s+", "", excerpt)
                excerpt = re.sub(r"\*\*|\*|__|_", "", excerpt)

                # Normalize score to 0-1 range
                normalized_score = min(1.0, max(0.0, float(score)))

                items.append(
                    NoteSearchResultItem(
                        id=note.note_id,
                        title=note.title,
                        excerpt=excerpt,
                        score=normalized_score,
                        timestamp=note.updated_at,
                        path=note.metadata.get("path", ""),
                        tags=note.tags,
                        metadata={
                            "created_at": note.created_at.isoformat(),
                            "pinned": note.metadata.get("pinned", False),
                        },
                    )
                )

            return items

        except Exception as e:
            logger.error(f"Note search failed: {e}")
            return []

    async def _search_emails(
        self,
        query: str,
        limit: int,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[EmailSearchResultItem]:
        """Search emails in queue storage"""
        try:
            storage = self._get_queue_storage()
            # Load all queue items (we'll filter and score)
            all_items = storage.load_queue(status=None)  # All statuses

            scored_items = []
            for item in all_items:
                metadata = item.get("metadata", {})
                content = item.get("content", {})

                # Combine searchable text
                subject = metadata.get("subject", "")
                from_name = metadata.get("from_name", "")
                from_address = metadata.get("from_address", "")
                preview = content.get("preview", "")
                searchable = f"{subject} {from_name} {from_address} {preview}"

                # Calculate score
                score = _text_match_score(searchable, query)
                if score == 0:
                    continue

                # Parse date
                date_str = metadata.get("date")
                if date_str:
                    try:
                        item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        item_date = datetime.now(timezone.utc)
                else:
                    item_date = datetime.now(timezone.utc)

                # Apply date filters
                if date_from and item_date < date_from:
                    continue
                if date_to and item_date > date_to:
                    continue

                scored_items.append((item, score, item_date))

            # Sort by score descending
            scored_items.sort(key=lambda x: x[1], reverse=True)
            scored_items = scored_items[:limit]

            # Build response
            items = []
            for item, score, item_date in scored_items:
                metadata = item.get("metadata", {})
                content = item.get("content", {})

                items.append(
                    EmailSearchResultItem(
                        id=item.get("id", ""),
                        title=metadata.get("subject", "(No subject)"),
                        excerpt=_highlight_matches(content.get("preview", ""), query),
                        score=score,
                        timestamp=item_date,
                        from_address=metadata.get("from_address", ""),
                        from_name=metadata.get("from_name", ""),
                        status=item.get("status", "pending"),
                        metadata={
                            "account_id": item.get("account_id"),
                            "has_attachments": metadata.get("has_attachments", False),
                            "queued_at": item.get("queued_at"),
                        },
                    )
                )

            return items

        except Exception as e:
            logger.error(f"Email search failed: {e}")
            return []

    async def _search_calendar(
        self,
        _query: str,
        _limit: int,
        _date_from: datetime | None,
        _date_to: datetime | None,
    ) -> list[CalendarSearchResultItem]:
        """
        Search calendar events

        Note: Currently returns empty list as calendar events
        are not persisted locally. Future implementation will
        query the Microsoft Graph API or use cached events.
        """
        # TODO: Implement calendar search when event caching is added
        # This would require:
        # 1. Caching calendar events locally
        # 2. Or querying Graph API directly (with rate limiting)
        logger.debug("Calendar search not yet implemented")
        return []

    async def _search_teams(
        self,
        _query: str,
        _limit: int,
        _date_from: datetime | None,
        _date_to: datetime | None,
    ) -> list[TeamsSearchResultItem]:
        """
        Search Teams messages

        Note: Currently returns empty list as Teams messages
        are not persisted locally. Future implementation will
        query the Microsoft Graph API or use cached messages.
        """
        # TODO: Implement Teams search when message caching is added
        # This would require:
        # 1. Caching Teams messages locally
        # 2. Or querying Graph API directly (with rate limiting)
        logger.debug("Teams search not yet implemented")
        return []

    async def get_recent_searches(self, limit: int = 20) -> RecentSearchesResponse:
        """
        Get recent search queries

        Args:
            limit: Maximum number of recent searches to return

        Returns:
            RecentSearchesResponse with recent queries
        """
        searches = self._recent_searches[:limit]
        return RecentSearchesResponse(
            searches=searches,
            total=len(self._recent_searches),
        )

    async def cross_source_search(
        self,
        request: CrossSourceSearchRequest,
    ) -> CrossSourceSearchResponse:
        """
        Search across all available sources using CrossSourceEngine

        Uses the unified CrossSourceEngine to search calendar, Teams,
        emails, and other sources with intelligent ranking.

        Args:
            request: Cross-source search request with query and options

        Returns:
            CrossSourceSearchResponse with results from all sources
        """
        start_time = time.time()
        logger.info(
            f"Cross-source search: '{request.query}'",
            extra={
                "sources": [s.value for s in request.sources] if request.sources else "all",
                "max_results": request.max_results,
            }
        )

        try:
            # Import and create CrossSourceEngine
            from src.passepartout.cross_source import create_cross_source_engine

            engine = create_cross_source_engine(self.config)

            # Filter sources if specified
            sources_filter = None
            if request.sources:
                sources_filter = [s.value for s in request.sources]

            # Execute search
            result = await engine.search(
                query=request.query,
                sources=sources_filter,
                max_results=request.max_results,
            )

            # Convert SourceItem to CrossSourceResultItem
            items = []
            for source_item in result.items:
                # Filter by min_relevance
                score = source_item.final_score or source_item.relevance_score
                if score < request.min_relevance:
                    continue

                content = source_item.content if request.include_content else ""
                if len(content) > 500:
                    content = content[:500] + "..."

                items.append(
                    CrossSourceResultItem(
                        source=source_item.source,
                        type=source_item.type,
                        title=source_item.title,
                        content=content,
                        timestamp=source_item.timestamp,
                        relevance_score=source_item.relevance_score,
                        final_score=source_item.final_score or source_item.relevance_score,
                        url=source_item.url,
                        metadata=source_item.metadata,
                    )
                )

            search_time_ms = (time.time() - start_time) * 1000

            # Track recent search
            self._add_recent_search(request.query, len(items))

            logger.info(
                f"Cross-source search completed: {len(items)} results in {search_time_ms:.1f}ms",
                extra={
                    "query": request.query,
                    "total": len(items),
                    "sources_searched": result.sources_searched,
                },
            )

            return CrossSourceSearchResponse(
                query=request.query,
                items=items,
                total_results=len(items),
                sources_searched=result.sources_searched,
                sources_available=engine.available_sources,
                search_time_ms=search_time_ms,
                cached=result.from_cache,
            )

        except Exception as e:
            logger.error(f"Cross-source search failed: {e}", exc_info=True)
            search_time_ms = (time.time() - start_time) * 1000
            return CrossSourceSearchResponse(
                query=request.query,
                items=[],
                total_results=0,
                sources_searched=[],
                sources_available=[],
                search_time_ms=search_time_ms,
                cached=False,
            )
