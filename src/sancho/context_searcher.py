"""
Context Searcher for Multi-Pass Analysis

Wrapper that coordinates searches across NoteManager and CrossSourceEngine
to build structured context for the multi-pass analyzer.

Part of Sancho's multi-pass extraction system (v2.2).
See ADR-002 in MULTI_PASS_SPEC.md for design decisions.

Key responsibilities:
- Search notes by entity names
- Search across sources (calendar, email, tasks)
- Build EntityProfile from search results
- Detect conflicts across sources
- Return structured context for prompt injection
"""

import asyncio
import functools
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.passepartout.cross_source.engine import CrossSourceEngine
    from src.passepartout.entity_search import EntitySearcher
    from src.passepartout.note_manager import Note, NoteManager

logger = get_logger("context_searcher")


@dataclass
class NoteContextBlock:
    """A note result for context injection"""

    note_id: str
    title: str
    note_type: str  # personne, projet, entreprise, concept, etc.
    summary: str
    relevance: float  # 0-1 relevance score
    last_modified: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """Format for prompt injection"""
        return f"📝 **{self.title}** ({self.note_type}, relevance: {self.relevance * 100:.0f}%)\n> {self.summary[:200]}"


@dataclass
class CalendarContextBlock:
    """A calendar event for context injection"""

    event_id: str
    title: str
    date: str  # YYYY-MM-DD
    time: Optional[str]  # HH:MM
    participants: list[str] = field(default_factory=list)
    location: Optional[str] = None
    relevance: float = 0.5

    def to_prompt_block(self) -> str:
        """Format for prompt injection"""
        time_str = f" {self.time}" if self.time else ""
        participants_str = f" ({', '.join(self.participants)})" if self.participants else ""
        return f"📅 {self.date}{time_str}: **{self.title}**{participants_str}"


@dataclass
class TaskContextBlock:
    """A task for context injection"""

    task_id: str
    title: str
    project: Optional[str] = None
    due_date: Optional[str] = None
    status: str = "active"  # active, completed, deferred
    relevance: float = 0.5

    def to_prompt_block(self) -> str:
        """Format for prompt injection"""
        due_str = f" (due: {self.due_date})" if self.due_date else ""
        project_str = f" [{self.project}]" if self.project else ""
        return f"⚡ {self.title}{project_str}{due_str}"


@dataclass
class EmailContextBlock:
    """An email from history for context injection"""

    message_id: str
    subject: str
    sender: str
    date: str  # YYYY-MM-DD
    snippet: str
    relevance: float = 0.5

    def to_prompt_block(self) -> str:
        """Format for prompt injection"""
        return f"✉️ {self.date} - **{self.subject}** (de {self.sender})\n> {self.snippet[:150]}"


@dataclass
class ConflictBlock:
    """A detected conflict between sources"""

    conflict_type: str  # calendar_overlap, duplicate_info, ambiguous_entity
    description: str
    options: list[str] = field(default_factory=list)
    severity: str = "minor"  # minor, major, critical

    def to_prompt_block(self) -> str:
        """Format for prompt injection"""
        options_str = " | ".join(self.options) if self.options else ""
        return f"⚠️ **{self.conflict_type}**: {self.description}\n  Options: {options_str}"


@dataclass
class EntityProfile:
    """Consolidated profile of an entity from multiple sources"""

    name: str
    canonical_name: str  # Name in PKM notes
    entity_type: str  # personne, entreprise, projet, etc.
    role: Optional[str] = None  # "Tech Lead", "Client", etc.
    relationship: Optional[str] = None  # "Collègue", "Manager", etc.
    last_interaction: Optional[datetime] = None
    key_facts: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    source_note_id: Optional[str] = None

    def to_prompt_block(self) -> str:
        """Format for prompt injection"""
        lines = [f"### {self.canonical_name} ({self.entity_type})"]
        if self.role:
            lines.append(f"- **Rôle**: {self.role}")
        if self.relationship:
            lines.append(f"- **Relation**: {self.relationship}")
        if self.last_interaction:
            lines.append(
                f"- **Dernière interaction**: {self.last_interaction.strftime('%Y-%m-%d')}"
            )
        if self.key_facts:
            lines.append("- **Faits clés**:")
            for fact in self.key_facts[:5]:
                lines.append(f"  - {fact}")
        return "\n".join(lines)


