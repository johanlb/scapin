"""
Coherence Service — Validates and maintains coherence across PKM notes.

This module provides coherence validation as a REUSABLE SERVICE with multiple modes:

1. EXTRACTION MODE (during email analysis):
   - Validates proposed extractions against existing notes
   - Ensures enrichir > creer preference
   - Detects duplicates before writing

2. NOTE MAINTENANCE MODE (background service - future):
   - Analyzes individual notes for internal coherence
   - Finds and analyzes related notes
   - Suggests refactoring (merge, split, deduplicate)

3. BATCH ANALYSIS MODE (on-demand - future):
   - Analyzes a set of notes together
   - Detects cross-note duplicates
   - Suggests consolidation

The service is designed to be called from:
- MultiPassAnalyzer (email processing)
- BackgroundNoteWorker (future maintenance service)
- API endpoints (manual coherence checks)

Part of the Multi-Pass v2.2+ architecture.
See COHERENCE_PASS_SPEC.md for design decisions.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.monitoring.logger import get_logger
from src.sancho.convergence import Extraction
from src.sancho.router import AIModel
from src.sancho.template_renderer import TemplateRenderer

if TYPE_CHECKING:
    from src.core.events import PerceivedEvent
    from src.passepartout.entity_search import EntitySearcher
    from src.passepartout.note_manager import Note, NoteManager
    from src.sancho.router import AIRouter

logger = get_logger("coherence_validator")


# Section mapping by extraction type
SECTION_SUGGESTIONS: dict[str, list[str]] = {
    "deadline": ["## Actions", "## À faire", "## Suivi", "## Deadlines"],
    "engagement": ["## Actions", "## À faire", "## Engagements", "## Suivi"],
    "fait": ["## Historique", "## Notes", "## Événements", "## Faits"],
    "decision": ["## Historique", "## Décisions", "## Notes"],
    "coordonnees": ["## Contact", "## Coordonnées", "## Infos"],
    "montant": ["## Finances", "## Budget", "## Transactions", "## Montants"],
    "relation": ["## Relations", "## Contexte", "## Liens", "## Réseau"],
    "reference": ["## Références", "## Documents", "## Liens"],
    "demande": ["## Actions", "## À faire", "## Demandes"],
    "evenement": ["## Événements", "## Calendrier", "## Historique"],
}


@dataclass
class FullNoteContext:
    """Full note context for coherence validation."""

    title: str
    full_content: str
    sections: list[str] = field(default_factory=list)
    entry_count: int = 0
    last_modified: datetime | None = None
    note_type: str = "unknown"
    file_path: str = ""

    @classmethod
    def from_note(cls, note: "Note", content: str) -> "FullNoteContext":
        """Create from a Note object and its content."""
        sections = cls._extract_sections(content)
        entry_count = cls._count_entries(content)

        return cls(
            title=note.title,
            full_content=content,
            sections=sections,
            entry_count=entry_count,
            last_modified=note.updated_at,
            note_type=note.metadata.get("type", "unknown") if note.metadata else "unknown",
            file_path=str(note.file_path) if note.file_path else "",
        )

    @staticmethod
    def _extract_sections(content: str) -> list[str]:
        """Extract ## headers from content."""
        sections = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("## "):
                sections.append(line)
        return sections

    @staticmethod
    def _count_entries(content: str) -> int:
        """Count entries (lines starting with - or * or ###)."""
        count = 0
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* ") or line.startswith("### "):
                count += 1
        return count


@dataclass
class SimilarNote:
    """A similar note that could be an alternative target."""

    title: str
    match_score: float
    match_type: str  # "exact", "fuzzy", "partial"
    sections: list[str] = field(default_factory=list)
    snippet: str = ""


@dataclass
class ValidatedExtraction:
    """An extraction after coherence validation."""

    # Original values
    original_note_cible: str | None
    original_note_action: str

    # Validated values
    validated_note_cible: str | None
    note_action: str
    suggested_section: str | None = None

    # Flags
    is_duplicate: bool = False
    duplicate_reason: str | None = None
    confidence: float = 0.9

    # Changes made
    changes: list[str] = field(default_factory=list)

    # Original extraction data (preserved)
    info: str = ""
    type: str = ""
    importance: str = ""
    omnifocus: bool = False
    calendar: bool = False
    date: str | None = None
    time: str | None = None


