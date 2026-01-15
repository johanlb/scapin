"""
Entity Search Module — Option D Implementation

Provides entity-based local search on notes using exact and fuzzy matching.
This is used BEFORE the main semantic search to find notes by entity names.

Key features:
- Exact match on note titles
- Fuzzy match using difflib (no external dependencies)
- Partial match (entity name appears in note title)
- Integration with ScapinConfig for entity resolution rules

Part of the v2.2+ context retrieval improvements.
See TODO list item "Option D" for design decisions.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.scapin_config import ScapinConfigReader, get_scapin_config
from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.passepartout.note_manager import Note, NoteManager

logger = get_logger("entity_search")


# Fuzzy matching thresholds
EXACT_MATCH_SCORE = 1.0
HIGH_FUZZY_THRESHOLD = 0.85  # "Marc Dupont" vs "Marc Dupont - Tech Lead"
MEDIUM_FUZZY_THRESHOLD = 0.70  # "M. Dupont" vs "Marc Dupont"
PARTIAL_MATCH_SCORE = 0.80  # Entity name fully contained in title


@dataclass
class EntitySearchResult:
    """Result of an entity search"""

    note: "Note"
    entity_name: str  # The searched entity name
    matched_title: str  # The note title that matched
    match_type: str  # "exact", "fuzzy", "partial", "content"
    match_score: float  # 0.0 to 1.0
    is_my_entity: bool = False  # From ScapinConfig
    is_vip: bool = False  # From ScapinConfig

    def __repr__(self) -> str:
        return (
            f"EntitySearchResult(entity='{self.entity_name}', "
            f"note='{self.matched_title}', type={self.match_type}, "
            f"score={self.match_score:.2f})"
        )


@dataclass
class EntitySearchStats:
    """Statistics for entity search"""

    entities_searched: int = 0
    exact_matches: int = 0
    fuzzy_matches: int = 0
    partial_matches: int = 0
    content_matches: int = 0
    total_results: int = 0


class EntitySearcher:
    """
    Entity-based search on notes using exact and fuzzy matching.

    This complements the semantic search in ContextEngine by providing
    precise entity matching based on note titles.

    Usage:
        searcher = EntitySearcher(note_manager)
        results = searcher.search_entities(["Marc Dupont", "Projet Alpha"])
        for result in results:
            print(f"{result.entity_name} -> {result.matched_title} ({result.match_type})")
    """

    def __init__(
        self,
        note_manager: "NoteManager",
        scapin_config: ScapinConfigReader | None = None,
        fuzzy_threshold: float = MEDIUM_FUZZY_THRESHOLD,
        search_content: bool = True,
        max_results_per_entity: int = 3,
    ):
        """
        Initialize the entity searcher.

        Args:
            note_manager: NoteManager instance for note access
            scapin_config: ScapinConfigReader for entity rules (auto-loads if None)
            fuzzy_threshold: Minimum similarity for fuzzy matching (0.0-1.0)
            search_content: Whether to search in note content too
            max_results_per_entity: Max results to return per entity
        """
        self.note_manager = note_manager
        self._scapin_config = scapin_config
        self.fuzzy_threshold = fuzzy_threshold
        self.search_content = search_content
        self.max_results_per_entity = max_results_per_entity

        # Cache for note titles (rebuilt on search if stale)
        self._title_cache: dict[str, Note] = {}
        self._title_cache_valid = False

        logger.info(
            "EntitySearcher initialized",
            extra={
                "fuzzy_threshold": fuzzy_threshold,
                "search_content": search_content,
                "max_per_entity": max_results_per_entity,
            },
        )

    @property
    def scapin_config(self) -> ScapinConfigReader:
        """Get or lazy-load ScapinConfig"""
        if self._scapin_config is None:
            try:
                notes_path = Path(self.note_manager.notes_dir)
                self._scapin_config = get_scapin_config(notes_path)
            except Exception as e:
                logger.warning(f"Could not load ScapinConfig: {e}")
                # Create a dummy config
                self._scapin_config = ScapinConfigReader(
                    self.note_manager.notes_dir
                )
        return self._scapin_config

    def _rebuild_title_cache(self) -> None:
        """Rebuild the title -> note cache"""
        self._title_cache.clear()

        try:
            all_notes = self.note_manager.get_all_notes()
            for note in all_notes:
                # Store by lowercase title for case-insensitive matching
                title_lower = note.title.lower().strip()
                self._title_cache[title_lower] = note

            self._title_cache_valid = True
            logger.debug(f"Title cache rebuilt with {len(self._title_cache)} notes")

        except Exception as e:
            logger.error(f"Failed to rebuild title cache: {e}")
            self._title_cache_valid = False

    def _normalize_name(self, name: str) -> str:
        """
        Normalize an entity name for matching.

        Handles:
        - Case normalization
        - Whitespace cleanup
        - Common abbreviations (M., Mme, Dr, etc.)
        """
        name = name.lower().strip()

        # Expand common French abbreviations
        abbreviations = {
            "m.": "monsieur",
            "mme": "madame",
            "mme.": "madame",
            "mlle": "mademoiselle",
            "mlle.": "mademoiselle",
            "dr": "docteur",
            "dr.": "docteur",
            "pr": "professeur",
            "pr.": "professeur",
        }

        for abbr, _full in abbreviations.items():
            if name.startswith(abbr + " "):
                name = name.replace(abbr + " ", "", 1)
                break

        return name

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """
        Calculate fuzzy match score between two strings.

        Uses difflib's SequenceMatcher which is good for human names.

        Args:
            s1: First string (normalized)
            s2: Second string (normalized)

        Returns:
            Similarity score between 0.0 and 1.0
        """
        return SequenceMatcher(None, s1, s2).ratio()

    def _extract_name_from_title(self, title: str) -> str:
        """
        Extract the main name from a note title.

        Handles patterns like:
        - "Marc Dupont" -> "Marc Dupont"
        - "Marc Dupont - Tech Lead" -> "Marc Dupont"
        - "Projet Alpha (2024)" -> "Projet Alpha"
        """
        title = title.strip()

        # Split on common separators
        separators = [" - ", " – ", " — ", " | ", " ("]
        for sep in separators:
            if sep in title:
                title = title.split(sep)[0].strip()
                break

        return title

    def search_entities(
        self,
        entity_names: list[str],
        include_content_search: bool | None = None,
    ) -> list[EntitySearchResult]:
        """
        Search for notes matching the given entity names.

        Args:
            entity_names: List of entity names to search for
            include_content_search: Override self.search_content for this call

        Returns:
            List of EntitySearchResult sorted by match score (descending)
        """
        if include_content_search is None:
            include_content_search = self.search_content

        # Rebuild cache if needed
        if not self._title_cache_valid:
            self._rebuild_title_cache()

        results: list[EntitySearchResult] = []
        stats = EntitySearchStats(entities_searched=len(entity_names))

        for entity_name in entity_names:
            entity_results = self._search_single_entity(
                entity_name, include_content_search
            )

            # Apply ScapinConfig rules
            for result in entity_results:
                result.is_my_entity = self.scapin_config.is_my_entity(entity_name)
                result.is_vip = self.scapin_config.is_vip_contact(entity_name)

            # Update stats
            for r in entity_results:
                if r.match_type == "exact":
                    stats.exact_matches += 1
                elif r.match_type == "fuzzy":
                    stats.fuzzy_matches += 1
                elif r.match_type == "partial":
                    stats.partial_matches += 1
                elif r.match_type == "content":
                    stats.content_matches += 1

            # Limit results per entity
            results.extend(entity_results[: self.max_results_per_entity])

        # Sort all results by score
        results.sort(key=lambda r: r.match_score, reverse=True)

        stats.total_results = len(results)
        logger.info(
            "Entity search completed",
            extra={
                "entities": len(entity_names),
                "exact": stats.exact_matches,
                "fuzzy": stats.fuzzy_matches,
                "partial": stats.partial_matches,
                "content": stats.content_matches,
                "total": stats.total_results,
            },
        )

        return results

    def _search_single_entity(
        self,
        entity_name: str,
        include_content_search: bool,
    ) -> list[EntitySearchResult]:
        """Search for a single entity name"""
        results: list[EntitySearchResult] = []
        normalized_entity = self._normalize_name(entity_name)

        # Track seen note IDs to avoid duplicates
        seen_note_ids: set[str] = set()

        # 1. Exact match on title
        if normalized_entity in self._title_cache:
            note = self._title_cache[normalized_entity]
            results.append(
                EntitySearchResult(
                    note=note,
                    entity_name=entity_name,
                    matched_title=note.title,
                    match_type="exact",
                    match_score=EXACT_MATCH_SCORE,
                )
            )
            seen_note_ids.add(note.note_id)

        # 2. Fuzzy match on titles
        for title_lower, note in self._title_cache.items():
            if note.note_id in seen_note_ids:
                continue

            # Extract main name from title for comparison
            title_name = self._extract_name_from_title(title_lower)
            title_name_normalized = self._normalize_name(title_name)

            # Calculate fuzzy score
            score = self._fuzzy_match(normalized_entity, title_name_normalized)

            if score >= self.fuzzy_threshold:
                results.append(
                    EntitySearchResult(
                        note=note,
                        entity_name=entity_name,
                        matched_title=note.title,
                        match_type="fuzzy",
                        match_score=score,
                    )
                )
                seen_note_ids.add(note.note_id)

            # 3. Partial match - entity name contained in title
            elif normalized_entity in title_lower:
                results.append(
                    EntitySearchResult(
                        note=note,
                        entity_name=entity_name,
                        matched_title=note.title,
                        match_type="partial",
                        match_score=PARTIAL_MATCH_SCORE,
                    )
                )
                seen_note_ids.add(note.note_id)

        # 4. Content search (if enabled and not enough results)
        if include_content_search and len(results) < self.max_results_per_entity:
            content_results = self._search_in_content(
                entity_name,
                normalized_entity,
                seen_note_ids,
                limit=self.max_results_per_entity - len(results),
            )
            results.extend(content_results)

        # Sort by score
        results.sort(key=lambda r: r.match_score, reverse=True)

        return results

    def _search_in_content(
        self,
        entity_name: str,
        normalized_entity: str,
        exclude_ids: set[str],
        limit: int,
    ) -> list[EntitySearchResult]:
        """Search for entity name in note content"""
        results: list[EntitySearchResult] = []

        for note in self._title_cache.values():
            if note.note_id in exclude_ids:
                continue

            if len(results) >= limit:
                break

            # Check if entity name appears in content
            content_lower = (note.content or "").lower()
            if normalized_entity in content_lower:
                # Calculate a relevance score based on mention count
                mention_count = content_lower.count(normalized_entity)
                # Score: 0.5 base + up to 0.2 for multiple mentions
                score = min(0.7, 0.5 + (mention_count - 1) * 0.05)

                results.append(
                    EntitySearchResult(
                        note=note,
                        entity_name=entity_name,
                        matched_title=note.title,
                        match_type="content",
                        match_score=score,
                    )
                )

        return results

    def invalidate_cache(self) -> None:
        """Invalidate the title cache (call after note changes)"""
        self._title_cache_valid = False
        logger.debug("Title cache invalidated")

    def get_entity_resolution_rule(
        self,
        person_name: str,
        company_name: str | None,
    ) -> str:
        """
        Get the entity resolution rule for a person.

        Returns:
            "person" if should create individual person note
            "company" if should enrich company note
        """
        if self.scapin_config.should_create_person_note(person_name, company_name):
            return "person"
        return "company"


def create_entity_searcher(
    note_manager: "NoteManager",
    notes_dir: str | Path | None = None,
) -> EntitySearcher:
    """
    Factory function to create an EntitySearcher.

    Args:
        note_manager: NoteManager instance
        notes_dir: Notes directory for ScapinConfig (uses note_manager's dir if None)

    Returns:
        Configured EntitySearcher instance
    """
    notes_path = notes_dir or note_manager.notes_dir
    scapin_config = get_scapin_config(notes_path)

    return EntitySearcher(
        note_manager=note_manager,
        scapin_config=scapin_config,
    )
