"""
Note Reviewer

Analyzes notes and determines what actions are needed during review.
Integrates with Sancho for AI-powered analysis and Passepartout for context.
Uses CrossSourceEngine to enrich reviews with external context.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from src.monitoring.logger import get_logger
from src.passepartout.note_manager import Note, NoteManager
from src.passepartout.note_metadata import (
    EnrichmentRecord,
    NoteMetadata,
    NoteMetadataStore,
)
from src.passepartout.note_scheduler import NoteScheduler
from src.passepartout.note_types import (
    DEFAULT_CONSERVATION_CRITERIA,
    ConservationCriteria,
)

if TYPE_CHECKING:
    from src.passepartout.cross_source import CrossSourceEngine

logger = get_logger("passepartout.note_reviewer")

# Maximum regex matches to process per pattern to prevent DoS on large documents
MAX_REGEX_MATCHES = 100


class ActionType(str, Enum):
    """Types of review actions"""

    ADD = "add"  # Add new content
    UPDATE = "update"  # Update existing content
    REMOVE = "remove"  # Remove obsolete content
    LINK = "link"  # Add wikilink to another note
    ARCHIVE = "archive"  # Move content to archive section
    FORMAT = "format"  # Formatting fixes only
    ENRICH = "enrich"  # Enrich an external note (Reflection)

    # Hygiene actions (Phase 1+)
    VALIDATE = "validate"  # Fix frontmatter validation issues
    FIX_LINKS = "fix_links"  # Fix broken wikilinks
    MERGE = "merge"  # Merge with another note (destructive)
    SPLIT = "split"  # Split into multiple notes (destructive)
    REFACTOR = "refactor"  # Reorganize content between linked notes


@dataclass
class ReviewAction:
    """A single action suggested during review"""

    action_type: ActionType
    target: str  # Section or content being targeted
    content: Optional[str] = None  # New content if applicable
    confidence: float = 0.5  # 0.0 - 1.0
    reasoning: str = ""
    source: str = ""  # Where this suggestion came from
    target_note_id: Optional[str] = None  # ID of the note to update (None for current note)

    def to_enrichment_record(self, applied: bool) -> EnrichmentRecord:
        """Convert to EnrichmentRecord for history"""
        return EnrichmentRecord(
            timestamp=datetime.now(timezone.utc),
            action_type=self.action_type.value,
            target=self.target,
            content=self.content,
            confidence=self.confidence,
            applied=applied,
            reasoning=self.reasoning,
        )


@dataclass
class ReviewContext:
    """Context collected for reviewing a note"""

    note: Note
    metadata: NoteMetadata
    linked_notes: list[Note] = field(default_factory=list)
    linked_note_excerpts: dict[str, str] = field(default_factory=dict)
    recent_changes: list[dict[str, Any]] = field(default_factory=list)
    related_entities: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class HygieneMetrics:
    """Structural health metrics for a note"""

    word_count: int
    is_too_short: bool  # < 100 words
    is_too_long: bool  # > 2000 words
    frontmatter_valid: bool
    frontmatter_issues: list[str] = field(default_factory=list)
    broken_links: list[str] = field(default_factory=list)
    heading_issues: list[str] = field(default_factory=list)
    duplicate_candidates: list[tuple[str, float]] = field(
        default_factory=list
    )  # (note_id, similarity_score)
    formatting_score: float = 1.0  # 0-1, 1 = perfect


@dataclass
class ReviewAnalysis:
    """Result of analyzing a note for review"""

    needs_update: bool
    confidence: float
    suggested_actions: list[ReviewAction]
    reasoning: str
    detected_issues: list[str] = field(default_factory=list)
    detected_strengths: list[str] = field(default_factory=list)
    hygiene: Optional[HygieneMetrics] = None  # NEW: hygiene metrics


@dataclass
class ReviewResult:
    """Complete result of a note review"""

    note_id: str
    quality: int  # 0-5 for SM-2
    applied_actions: list[ReviewAction]
    pending_actions: list[ReviewAction]  # Actions needing approval
    analysis: ReviewAnalysis
    updated_content: Optional[str] = None
    error: Optional[str] = None


class NoteReviewer:
    """
    Reviews notes and determines enrichment actions

    The reviewer:
    1. Loads context (note, linked notes, history)
    2. Analyzes content for issues and improvements
    3. Suggests actions with confidence scores
    4. Auto-applies high-confidence actions
    5. Queues low-confidence actions for approval
    """

    # Confidence thresholds for auto-applying actions
    AUTO_APPLY_THRESHOLD = 0.85  # Semantic actions (enrichments, refactoring)
    HYGIENE_THRESHOLD = 0.70  # Mechanical actions (validation, formatting, link fixes)

    # Destructive actions always require approval
    DESTRUCTIVE_ACTIONS = {ActionType.MERGE, ActionType.SPLIT}

    def __init__(
        self,
        note_manager: NoteManager,
        metadata_store: NoteMetadataStore,
        scheduler: NoteScheduler,
        conservation_criteria: Optional[ConservationCriteria] = None,
        ai_router: Optional[Any] = None,
        cross_source_engine: Optional["CrossSourceEngine"] = None,
        note_janitor: Optional[Any] = None,
    ):
        """
        Initialize reviewer

        Args:
            note_manager: Note manager for accessing notes
            metadata_store: Store for metadata
            scheduler: Scheduler for updating review times
            conservation_criteria: Rules for what to keep/remove
            ai_router: Optional AI router for analysis (Sancho)
            cross_source_engine: Optional CrossSourceEngine for external context
            note_janitor: Optional NoteJanitor for technical validation
        """
        self.notes = note_manager
        self.store = metadata_store
        self.scheduler = scheduler
        self.criteria = conservation_criteria or DEFAULT_CONSERVATION_CRITERIA
        self.ai_router = ai_router
        self.cross_source_engine = cross_source_engine

        # Initialize NoteJanitor for hygiene validation
        if note_janitor is None:
            try:
                from src.passepartout.janitor import NoteJanitor

                self.janitor = NoteJanitor(note_manager.notes_dir)
            except Exception as e:
                logger.warning(f"Failed to initialize NoteJanitor: {e}")
                self.janitor = None
        else:
            self.janitor = note_janitor

    async def review_note(self, note_id: str) -> ReviewResult:
        """
        Perform a complete review of a note

        Args:
            note_id: Note to review

        Returns:
            ReviewResult with actions taken and pending
        """
        logger.info(f"Starting review for note {note_id}")

        # Load note and metadata
        note = self.notes.get_note(note_id)
        if note is None:
            return ReviewResult(
                note_id=note_id,
                quality=0,
                applied_actions=[],
                pending_actions=[],
                analysis=ReviewAnalysis(
                    needs_update=False,
                    confidence=0.0,
                    suggested_actions=[],
                    reasoning="Note not found",
                ),
                error="Note not found",
            )

        metadata = self.store.get(note_id)
        if metadata is None:
            # Create metadata if missing
            from src.passepartout.note_types import detect_note_type_from_path

            note_type = detect_note_type_from_path(str(note.file_path) if note.file_path else "")
            metadata = self.store.create_for_note(
                note_id=note_id,
                note_type=note_type,
                content=note.content,
            )

        # Build review context
        context = await self._load_context(note, metadata)

        # Calculate hygiene metrics
        hygiene_metrics = self._calculate_hygiene_metrics(note)

        # Scrub content for AI analysis (prevent binary bloat/token waste)
        scrubbed_content = self._scrub_content(note.content)

        # Analyze note (use scrubbed content and hygiene metrics)
        analysis = await self._analyze(
            context, scrubbed_content=scrubbed_content, hygiene=hygiene_metrics
        )

        # Process actions
        applied_actions = []
        pending_actions = []
        updated_content = note.content

        for action in analysis.suggested_actions:
            # Determine if action should be auto-applied
            should_auto_apply = self._should_auto_apply(action)

            if should_auto_apply:
                # Auto-apply high confidence actions
                if action.action_type == ActionType.ENRICH and action.target_note_id:
                    # External update (Briefing or other note)
                    logger.info(f"Applying external enrichment to {action.target_note_id}")
                    if self._apply_external_action(action):
                        applied_actions.append(action)
                        metadata.enrichment_history.append(
                            action.to_enrichment_record(applied=True)
                        )
                else:
                    new_content = self._apply_action(updated_content, action)
                    if new_content != updated_content:
                        updated_content = new_content
                        applied_actions.append(action)
                        # Record in history
                        metadata.enrichment_history.append(
                            action.to_enrichment_record(applied=True)
                        )
            else:
                # Queue for approval
                pending_actions.append(action)
                metadata.enrichment_history.append(action.to_enrichment_record(applied=False))

        # Calculate quality for SM-2
        quality = self._calculate_quality(analysis, len(applied_actions))

        # Save updated note if changes were made
        if updated_content != note.content:
            self.notes.update_note(
                note_id=note_id,
                content=updated_content,
            )

        # Update metadata and schedule
        self.scheduler.record_review(note_id, quality, metadata=metadata)

        logger.info(
            f"Completed review for {note_id}: "
            f"Q={quality}, applied={len(applied_actions)}, pending={len(pending_actions)}"
        )

        return ReviewResult(
            note_id=note_id,
            quality=quality,
            applied_actions=applied_actions,
            pending_actions=pending_actions,
            analysis=analysis,
            updated_content=updated_content if applied_actions else None,
        )

    async def _load_context(
        self,
        note: Note,
        metadata: NoteMetadata,
    ) -> ReviewContext:
        """Load full context for review"""

        # Find linked notes via wikilinks
        wikilinks = self._extract_wikilinks(note.content)
        linked_notes = []
        linked_excerpts = {}

        for link in wikilinks[:10]:  # Limit to 10 linked notes
            linked_note = self.notes.search_notes(query=link, top_k=1)
            if linked_note:
                if isinstance(linked_note[0], tuple):
                    linked_note_obj = linked_note[0][0]
                else:
                    linked_note_obj = linked_note[0]
                linked_notes.append(linked_note_obj)
                # Extract relevant excerpt
                linked_excerpts[link] = linked_note_obj.content[:500]

        # Get recent changes from git
        recent_changes = []
        if hasattr(self.notes, "git_manager") and self.notes.git_manager:
            try:
                versions = self.notes.git_manager.get_note_versions(note.note_id, limit=5)
                recent_changes = [
                    {
                        "commit_hash": v.commit_hash,
                        "timestamp": v.timestamp,
                        "message": v.commit_message,
                    }
                    for v in versions
                ]
            except Exception as e:
                logger.debug(f"Could not load git history: {e}")

        # Query CrossSourceEngine for related items from external sources
        related_entities = await self._query_cross_source(note)

        return ReviewContext(
            note=note,
            metadata=metadata,
            linked_notes=linked_notes,
            linked_note_excerpts=linked_excerpts,
            recent_changes=recent_changes,
            related_entities=related_entities,
        )

    async def _query_cross_source(self, note: Note) -> list[dict[str, Any]]:
        """
        Query CrossSourceEngine for related items from external sources.

        Builds a search query from the note's title and key terms,
        then retrieves relevant items from emails, calendar, teams, etc.

        Args:
            note: The note being reviewed

        Returns:
            List of related items as dictionaries
        """
        if self.cross_source_engine is None:
            return []

        try:
            # Build search query from note title and first 200 chars of content
            query_parts = [note.title]

            # Add key tags if available
            if note.tags:
                query_parts.extend(note.tags[:3])  # Limit to 3 tags

            # Extract key terms from content (first line after title often has context)
            content_lines = note.content.strip().split("\n")
            if len(content_lines) > 1:
                # Skip title (usually first line), get next non-empty line
                for line in content_lines[1:4]:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith("#"):
                        # Add first 100 chars of context
                        query_parts.append(clean_line[:100])
                        break

            query = " ".join(query_parts)
            logger.debug(f"CrossSource query for note {note.note_id}: {query[:100]}...")

            # Search cross-source with reasonable limits
            result = await self.cross_source_engine.search(
                query=query,
                max_results=5,  # Limit to top 5 most relevant
            )

            # Convert SourceItems to dictionaries for storage
            related_items = []
            for item in result.items:
                related_items.append(
                    {
                        "source": item.source,
                        "type": item.type,
                        "title": item.title,
                        "content": item.content[:300] if item.content else "",  # Limit content
                        "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                        "relevance_score": item.relevance_score,
                        "url": item.url,
                        "metadata": item.metadata,
                    }
                )

            logger.info(
                f"CrossSource found {len(related_items)} related items for note {note.note_id}",
                extra={"sources": result.sources_searched},
            )

            return related_items

        except Exception as e:
            logger.warning(f"CrossSource query failed for note {note.note_id}: {e}")
            return []

    def _calculate_hygiene_metrics(self, note: Note) -> HygieneMetrics:
        """
        Calculate structural health metrics for a note

        Args:
            note: The note to analyze

        Returns:
            HygieneMetrics with structural health information
        """
        # Count words
        words = note.content.split()
        word_count = len(words)

        # Length analysis
        is_too_short = word_count < 100
        is_too_long = word_count > 2000

        # Frontmatter validation
        frontmatter_issues = []
        frontmatter_valid = True

        required_fields = ["title", "created_at", "updated_at"]
        for field in required_fields:
            if field not in note.metadata or not note.metadata.get(field):
                frontmatter_issues.append(f"Missing: {field}")
                frontmatter_valid = False

        # Detect broken wikilinks with similarity suggestions
        broken_links = []
        wikilinks = self._extract_wikilinks(note.content)
        for link in wikilinks[:20]:  # Limit checks to avoid slowdown
            search_result = self.notes.search_notes(query=link, top_k=3)
            if not search_result:
                # No exact match - try to find similar notes
                similar = self.notes.search_notes(query=link, top_k=1)
                if similar:
                    # Found a similar note, suggest it
                    similar_note = similar[0][0] if isinstance(similar[0], tuple) else similar[0]
                    broken_links.append(f"{link} -> suggest: {similar_note.title}")
                else:
                    broken_links.append(link)
            elif isinstance(search_result[0], tuple):
                # Check if it's a good match (score > 0.7)
                score = search_result[0][1] if len(search_result[0]) > 1 else 1.0
                if score < 0.7:
                    broken_links.append(f"{link} (low confidence)")

        # Check heading hierarchy
        heading_issues = []
        lines = note.content.split("\n")
        prev_level = 0
        for line in lines:
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                if level > prev_level + 1:
                    heading_issues.append(f"Skip at: {line[:40]}")
                prev_level = level

        # Formatting score
        formatting_score = 1.0
        if heading_issues:
            formatting_score -= 0.2
        if broken_links:
            formatting_score -= 0.1 * min(len(broken_links), 5)
        formatting_score = max(0.0, formatting_score)

        # Detect duplicate candidates using vector similarity
        duplicate_candidates = []
        try:
            # Use vector store to find similar notes
            similar_notes = self.notes.search_notes(query=note.content[:500], top_k=5)
            for result in similar_notes:
                if isinstance(result, tuple):
                    similar_note, score = result[0], result[1] if len(result) > 1 else 0.0
                else:
                    similar_note, score = result, 0.0

                # Skip self and low similarity
                if similar_note.note_id == note.note_id:
                    continue
                if score > 0.8:  # High similarity threshold for duplicates
                    duplicate_candidates.append((similar_note.note_id, score))
        except Exception as e:
            logger.debug(f"Duplicate detection failed: {e}")

        return HygieneMetrics(
            word_count=word_count,
            is_too_short=is_too_short,
            is_too_long=is_too_long,
            frontmatter_valid=frontmatter_valid,
            frontmatter_issues=frontmatter_issues,
            broken_links=broken_links,
            heading_issues=heading_issues,
            duplicate_candidates=duplicate_candidates,
            formatting_score=formatting_score,
        )

    def _extract_wikilinks(self, content: str) -> list[str]:
        """Extract wikilinks from content"""
        pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        return re.findall(pattern, content)

    def _scrub_content(self, content: str) -> str:
        """
        Scrub media links and large binary-like patterns from content.

        Replaces ![image](path) or other media markers with placeholders.
        """
        # Replace Markdown images/attachments: ![alt](path)
        scrubbed = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"[MEDIA: \1]", content)

        # Replace HTML images: <img src="...">
        scrubbed = re.sub(r"<img[^>]+src=[\"'][^\"']+[\"'][^>]*>", "[IMAGE]", scrubbed)

        return scrubbed

    async def _analyze(
        self,
        context: ReviewContext,
        scrubbed_content: Optional[str] = None,
        hygiene: Optional[HygieneMetrics] = None,
    ) -> ReviewAnalysis:
        """Analyze note and suggest actions"""
        note = context.note
        content_for_analysis = scrubbed_content if scrubbed_content is not None else note.content
        metadata = context.metadata
        actions = []
        issues = []
        strengths = []

        # Rule-based analysis
        content = content_for_analysis

        # Check for outdated temporal references
        temporal_issues = self._check_temporal_references(content)
        for issue in temporal_issues:
            actions.append(
                ReviewAction(
                    action_type=ActionType.ARCHIVE,
                    target=issue["text"],
                    confidence=issue["confidence"],
                    reasoning=issue["reason"],
                    source="temporal_analysis",
                )
            )
            issues.append(issue["reason"])

        # Check for completed tasks that could be cleaned
        completed_tasks = self._check_completed_tasks(content)
        for task in completed_tasks:
            actions.append(
                ReviewAction(
                    action_type=ActionType.ARCHIVE,
                    target=task["text"],
                    confidence=task["confidence"],
                    reasoning=task["reason"],
                    source="task_analysis",
                )
            )

        # Check for missing links
        missing_links = self._check_missing_links(content, context.linked_notes)
        for link in missing_links:
            actions.append(
                ReviewAction(
                    action_type=ActionType.LINK,
                    target=link["entity"],
                    content=f"[[{link['entity']}]]",
                    confidence=link["confidence"],
                    reasoning=link["reason"],
                    source="link_analysis",
                )
            )

        # Check formatting issues
        format_issues = self._check_formatting(content)
        for issue in format_issues:
            actions.append(
                ReviewAction(
                    action_type=ActionType.FORMAT,
                    target=issue["location"],
                    content=issue["fix"],
                    confidence=0.95,  # Formatting is usually safe
                    reasoning=issue["reason"],
                    source="format_analysis",
                )
            )

        # Detect strengths
        if len(context.linked_notes) > 3:
            strengths.append("Bien connectée avec d'autres notes")
        if len(note.tags) > 0:
            strengths.append(f"Tags présents: {', '.join(note.tags)}")
        if len(content) > 500:
            strengths.append("Contenu substantiel")

        # AI analysis if available
        if self.ai_router and metadata.auto_enrich:
            try:
                ai_actions = await self._ai_analyze(context)
                actions.extend(ai_actions)
            except Exception as e:
                logger.warning(f"AI analysis failed: {e}")

        # Calculate overall confidence
        needs_update = len(actions) > 0
        overall_confidence = max(a.confidence for a in actions) if actions else 1.0

        # Generate reasoning summary
        if not actions:
            reasoning = "Note en bon état, aucune action suggérée"
        else:
            action_summary = ", ".join(
                f"{a.action_type.value}({a.target[:30]}...)" for a in actions[:3]
            )
            reasoning = f"{len(actions)} actions suggérées: {action_summary}"

        return ReviewAnalysis(
            needs_update=needs_update,
            confidence=overall_confidence,
            suggested_actions=actions,
            reasoning=reasoning,
            detected_issues=issues,
            detected_strengths=strengths,
        )

    def _check_temporal_references(self, content: str) -> list[dict]:
        """Check for outdated temporal references"""
        issues = []

        # Patterns for temporal references
        patterns = [
            (r"(cette semaine|this week)", 7),
            (r"(demain|tomorrow)", 2),
            (r"(aujourd'hui|today)", 1),
            (r"(la semaine prochaine|next week)", 14),
            (r"(le mois prochain|next month)", 45),
            (r"(réunion|meeting).*?(\d{1,2}[/\-]\d{1,2})", 30),
        ]

        for pattern, days_threshold in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for i, match in enumerate(matches):
                if i >= MAX_REGEX_MATCHES:
                    logger.warning(
                        f"Hit regex match limit ({MAX_REGEX_MATCHES}) for pattern {pattern}"
                    )
                    break
                # Check if this matches a keep pattern
                context = content[max(0, match.start() - 50) : match.end() + 50]
                should_keep = any(
                    re.search(keep_pattern, context, re.IGNORECASE)
                    for keep_pattern in self.criteria.keep_patterns
                )

                if not should_keep:
                    confidence = min(0.85, 0.5 + (days_threshold / 100))
                    issues.append(
                        {
                            "text": match.group(0),
                            "confidence": confidence,
                            "reason": f"Référence temporelle potentiellement obsolète: '{match.group(0)}'",
                        }
                    )

        return issues

    def _check_completed_tasks(self, content: str) -> list[dict]:
        """Check for completed minor tasks"""
        tasks = []

        # Pattern for completed tasks
        pattern = r"\[x\]\s*(.+?)(?:\n|$)"
        matches = re.finditer(pattern, content, re.IGNORECASE)

        for i, match in enumerate(matches):
            if i >= MAX_REGEX_MATCHES:
                logger.warning(f"Hit regex match limit ({MAX_REGEX_MATCHES}) for completed tasks")
                break
            task_text = match.group(1).strip()

            # Check if it's a minor task (short, no important keywords)
            important_keywords = [
                "projet",
                "client",
                "deadline",
                "important",
                "urgent",
                "milestone",
            ]
            is_minor = len(task_text) < 50 and not any(
                kw in task_text.lower() for kw in important_keywords
            )

            if is_minor:
                tasks.append(
                    {
                        "text": match.group(0),
                        "confidence": 0.75,
                        "reason": f"Tâche mineure terminée: '{task_text[:30]}...'",
                    }
                )

        return tasks

    def _check_missing_links(
        self,
        content: str,
        _linked_notes: list[Note],
    ) -> list[dict]:
        """Check for entities that could be linked"""
        suggestions = []

        # Get existing wikilinks
        existing_links = set(self._extract_wikilinks(content))

        # Look for capitalized words that might be entities
        # but aren't already linked
        pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
        potential_entities = set(re.findall(pattern, content))

        for entity in potential_entities:
            if entity in existing_links:
                continue
            if len(entity) < 3:
                continue

            # Check if this entity exists as a note
            search_results = self.notes.search_notes(query=entity, top_k=1)
            if search_results:
                suggestions.append(
                    {
                        "entity": entity,
                        "confidence": 0.7,
                        "reason": f"Entité '{entity}' pourrait être liée à une note existante",
                    }
                )

        return suggestions[:5]  # Limit suggestions

    def _check_formatting(self, content: str) -> list[dict]:
        """Check for formatting issues"""
        issues = []

        # Check for inconsistent header levels
        headers = re.findall(r"^(#+)\s", content, re.MULTILINE)
        if headers:
            levels = [len(h) for h in headers]
            if levels and levels[0] != 1:
                issues.append(
                    {
                        "location": "headers",
                        "fix": None,
                        "reason": "Le premier titre devrait être de niveau 1 (#)",
                    }
                )

        # Check for trailing whitespace
        if re.search(r"[ \t]+$", content, re.MULTILINE):
            issues.append(
                {
                    "location": "whitespace",
                    "fix": re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE),
                    "reason": "Espaces en fin de ligne détectés",
                }
            )

        return issues

    async def _ai_analyze(self, context: ReviewContext) -> list[ReviewAction]:
        """Use AI to analyze note with Sancho integration"""
        if not self.ai_router:
            return []

        try:
            # We use the scrubbed content for the AI call to save tokens and avoid noise
            scrubbed_content = self._scrub_content(context.note.content)

            # Create a temporary note object for the router
            from copy import copy

            temp_note = copy(context.note)
            temp_note.content = scrubbed_content

            analysis = self.ai_router.analyze_note(temp_note, context.metadata)
            if not analysis:
                logger.info("DEBUG: AI Analysis is None/Empty")
                return []

            actions = []

            # Map AI proposed notes (enrichments) to review actions
            briefing_map = {"Profile": "Profile", "Projects": "Projects", "Goals": "Goals"}

            for prop in analysis.proposed_notes:
                # Note: AI might use 'note_id', 'target_note_id' or 'title' for targeting
                target_note_id = prop.get("target_note_id") or prop.get("note_id")
                title = prop.get("title", "")

                # Check if this is a Briefing update (Reflection Loop)
                is_briefing = False
                if title in briefing_map:
                    is_briefing = True
                    target_note_id = briefing_map[title]

                # If it's a proposal for the CURRENT note, we can map it to an action
                if target_note_id == context.note.note_id or not target_note_id:
                    # For now, map simple enrichments to ActionType.UPDATE or ActionType.ADD
                    actions.append(
                        ReviewAction(
                            action_type=ActionType.UPDATE,
                            target=prop.get("title", "Enrichment"),
                            content=prop.get("content"),
                            confidence=analysis.confidence,
                            reasoning=prop.get("reasoning", analysis.reasoning),
                            source="ai_analysis",
                        )
                    )
                elif is_briefing or target_note_id:
                    # Proposed update for an EXTERNAL note (Reflection Loop)
                    actions.append(
                        ReviewAction(
                            action_type=ActionType.ENRICH,
                            target=prop.get("title", "External Enrichment"),
                            content=prop.get("content_summary") or prop.get("content"),
                            confidence=analysis.confidence,
                            reasoning=prop.get("reasoning", analysis.reasoning),
                            source="ai_analysis",
                            target_note_id=target_note_id,
                        )
                    )

            # Map AI proposed tasks to review actions
            for task in analysis.proposed_tasks:
                actions.append(
                    ReviewAction(
                        action_type=ActionType.ADD,
                        target=task.get("title", "New Task"),
                        content=f"- [ ] {task.get('title')} #task",
                        confidence=analysis.confidence,
                        reasoning=task.get("reasoning", analysis.reasoning),
                        source="ai_analysis",
                    )
                )

            return actions

        except Exception as e:
            logger.warning(f"AI analysis integration failed: {e}", exc_info=True)
            return []

    def _should_auto_apply(self, action: ReviewAction) -> bool:
        """
        Determine if an action should be auto-applied based on its type and confidence

        Args:
            action: The review action to evaluate

        Returns:
            True if action should be auto-applied, False if it needs approval
        """
        # Destructive actions ALWAYS require approval
        if action.action_type in self.DESTRUCTIVE_ACTIONS:
            logger.info(
                f"Destructive action {action.action_type} requires approval (confidence={action.confidence})"
            )
            return False

        # Hygiene actions (mechanical) use lower threshold
        hygiene_actions = {ActionType.VALIDATE, ActionType.FORMAT, ActionType.FIX_LINKS}
        if action.action_type in hygiene_actions:
            return action.confidence >= self.HYGIENE_THRESHOLD

        # Semantic actions use standard threshold
        return action.confidence >= self.AUTO_APPLY_THRESHOLD

    def _apply_action(self, content: str, action: ReviewAction) -> str:
        """Apply a single action to content"""
        if action.action_type == ActionType.FORMAT:
            if action.content:
                return action.content
            return content

        if action.action_type == ActionType.ARCHIVE:
            # Move content to archive section
            archive_section = "\n\n---\n## Historique (archivé)\n"
            if archive_section not in content:
                content += archive_section
            # Add archived content
            content += (
                f"\n- {action.target} (archivé {datetime.now(timezone.utc).strftime('%Y-%m-%d')})"
            )
            # Remove from original location
            content = content.replace(action.target, "", 1)
            return content

        if action.action_type == ActionType.LINK:
            # Replace entity with wikilink
            if action.content:
                content = content.replace(action.target, action.content, 1)
            return content

        if action.action_type == ActionType.FIX_LINKS:
            # Fix broken wikilinks
            # action.target = old broken link, action.content = corrected link
            if action.target and action.content:
                # Replace [[BrokenLink]] with [[CorrectLink]]
                old_link = f"[[{action.target}]]"
                new_link = f"[[{action.content}]]"
                content = content.replace(old_link, new_link)
                logger.info(f"Fixed broken link: {action.target} -> {action.content}")
            return content

        if action.action_type == ActionType.VALIDATE:
            # Fix frontmatter validation issues
            # action.content contains the corrected frontmatter or field to add
            if action.content:
                # Simple implementation: append missing field info to metadata section
                # More sophisticated implementation would parse and update YAML
                logger.info(f"Frontmatter validation: {action.description}")
                # For now, just log - full implementation would update YAML frontmatter
            return content

        if action.action_type == ActionType.REFACTOR:
            # Reorganize content between linked notes
            # action.target = content to move, action.target_note_id = destination note
            if action.target and action.target_note_id:
                # Remove content from current note
                content = content.replace(action.target, "", 1)
                # Add a reference to where the content was moved
                reference = f"\n\n> [Déplacé vers [[{action.target_note_id}]]]\n"
                content += reference
                logger.info(
                    f"Refactored content to {action.target_note_id}: {action.target[:50]}..."
                )
                # Note: The actual addition to the target note is handled by _apply_external_action
            return content

        if action.action_type == ActionType.UPDATE:
            # Simple enrichment for the current note
            if action.content:
                # Append enrichment before archive or at end
                if "---" in content:
                    parts = content.split("---", 1)
                    return f"{parts[0].strip()}\n\n{action.content}\n\n---{parts[1]}"
                return f"{content.strip()}\n\n{action.content}"
            return content

        return content

    def _apply_external_action(self, action: ReviewAction) -> bool:
        """Apply an enrichment action to an external note (Reflection Loop)"""
        if not action.target_note_id or not action.content:
            return False

        target_note = self.notes.get_note(action.target_note_id)
        if not target_note:
            logger.warning(
                f"Could not find target note for external update: {action.target_note_id}"
            )
            return False

        # For Briefing files, we typically APPEND or ENRICH.
        # For now, we append the enrichment as a new bullet point or section.
        enrichment = (
            f"\n\n### Mise à jour Sancho ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n"
            f"{action.content}"
        )
        new_content = target_note.content + enrichment

        try:
            self.notes.update_note(note_id=action.target_note_id, content=new_content)
            logger.info(f"Successfully updated external note {action.target_note_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply external update to {action.target_note_id}: {e}")
            return False

    def _calculate_quality(
        self,
        analysis: ReviewAnalysis,
        _applied_count: int,
    ) -> int:
        """
        Calculate SM-2 quality score

        Quality Scale:
            5 - No changes needed
            4 - Minor formatting only
            3 - Small additions
            2 - Moderate updates
            1 - Significant changes
            0 - Major overhaul
        """
        total_actions = len(analysis.suggested_actions)

        if total_actions == 0:
            return 5

        # Count action types
        format_only = all(a.action_type == ActionType.FORMAT for a in analysis.suggested_actions)
        link_only = all(
            a.action_type in (ActionType.FORMAT, ActionType.LINK)
            for a in analysis.suggested_actions
        )

        if format_only:
            return 4
        if link_only and total_actions <= 3:
            return 3
        if total_actions <= 5:
            return 2
        if total_actions <= 10:
            return 1
        return 0