@dataclass
class StructuredContext:
    """Structured context for prompt injection"""

    # Metadata
    query_entities: list[str]
    search_timestamp: datetime
    sources_searched: list[str]

    # Results by source
    notes: list[NoteContextBlock] = field(default_factory=list)
    calendar: list[CalendarContextBlock] = field(default_factory=list)
    tasks: list[TaskContextBlock] = field(default_factory=list)
    emails: list[EmailContextBlock] = field(default_factory=list)

    # Synthesis
    entity_profiles: dict[str, EntityProfile] = field(default_factory=dict)
    conflicts: list[ConflictBlock] = field(default_factory=list)

    def to_prompt_format(self) -> str:
        """Generate formatted context for prompt injection"""
        sections = []

        # Entity profiles (most important)
        if self.entity_profiles:
            profiles_section = ["### Profils des Entités Mentionnées"]
            for profile in self.entity_profiles.values():
                profiles_section.append(profile.to_prompt_block())
            sections.append("\n\n".join(profiles_section))

        # Relevant notes
        if self.notes:
            notes_section = ["### Notes PKM Pertinentes"]
            for note in self.notes[:5]:
                notes_section.append(note.to_prompt_block())
            sections.append("\n".join(notes_section))

        # Calendar events
        if self.calendar:
            calendar_section = ["### Événements Calendar Liés"]
            for event in self.calendar[:5]:
                calendar_section.append(event.to_prompt_block())
            sections.append("\n".join(calendar_section))

        # Tasks
        if self.tasks:
            tasks_section = ["### Tâches OmniFocus Existantes"]
            for task in self.tasks[:5]:
                tasks_section.append(task.to_prompt_block())
            sections.append("\n".join(tasks_section))

        # Email history
        if self.emails:
            emails_section = ["### Historique Email"]
            for email in self.emails[:3]:
                emails_section.append(email.to_prompt_block())
            sections.append("\n".join(emails_section))

        # Conflicts
        if self.conflicts:
            conflicts_section = ["### ⚠️ Conflits Détectés"]
            for conflict in self.conflicts:
                conflicts_section.append(conflict.to_prompt_block())
            sections.append("\n".join(conflicts_section))

        return "\n\n".join(sections) if sections else ""

    @property
    def is_empty(self) -> bool:
        """Check if context is empty"""
        return (
            not self.notes
            and not self.calendar
            and not self.tasks
            and not self.emails
            and not self.entity_profiles
        )

    @property
    def total_results(self) -> int:
        """Total number of results across all sources"""
        return len(self.notes) + len(self.calendar) + len(self.tasks) + len(self.emails)


@dataclass
class ContextSearchConfig:
    """Configuration for context search"""

    max_notes: int = 10  # Increased from 5 for better context (Option D)
    max_calendar_events: int = 10
    max_tasks: int = 5
    max_emails: int = 5
    min_relevance: float = 0.3
    include_calendar: bool = True
    include_tasks: bool = True
    include_emails: bool = True
    calendar_days_behind: int = 30
    calendar_days_ahead: int = 14
    # Option D: Entity-based search before semantic search
    use_entity_search: bool = True
    entity_fuzzy_threshold: float = 0.70