@dataclass
class CoherenceWarning:
    """A warning about a potential issue."""

    type: str  # "potential_duplicate", "ambiguous_target", "missing_note", "low_confidence"
    extraction_index: int
    message: str


@dataclass
class CoherenceSummary:
    """Summary of coherence validation."""

    total_extractions: int = 0
    validated_unchanged: int = 0
    corrected: int = 0
    duplicates_detected: int = 0
    creations_blocked: int = 0


@dataclass
class CoherenceResult:
    """Result of extraction coherence validation (Mode 1)."""

    validated_extractions: list[ValidatedExtraction]
    warnings: list[CoherenceWarning]
    coherence_summary: CoherenceSummary
    coherence_confidence: float
    reasoning: str

    # Metadata
    duration_ms: float = 0
    model_used: str = "haiku"
    tokens_used: int = 0


# =============================================================================
# FUTURE MODE STRUCTURES (Note Maintenance)
# =============================================================================


@dataclass
class NoteDuplicateCandidate:
    """A potential duplicate found across notes (Mode 2/3)."""

    note_a_title: str
    note_a_excerpt: str
    note_b_title: str
    note_b_excerpt: str
    similarity_score: float
    duplicate_type: str  # "exact", "paraphrase", "overlapping"
    suggested_action: str  # "merge_into_a", "merge_into_b", "keep_both", "review"


@dataclass
class NoteRefactorSuggestion:
    """A suggestion to refactor a note (Mode 2)."""

    note_title: str
    suggestion_type: str  # "split", "merge", "reorganize", "archive"
    reason: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)
    # For split: {"proposed_notes": ["Note A", "Note B"]}
    # For merge: {"merge_into": "Target Note"}
    # For reorganize: {"new_sections": ["## Section 1", "## Section 2"]}


@dataclass
class NoteHealthReport:
    """Health report for a single note (Mode 2)."""

    note_title: str
    note_path: str

    # Metrics
    content_length: int
    section_count: int
    entry_count: int
    last_modified: datetime | None

    # Issues found
    internal_duplicates: list[str]  # Duplicate entries within the note
    orphan_sections: list[str]  # Empty or near-empty sections
    missing_links: list[str]  # Referenced notes that don't exist
    broken_structure: list[str]  # Structural issues (nested headers, etc.)

    # Related notes
    related_notes: list[str]
    potential_merges: list[str]

    # Overall health score (0-1)
    health_score: float
    recommendations: list[NoteRefactorSuggestion]


@dataclass
class BatchCoherenceResult:
    """Result of batch coherence analysis (Mode 3)."""

    notes_analyzed: int
    duplicates_found: list[NoteDuplicateCandidate]
    refactor_suggestions: list[NoteRefactorSuggestion]
    global_health_score: float
    duration_ms: float
    reasoning: str


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================


class CoherenceService:
    """
    Coherence Service — Validates and maintains coherence across PKM notes.

    This service provides three modes of operation:

    1. EXTRACTION MODE (`validate_extractions`):
       - Called during email analysis (MultiPassAnalyzer)
       - Validates proposed extractions against existing notes
       - Ensures enrichir > creer preference
       - Detects duplicates before writing

    2. NOTE MAINTENANCE MODE (`analyze_note`, `analyze_note_health`) [FUTURE]:
       - Called by background maintenance worker
       - Analyzes individual notes for internal coherence
       - Finds related notes and suggests consolidation
       - Detects orphan sections, broken links, duplicates

    3. BATCH ANALYSIS MODE (`analyze_batch`) [FUTURE]:
       - Called on-demand or by scheduler
       - Analyzes multiple notes together
       - Detects cross-note duplicates
       - Suggests global refactoring

    Usage:
        # Mode 1: During email processing
        service = CoherenceService(note_manager, ai_router)
        result = await service.validate_extractions(extractions, event)

        # Mode 2: Background maintenance (future)
        health = await service.analyze_note_health("Nautil 6")

        # Mode 3: Batch analysis (future)
        batch_result = await service.analyze_batch(["Note A", "Note B", "Note C"])
    """

    def __init__(
        self,
        note_manager: "NoteManager",
        ai_router: "AIRouter",
        entity_searcher: "EntitySearcher | None" = None,
        template_renderer: TemplateRenderer | None = None,
    ):
        """
        Initialize the coherence validator.

        Args:
            note_manager: NoteManager for accessing notes
            ai_router: AIRouter for AI calls
            entity_searcher: EntitySearcher for finding similar notes
            template_renderer: TemplateRenderer for prompts
        """
        self._note_manager = note_manager
        self._ai_router = ai_router
        self._entity_searcher = entity_searcher
        self._template_renderer = template_renderer or TemplateRenderer()

    # =========================================================================
    # MODE 1: EXTRACTION VALIDATION (during email analysis)
    # =========================================================================

    async def validate_extractions(
        self,
        extractions: list[Extraction],
        event: "PerceivedEvent | None" = None,
    ) -> CoherenceResult:
        """
        Validate proposed extractions against existing notes.

        This is the primary method called during email analysis.
        It ensures that extractions target the right notes and don't
        create duplicates.

        Args:
            extractions: List of extractions to validate
            event: The original event being processed (optional, for context)

        Returns:
            CoherenceResult with validated extractions and warnings

        Example:
            result = await service.validate_extractions(extractions, event)
            for ext in result.validated_extractions:
                if not ext.is_duplicate:
                    await note_manager.enrich(ext.validated_note_cible, ext.info)
        """
        start_time = datetime.now()

        # Skip if no extractions
        if not extractions:
            return CoherenceResult(
                validated_extractions=[],
                warnings=[],
                coherence_summary=CoherenceSummary(),
                coherence_confidence=1.0,
                reasoning="No extractions to validate",
            )

        # 1. Gather unique note targets
        unique_targets = set()
        for ext in extractions:
            if ext.note_cible:
                unique_targets.add(ext.note_cible)

        logger.info(
            "Validating %d extractions with %d unique targets",
            len(extractions),
            len(unique_targets),
        )

        # 2. Load full content of target notes
        target_notes = self._load_target_notes(unique_targets)

        # 3. Find similar notes (alternatives) - includes PROJECT-FIRST search
        similar_notes = self._find_similar_notes(unique_targets, event)

        # 4. Get index of existing notes
        existing_notes = self._get_existing_notes_index()

        # 5. Render prompt and call AI
        prompt = self._render_prompt(
            extractions=extractions,
            event=event,
            target_notes=target_notes,
            similar_notes=similar_notes,
            existing_notes=existing_notes,
        )

        # 6. Call AI for validation
        response_text, usage = await self._ai_router.analyze_with_prompt_async(
            prompt=prompt,
            model=AIModel.CLAUDE_HAIKU,
            max_tokens=2000,
        )

        # 7. Parse JSON response
        try:
            response_data = json.loads(self._extract_json(response_text))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse coherence response: {e}")
            # Return extractions unchanged if parsing fails
            return self._fallback_result(extractions, str(e))

        # 8. Parse response
        result = self._parse_response(response_data, extractions)
        result.tokens_used = usage.get("total_tokens", 0)

        # Add metadata
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        result.duration_ms = duration_ms
        result.model_used = "haiku"

        logger.info(
            "Coherence validation completed in %.2fms: %d corrected, %d duplicates",
            duration_ms,
            result.coherence_summary.corrected,
            result.coherence_summary.duplicates_detected,
        )

        return result

    def _load_target_notes(self, targets: set[str]) -> list[FullNoteContext]:
        """Load full content of target notes."""
        target_notes = []

        for target in targets:
            # Try exact match first
            note = self._note_manager.get_note_by_title(target)
            if note:
                content = note.content or ""
                target_notes.append(FullNoteContext.from_note(note, content))
            else:
                # Try fuzzy match
                if self._entity_searcher:
                    results = self._entity_searcher.search_entities([target])
                    for result in results[:1]:  # Take best match
                        content = result.note.content or ""
                        target_notes.append(FullNoteContext.from_note(result.note, content))

        return target_notes

    def _find_similar_notes(
        self, targets: set[str], event: "PerceivedEvent | None" = None
    ) -> list[SimilarNote]:
        """Find similar notes that could be alternatives.

        Also proactively searches for PROJECT notes based on email content
        to support Project-First prioritization.
        """
        similar_notes = []
        seen_titles: set[str] = set()

        # 1. Search based on extraction targets (only if entity_searcher available)
        if self._entity_searcher:
            for target in targets:
                results = self._entity_searcher.search_entities([target])
                for result in results[:3]:  # Top 3 matches per target
                    # Skip exact matches (already in target_notes)
                    if result.match_type == "exact":
                        continue

                    if result.note.title in seen_titles:
                        continue
                    seen_titles.add(result.note.title)

                    content = result.note.content or ""
                    sections = FullNoteContext._extract_sections(content)

                    similar_notes.append(
                        SimilarNote(
                            title=result.note.title,
                            match_score=result.match_score,
                            match_type=result.match_type,
                            sections=sections,
                            snippet=content[:200] if content else "",
                        )
                    )

        # 2. PROJECT-FIRST: Proactively search for project notes based on email content
        # This runs regardless of entity_searcher availability
        if event:
            project_notes = self._find_project_notes_for_event(event, seen_titles)
            similar_notes.extend(project_notes)

        return similar_notes

    def _find_project_notes_for_event(
        self, event: "PerceivedEvent", seen_titles: set[str]
    ) -> list[SimilarNote]:
        """Find PROJECT notes that might be related to this email.

        Searches for notes starting with "Projet" that contain keywords
        from the email content (locations, topics, parties).
        """
        import unicodedata

        def normalize(text: str) -> str:
            """Normalize text: lowercase and remove accents."""
            text = text.lower()
            # NFD decomposition separates accents from base characters
            # Then filter out combining characters (accents)
            return "".join(
                c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
            )

        project_notes = []

        # Get all project notes
        all_notes = self._note_manager.get_all_notes()
        projet_notes = [n for n in all_notes if n.title.lower().startswith("projet")]

        logger.info(f"PROJECT-FIRST: Found {len(projet_notes)} project notes")

        if not projet_notes:
            return project_notes

        # Extract keywords from email - include both title and content
        title = getattr(event, "title", "") or ""
        content = getattr(event, "content", "") or ""
        full_text = normalize(f"{title} {content}")

        logger.debug(f"PROJECT-FIRST: Email title={title[:100]}, content length={len(content)}")

        # Keywords that suggest specific project contexts
        # Real estate keywords (already normalized - no accents)
        immo_keywords = [
            "immobilier",
            "villa",
            "maison",
            "appartement",
            "terrain",
            "achat",
            "vente",
            "offre",
            "acquisition",
            "propriete",
            "maurice",
            "mauritius",
            "azuri",
            "valriche",
            "anahita",
            "ocean river",
            "bluelife",
            "esperance",
            "lagesse",
            "piscine",
            "location",
            "loyer",
            "bail",
        ]

        for note in projet_notes:
            if note.title in seen_titles:
                continue

            note_content = normalize(note.content or "")
            note_title_norm = normalize(note.title)

            # Check if project note is related to email content
            match_score = 0.0
            matching_keywords = []

            for keyword in immo_keywords:
                # Keyword in both email and project note
                if keyword in full_text and (keyword in note_content or keyword in note_title_norm):
                    match_score += 0.15
                    matching_keywords.append(keyword)

            logger.debug(
                f"PROJECT-FIRST: Note '{note.title}' - "
                f"score={match_score:.2f}, keywords={matching_keywords}"
            )

            # If we have a significant match, add as similar note
            if match_score >= 0.3 and matching_keywords:
                seen_titles.add(note.title)
                raw_content = note.content or ""
                sections = FullNoteContext._extract_sections(raw_content)

                logger.info(
                    f"PROJECT-FIRST: Matched '{note.title}' "
                    f"(score={match_score:.2f}, keywords={matching_keywords})"
                )

                project_notes.append(
                    SimilarNote(
                        title=note.title,
                        match_score=min(match_score, 0.95),
                        match_type="keyword",
                        sections=sections,
                        snippet=raw_content[:200] if raw_content else "",
                    )
                )

        return project_notes

    def _get_existing_notes_index(self) -> list[str]:
        """Get list of all existing note titles."""
        notes = self._note_manager.get_all_notes()
        return [note.title for note in notes]

    def _render_prompt(
        self,
        extractions: list[Extraction],
        event: "PerceivedEvent",
        target_notes: list[FullNoteContext],
        similar_notes: list[SimilarNote],
        existing_notes: list[str],
    ) -> str:
        """Render the coherence validation prompt."""
        return self._template_renderer.render(
            "pass_coherence.j2",
            extractions=extractions,
            event=event,
            target_notes=target_notes,
            similar_notes=similar_notes,
            existing_notes=existing_notes,
        )

    def _parse_response(
        self, response: dict[str, Any], original_extractions: list[Extraction]
    ) -> CoherenceResult:
        """Parse AI response into CoherenceResult."""
        validated = []
        warnings = []

        # Parse validated extractions
        for i, ext_data in enumerate(response.get("validated_extractions", [])):
            original = original_extractions[i] if i < len(original_extractions) else None

            validated.append(
                ValidatedExtraction(
                    original_note_cible=ext_data.get("original_note_cible"),
                    original_note_action=original.note_action if original else "enrichir",
                    validated_note_cible=ext_data.get("validated_note_cible"),
                    note_action=ext_data.get("note_action", "enrichir"),
                    suggested_section=ext_data.get("suggested_section"),
                    is_duplicate=ext_data.get("is_duplicate", False),
                    duplicate_reason=ext_data.get("duplicate_reason"),
                    confidence=ext_data.get("confidence", 0.9),
                    changes=ext_data.get("changes", []),
                    info=ext_data.get("info", original.info if original else ""),
                    type=ext_data.get("type", original.type if original else ""),
                    importance=ext_data.get("importance", original.importance if original else ""),
                    omnifocus=ext_data.get("omnifocus", original.omnifocus if original else False),
                    calendar=ext_data.get("calendar", original.calendar if original else False),
                    date=ext_data.get("date", original.date if original else None),
                    time=ext_data.get("time", original.time if original else None),
                )
            )

        # Parse warnings
        for warn_data in response.get("warnings", []):
            warnings.append(
                CoherenceWarning(
                    type=warn_data.get("type", "unknown"),
                    extraction_index=warn_data.get("extraction_index", 0),
                    message=warn_data.get("message", ""),
                )
            )

        # Parse summary
        summary_data = response.get("coherence_summary", {})
        summary = CoherenceSummary(
            total_extractions=summary_data.get("total_extractions", len(original_extractions)),
            validated_unchanged=summary_data.get("validated_unchanged", 0),
            corrected=summary_data.get("corrected", 0),
            duplicates_detected=summary_data.get("duplicates_detected", 0),
            creations_blocked=summary_data.get("creations_blocked", 0),
        )

        return CoherenceResult(
            validated_extractions=validated,
            warnings=warnings,
            coherence_summary=summary,
            coherence_confidence=response.get("coherence_confidence", 0.9),
            reasoning=response.get("reasoning", ""),
        )

    def suggest_section(self, extraction_type: str, note_sections: list[str]) -> str | None:
        """Suggest the best section for an extraction type."""
        suggestions = SECTION_SUGGESTIONS.get(extraction_type, [])

        for suggestion in suggestions:
            for section in note_sections:
                if suggestion.lower() in section.lower():
                    return section

        return None

    def _extract_json(self, response: str) -> str:
        """
        Extract JSON object from response text.

        Uses multiple strategies to find valid JSON:
        1. Look for ```json code blocks
        2. Look for ``` code blocks
        3. Find first { and last }

        Args:
            response: Raw response text

        Returns:
            Extracted JSON string

        Raises:
            ValueError: If no valid JSON found
        """
        if not response or not response.strip():
            raise ValueError("Empty response from AI")

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                extracted = response[start:end].strip()
                if extracted:
                    return extracted

        if "```" in response:
            start = response.find("```") + 3
            newline_pos = response.find("\n", start)
            if newline_pos != -1 and newline_pos < start + 20:
                start = newline_pos + 1
            end = response.find("```", start)
            if end > start:
                extracted = response[start:end].strip()
                if extracted and "{" in extracted:
                    return extracted

        # Find first { and last }
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start == -1 or json_end <= json_start:
            raise ValueError(f"No JSON object found in response: {response[:100]}")

        return response[json_start:json_end]

    def _fallback_result(self, extractions: list[Extraction], error_reason: str) -> CoherenceResult:
        """
        Create a fallback result when coherence validation fails.

        Returns extractions unchanged with a warning.

        Args:
            extractions: Original extractions to preserve
            error_reason: Why the validation failed

        Returns:
            CoherenceResult with unchanged extractions
        """
        validated = []
        for ext in extractions:
            validated.append(
                ValidatedExtraction(
                    original_note_cible=ext.note_cible,
                    original_note_action=ext.note_action,
                    validated_note_cible=ext.note_cible,
                    note_action=ext.note_action,
                    confidence=0.7,  # Lower confidence since validation failed
                    changes=[],
                    info=ext.info,
                    type=ext.type,
                    importance=ext.importance,
                    omnifocus=ext.omnifocus,
                    calendar=ext.calendar,
                    date=ext.date,
                    time=ext.time,
                )
            )

        return CoherenceResult(
            validated_extractions=validated,
            warnings=[
                CoherenceWarning(
                    type="validation_error",
                    extraction_index=-1,
                    message=f"Coherence validation failed: {error_reason}. Extractions returned unchanged.",
                )
            ],
            coherence_summary=CoherenceSummary(
                total_extractions=len(extractions),
                validated_unchanged=len(extractions),
            ),
            coherence_confidence=0.7,
            reasoning=f"Validation failed due to: {error_reason}. Extractions preserved unchanged.",
        )

    # =========================================================================
    # MODE 2: NOTE MAINTENANCE (background service - FUTURE)
    # =========================================================================

    async def analyze_note_health(self, note_title: str) -> NoteHealthReport:
        """
        Analyze the health of a single note.

        This method will be called by the background maintenance worker
        to check individual notes for:
        - Internal duplicates
        - Orphan/empty sections
        - Missing linked notes
        - Structural issues
        - Related notes that could be merged

        Args:
            note_title: Title of the note to analyze

        Returns:
            NoteHealthReport with metrics and recommendations

        Note:
            This is a STUB for future implementation.
        """
        raise NotImplementedError(
            "Note health analysis is planned for future implementation. "
            "See COHERENCE_PASS_SPEC.md for design details."
        )

    async def find_related_notes(self, note_title: str) -> list[SimilarNote]:
        """
        Find notes related to the given note.

        Searches for notes that:
        - Share entities (people, projects, companies)
        - Have overlapping content
        - Link to each other via wikilinks

        Args:
            note_title: Title of the note to find relations for

        Returns:
            List of related notes with similarity scores

        Note:
            This is a STUB for future implementation.
        """
        raise NotImplementedError("Related notes search is planned for future implementation.")

    async def suggest_note_refactoring(self, note_title: str) -> list[NoteRefactorSuggestion]:
        """
        Suggest refactoring actions for a note.

        Analyzes the note and suggests:
        - Split if too long or covers multiple topics
        - Merge if very short or overlaps with another note
        - Reorganize if sections are disorganized
        - Archive if content is obsolete

        Args:
            note_title: Title of the note to analyze

        Returns:
            List of suggested refactoring actions

        Note:
            This is a STUB for future implementation.
        """
        raise NotImplementedError(
            "Note refactoring suggestions are planned for future implementation."
        )

    # =========================================================================
    # MODE 3: BATCH ANALYSIS (on-demand - FUTURE)
    # =========================================================================

    async def analyze_batch(
        self,
        note_titles: list[str] | None = None,
        analyze_all: bool = False,
    ) -> BatchCoherenceResult:
        """
        Analyze multiple notes for cross-note coherence.

        This method can be used to:
        - Analyze a specific set of notes
        - Analyze all notes in the PKM (if analyze_all=True)

        It detects:
        - Cross-note duplicates
        - Notes that should be merged
        - Global reorganization opportunities

        Args:
            note_titles: List of note titles to analyze (optional)
            analyze_all: If True, analyze all notes in PKM

        Returns:
            BatchCoherenceResult with findings and suggestions

        Note:
            This is a STUB for future implementation.
        """
        raise NotImplementedError(
            "Batch coherence analysis is planned for future implementation. "
            "See COHERENCE_PASS_SPEC.md for design details."
        )

    async def find_duplicates_across_notes(
        self,
        note_titles: list[str] | None = None,
    ) -> list[NoteDuplicateCandidate]:
        """
        Find duplicate content across multiple notes.

        Compares notes pairwise to find:
        - Exact duplicates (same text)
        - Paraphrased duplicates (same info, different words)
        - Overlapping content (partial duplication)

        Args:
            note_titles: List of note titles to compare (default: all notes)

        Returns:
            List of duplicate candidates with suggested actions

        Note:
            This is a STUB for future implementation.
        """
        raise NotImplementedError(
            "Cross-note duplicate detection is planned for future implementation."
        )


# =============================================================================
# CONVENIENCE ALIAS
# =============================================================================

# Alias for backward compatibility and shorter imports
CoherenceValidator = CoherenceService