class ContextSearcher:
    """
    Context searcher for multi-pass analysis.

    Coordinates searches across NoteManager, EntitySearcher and CrossSourceEngine
    to build structured context for prompt injection.

    Option D Enhancement (v2.2+):
    - First uses EntitySearcher for exact/fuzzy name matching on note titles
    - Then falls back to semantic search for additional context
    - Applies ScapinConfig rules for entity resolution

    Usage:
        searcher = ContextSearcher(note_manager, cross_source_engine)
        context = await searcher.search_for_entities(
            ["Marc Dupont", "Projet Alpha"],
            config=ContextSearchConfig(max_notes=10)
        )
        prompt_context = context.to_prompt_format()
    """

    def __init__(
        self,
        note_manager: Optional["NoteManager"] = None,
        cross_source_engine: Optional["CrossSourceEngine"] = None,
        entity_searcher: Optional["EntitySearcher"] = None,
    ) -> None:
        """
        Initialize the context searcher.

        Args:
            note_manager: NoteManager instance for PKM search
            cross_source_engine: CrossSourceEngine for cross-source search
            entity_searcher: EntitySearcher for entity-based search (Option D)
        """
        self._note_manager = note_manager
        self._cross_source = cross_source_engine
        self._entity_searcher = entity_searcher

        # Lazy-load EntitySearcher if note_manager is available but no searcher provided
        self._entity_searcher_loaded = entity_searcher is not None

        logger.info(
            "ContextSearcher initialized (notes=%s, cross_source=%s, entity_search=%s)",
            note_manager is not None,
            cross_source_engine is not None,
            entity_searcher is not None,
        )

    @property
    def has_note_manager(self) -> bool:
        """Check if note manager is available"""
        return self._note_manager is not None

    @property
    def has_cross_source(self) -> bool:
        """Check if cross source engine is available"""
        return self._cross_source is not None

    @property
    def entity_searcher(self) -> "EntitySearcher | None":
        """Get or lazy-load EntitySearcher (Option D)"""
        if not self._entity_searcher_loaded and self._note_manager is not None:
            try:
                from src.passepartout.entity_search import EntitySearcher

                self._entity_searcher = EntitySearcher(
                    note_manager=self._note_manager,
                )
                self._entity_searcher_loaded = True
                logger.debug("EntitySearcher lazy-loaded for Option D")
            except Exception as e:
                logger.warning("Could not load EntitySearcher: %s", e)
                self._entity_searcher_loaded = True  # Don't retry

        return self._entity_searcher

    async def search_for_entities(
        self,
        entities: list[str],
        config: Optional[ContextSearchConfig] = None,
        sender_email: Optional[str] = None,
    ) -> StructuredContext:
        """
        Search for context related to the given entities.

        Args:
            entities: List of entity names to search for
            config: Search configuration
            sender_email: Optional sender email for email history search

        Returns:
            StructuredContext with all found information
        """
        if config is None:
            config = ContextSearchConfig()

        start_time = datetime.now()
        sources_searched: list[str] = []

        # Initialize result containers
        notes: list[NoteContextBlock] = []
        calendar: list[CalendarContextBlock] = []
        tasks: list[TaskContextBlock] = []
        emails: list[EmailContextBlock] = []
        entity_profiles: dict[str, EntityProfile] = {}

        # 1. Search notes by entity names (Option D: entity search + semantic)
        if self._note_manager is not None:
            sources_searched.append("notes")
            # Run in executor to avoid blocking loop with extensive search/file I/O
            loop = asyncio.get_running_loop()
            notes, entity_profiles = await loop.run_in_executor(
                None, functools.partial(self._search_notes, entities, config)
            )

        # 2. Search cross-source if available
        if self._cross_source is not None:
            # Build query from entities
            query = " OR ".join(entities)

            # Search calendar
            if config.include_calendar:
                sources_searched.append("calendar")
                calendar = await self._search_calendar(query, entities, config.max_calendar_events)

            # Search tasks
            if config.include_tasks:
                sources_searched.append("tasks")
                tasks = await self._search_tasks(query, config.max_tasks)

            # Search email history
            if config.include_emails and sender_email:
                sources_searched.append("email")
                emails = await self._search_emails(sender_email, config.max_emails)

        # 3. Detect conflicts
        conflicts = self._detect_conflicts(notes, calendar, tasks)

        logger.debug(
            "Context search completed in %.2fs (notes=%d, calendar=%d, tasks=%d, emails=%d)",
            (datetime.now() - start_time).total_seconds(),
            len(notes),
            len(calendar),
            len(tasks),
            len(emails),
        )

        return StructuredContext(
            query_entities=entities,
            search_timestamp=start_time,
            sources_searched=sources_searched,
            notes=notes,
            calendar=calendar,
            tasks=tasks,
            emails=emails,
            entity_profiles=entity_profiles,
            conflicts=conflicts,
        )

    def _search_notes(
        self,
        entities: list[str],
        config: ContextSearchConfig,
    ) -> tuple[list[NoteContextBlock], dict[str, EntityProfile]]:
        """
        Search notes for entities using Option D approach.

        Option D: Entity-based search FIRST, then semantic search for additional results.
        This gives better precision for known entities while still finding related context.

        Args:
            entities: List of entity names to search for
            config: Search configuration with max_notes, min_relevance, etc.

        Returns:
            Tuple of (note_blocks, entity_profiles)
        """
        notes: list[NoteContextBlock] = []
        profiles: dict[str, EntityProfile] = {}
        seen_ids: set[str] = set()

        if self._note_manager is None:
            return notes, profiles

        max_results = config.max_notes
        min_relevance = config.min_relevance

        # STEP 1: Entity-based search (Option D) - exact/fuzzy matching on titles
        if config.use_entity_search and self.entity_searcher is not None:
            try:
                entity_results = self.entity_searcher.search_entities(entities)

                for result in entity_results:
                    if result.note.note_id in seen_ids:
                        continue

                    note = result.note
                    seen_ids.add(note.note_id)

                    # Create note context block with entity match info
                    note_block = NoteContextBlock(
                        note_id=note.note_id,
                        title=note.title,
                        note_type=getattr(note, "type", None) or "note",
                        summary=(note.content[:200] if note.content else ""),
                        relevance=min(1.0, result.match_score),
                        last_modified=getattr(note, "modified_at", None),
                        tags=note.tags or [],
                    )
                    notes.append(note_block)

                    # Build entity profile if note is about a person/project/company
                    note_type = getattr(note, "type", None)
                    if note_type in ["personne", "projet", "entreprise"]:
                        profile = self._build_profile_from_note(
                            result.entity_name, note, result.match_score
                        )
                        if profile and result.entity_name not in profiles:
                            # Add is_my_entity info to profile
                            if result.is_my_entity:
                                profile.relationship = "Mon équipe"
                            profiles[result.entity_name] = profile

                logger.debug(
                    "Entity search found %d notes for %d entities",
                    len(notes),
                    len(entities),
                )

            except Exception as e:
                logger.warning("Entity search failed, falling back to semantic: %s", e)

        # STEP 2: Semantic search for additional results (if we need more)
        remaining_slots = max_results - len(notes)
        if remaining_slots > 0:
            for entity in entities:
                try:
                    # Semantic search for notes matching this entity
                    results = self._note_manager.search_notes(
                        query=entity,
                        top_k=remaining_slots,
                        return_scores=True,
                    )

                    for note, score in results:
                        if note.note_id in seen_ids:
                            continue
                        if score < min_relevance:
                            continue

                        seen_ids.add(note.note_id)

                        # Create note context block
                        note_block = NoteContextBlock(
                            note_id=note.note_id,
                            title=note.title,
                            note_type=getattr(note, "type", None) or "note",
                            summary=(note.content[:200] if note.content else ""),
                            relevance=min(1.0, score),
                            last_modified=getattr(note, "modified_at", None),
                            tags=note.tags or [],
                        )
                        notes.append(note_block)

                        # Build entity profile if note is about a person/project
                        note_type = getattr(note, "type", None)
                        if note_type in ["personne", "projet", "entreprise"]:
                            profile = self._build_profile_from_note(entity, note, score)
                            if profile and entity not in profiles:
                                profiles[entity] = profile

                        if len(notes) >= max_results:
                            break

                except Exception as e:
                    logger.warning("Semantic search failed for entity %s: %s", entity, e)

                if len(notes) >= max_results:
                    break

        # Sort by relevance (entity matches typically have higher scores)
        notes.sort(key=lambda n: n.relevance, reverse=True)

        logger.info(
            "Note search completed: %d entity matches + %d semantic = %d total",
            len([n for n in notes if n.relevance >= 0.7]),
            len([n for n in notes if n.relevance < 0.7]),
            len(notes),
        )

        return notes[:max_results], profiles

    def _build_profile_from_note(
        self,
        entity_name: str,
        note: "Note",
        _relevance: float,
    ) -> Optional[EntityProfile]:
        """Build an entity profile from a note"""
        try:
            import re

            # Extract key facts from note content
            key_facts = []
            if note.content:
                # Take first few lines as key facts
                lines = [
                    line.strip()
                    for line in note.content.split("\n")
                    if line.strip() and not line.startswith("#")
                ]
                key_facts = lines[:5]

            # Extract related entities from wikilinks
            related = []
            if note.content:
                wikilinks = re.findall(r"\[\[([^\]]+)\]\]", note.content)
                related = [link for link in wikilinks if link != note.title][:5]

            # Get note type from metadata (Note class doesn't have .type attribute)
            note_type = note.metadata.get("type", "entity") if note.metadata else "entity"

            return EntityProfile(
                name=entity_name,
                canonical_name=note.title,
                entity_type=note_type,
                role=note.metadata.get("role") if note.metadata else None,
                relationship=note.metadata.get("relationship") if note.metadata else None,
                last_interaction=note.updated_at,  # Note uses updated_at, not modified_at
                key_facts=key_facts,
                related_entities=related,
                source_note_id=note.note_id,  # Note uses note_id, not id
            )
        except Exception as e:
            logger.warning("Error building profile from note: %s", e)
            return None

    async def _search_calendar(
        self,
        query: str,
        _entities: list[str],
        max_results: int,
    ) -> list[CalendarContextBlock]:
        """Search calendar events"""
        events: list[CalendarContextBlock] = []

        if self._cross_source is None:
            return events

        try:
            result = await self._cross_source.search(
                query=query,
                preferred_sources=["calendar"],
                max_results=max_results,
            )

            for item in result.items:
                if item.source == "calendar":
                    # Extract participants from metadata
                    participants = []
                    if item.metadata:
                        participants = item.metadata.get("participants", [])

                    event = CalendarContextBlock(
                        event_id=item.id,
                        title=item.title,
                        date=item.metadata.get("date", "") if item.metadata else "",
                        time=item.metadata.get("time") if item.metadata else None,
                        participants=participants,
                        location=item.metadata.get("location") if item.metadata else None,
                        relevance=min(1.0, item.final_score),
                    )
                    events.append(event)

        except Exception as e:
            logger.warning("Error searching calendar: %s", e)

        return events[:max_results]

    async def _search_tasks(
        self,
        query: str,
        max_results: int,
    ) -> list[TaskContextBlock]:
        """Search tasks in OmniFocus"""
        tasks: list[TaskContextBlock] = []

        if self._cross_source is None:
            return tasks

        try:
            result = await self._cross_source.search(
                query=query,
                preferred_sources=["omnifocus"],
                max_results=max_results,
            )

            for item in result.items:
                if item.source == "omnifocus":
                    task = TaskContextBlock(
                        task_id=item.id,
                        title=item.title,
                        project=item.metadata.get("project") if item.metadata else None,
                        due_date=item.metadata.get("due_date") if item.metadata else None,
                        status=item.metadata.get("status", "active") if item.metadata else "active",
                        relevance=min(1.0, item.final_score),
                    )
                    tasks.append(task)

        except Exception as e:
            logger.warning("Error searching tasks: %s", e)

        return tasks[:max_results]

    async def _search_emails(
        self,
        sender_email: str,
        max_results: int,
    ) -> list[EmailContextBlock]:
        """Search email history with sender"""
        emails: list[EmailContextBlock] = []

        if self._cross_source is None:
            return emails

        try:
            result = await self._cross_source.search(
                query=f"from:{sender_email}",
                preferred_sources=["email"],
                max_results=max_results,
            )

            for item in result.items:
                if item.source == "email":
                    email = EmailContextBlock(
                        message_id=item.id,
                        subject=item.title,
                        sender=item.metadata.get("sender", sender_email)
                        if item.metadata
                        else sender_email,
                        date=item.metadata.get("date", "") if item.metadata else "",
                        snippet=item.snippet or "",
                        relevance=min(1.0, item.final_score),
                    )
                    emails.append(email)

        except Exception as e:
            logger.warning("Error searching emails: %s", e)

        return emails[:max_results]

    def _detect_conflicts(
        self,
        notes: list[NoteContextBlock],
        calendar: list[CalendarContextBlock],
        _tasks: list[TaskContextBlock],
    ) -> list[ConflictBlock]:
        """Detect conflicts across sources"""
        conflicts: list[ConflictBlock] = []

        # Detect calendar overlaps
        if len(calendar) >= 2:
            dates = [e.date for e in calendar]
            if len(dates) != len(set(dates)):
                conflicts.append(
                    ConflictBlock(
                        conflict_type="calendar_overlap",
                        description="Plusieurs événements trouvés à la même date",
                        options=[e.title for e in calendar[:3]],
                        severity="minor",
                    )
                )

        # Detect duplicate info between notes
        if len(notes) >= 2:
            titles = [n.title for n in notes]
            for i, title in enumerate(titles):
                for _j, other_title in enumerate(titles[i + 1 :], i + 1):
                    # Check if titles are very similar
                    if self._similar_strings(title, other_title):
                        conflicts.append(
                            ConflictBlock(
                                conflict_type="duplicate_info",
                                description=f"Notes similaires: '{title}' et '{other_title}'",
                                options=[title, other_title],
                                severity="minor",
                            )
                        )
                        break

        return conflicts

    def _similar_strings(self, a: str, b: str, threshold: float = 0.8) -> bool:
        """Check if two strings are similar (simple ratio)"""
        if not a or not b:
            return False
        a_lower = a.lower()
        b_lower = b.lower()
        if a_lower == b_lower:
            return True
        # Simple word overlap check
        words_a = set(a_lower.split())
        words_b = set(b_lower.split())
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
        return overlap >= threshold
