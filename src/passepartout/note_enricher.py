"""
Note Enricher

Enriches notes using AI analysis and optional web search.
Generates enrichment suggestions with confidence scores.
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.monitoring.logger import get_logger
from src.passepartout.note_manager import Note
from src.passepartout.note_metadata import NoteMetadata
from src.passepartout.note_types import NoteType

logger = get_logger("passepartout.note_enricher")

# Confidence thresholds for different enrichment types
CONFIDENCE_ENTITY_REFERENCE = 0.6  # Entity found in note content
CONFIDENCE_EXISTING_SECTION = 0.65  # Update to existing section
CONFIDENCE_NEW_SECTION = 0.7  # Suggestion for new section

# Pre-compiled regex for date extraction (ISO format: YYYY-MM-DD)
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")

# Pre-compiled regex for section header detection (markdown headers)
SECTION_HEADER_PATTERN = re.compile(r'^(#+)\s+(.*)$')


class EnrichmentSource(str, Enum):
    """Sources of enrichment"""

    AI_ANALYSIS = "ai_analysis"  # From AI model analysis
    CROSS_REFERENCE = "cross_reference"  # From linked notes
    EMAIL_CONTEXT = "email_context"  # From email content
    WEB_SEARCH = "web_search"  # From web search


@dataclass
class Enrichment:
    """A single enrichment suggestion"""

    source: EnrichmentSource
    section: str  # Target section in note
    content: str  # Content to add/update
    confidence: float  # 0.0 - 1.0
    reasoning: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.source.value}] {self.section}: {self.content[:50]}... (conf={self.confidence:.2f})"


@dataclass
class EnrichmentContext:
    """Context for enrichment analysis"""

    note: Note
    metadata: NoteMetadata
    linked_notes: list[Note] = field(default_factory=list)
    recent_emails: list[dict[str, Any]] = field(default_factory=list)
    related_entities: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EnrichmentResult:
    """Result of enrichment analysis"""

    note_id: str
    enrichments: list[Enrichment]
    gaps_identified: list[str]  # Missing information
    sources_used: list[EnrichmentSource]
    analysis_summary: str


class NoteEnricher:
    """
    Generates enrichment suggestions for notes

    Sources of enrichment:
    - AI analysis of content gaps
    - Cross-reference with linked notes
    - Email/message context extraction
    - Web search (when enabled)
    """

    def __init__(
        self,
        ai_router: Any | None = None,
        web_search_enabled: bool = False,
    ):
        """
        Initialize enricher

        Args:
            ai_router: Optional AI router (Sancho) for analysis
            web_search_enabled: Global flag for web search
        """
        self.ai_router = ai_router
        self.web_search_enabled = web_search_enabled

    async def enrich(
        self,
        note: Note,
        metadata: NoteMetadata,
        context: EnrichmentContext | None = None,
    ) -> EnrichmentResult:
        """
        Generate enrichments for a note

        Args:
            note: Note to enrich
            metadata: Note metadata
            context: Optional enrichment context

        Returns:
            EnrichmentResult with suggestions
        """
        logger.info("Generating enrichments for note", extra={"note_id": note.note_id})

        if context is None:
            context = EnrichmentContext(note=note, metadata=metadata)

        enrichments = []
        gaps = []
        sources_used = []

        # 1. AI-based gap analysis
        if self.ai_router and metadata.auto_enrich:
            try:
                ai_enrichments = await self._ai_gap_analysis(context)
                enrichments.extend(ai_enrichments)
                if ai_enrichments:
                    sources_used.append(EnrichmentSource.AI_ANALYSIS)
            except Exception as e:
                logger.warning("AI gap analysis failed", extra={"error": str(e)})

        # 2. Cross-reference analysis
        xref_enrichments = self._cross_reference_analysis(context)
        enrichments.extend(xref_enrichments)
        if xref_enrichments:
            sources_used.append(EnrichmentSource.CROSS_REFERENCE)

        # 3. Email context extraction (for Person notes)
        if metadata.note_type == NoteType.PERSONNE:
            email_enrichments = self._extract_from_emails(context)
            enrichments.extend(email_enrichments)
            if email_enrichments:
                sources_used.append(EnrichmentSource.EMAIL_CONTEXT)

        # 4. Web search (if enabled for this note)
        if self.web_search_enabled and metadata.web_search_enabled:
            try:
                web_enrichments = await self._web_research(context)
                enrichments.extend(web_enrichments)
                if web_enrichments:
                    sources_used.append(EnrichmentSource.WEB_SEARCH)
            except Exception as e:
                logger.warning("Web research failed", extra={"error": str(e)})

        # Identify gaps based on note type
        gaps = self._identify_gaps(context)

        # Generate summary
        if enrichments:
            summary = (
                f"{len(enrichments)} enrichissements suggérés "
                f"(sources: {', '.join(s.value for s in sources_used)})"
            )
        else:
            summary = "Aucun enrichissement identifié"

        logger.info(
            "Enrichment complete",
            extra={"note_id": note.note_id, "summary": summary}
        )

        return EnrichmentResult(
            note_id=note.note_id,
            enrichments=enrichments,
            gaps_identified=gaps,
            sources_used=sources_used,
            analysis_summary=summary,
        )

    async def _ai_gap_analysis(
        self,
        context: EnrichmentContext,
    ) -> list[Enrichment]:
        """Use AI to identify content gaps and suggest enrichments"""
        # This will be implemented with Sancho integration
        # For now, return rule-based analysis

        enrichments = []
        note = context.note
        content = note.content

        # Check for empty or minimal sections
        sections = self._parse_sections(content)
        for section_name, section_content in sections.items():
            if len(section_content.strip()) < 20:
                enrichments.append(
                    Enrichment(
                        source=EnrichmentSource.AI_ANALYSIS,
                        section=section_name,
                        content="[Section nécessite plus de contenu]",
                        confidence=CONFIDENCE_ENTITY_REFERENCE,
                        reasoning=f"La section '{section_name}' semble incomplète",
                    )
                )

        return enrichments

    def _cross_reference_analysis(
        self,
        context: EnrichmentContext,
    ) -> list[Enrichment]:
        """Analyze linked notes for potential enrichments"""
        enrichments = []
        note = context.note

        for linked_note in context.linked_notes:
            # Look for information in linked note that might be relevant
            relevant_info = self._extract_relevant_info(note, linked_note)
            for info in relevant_info:
                enrichments.append(
                    Enrichment(
                        source=EnrichmentSource.CROSS_REFERENCE,
                        section=info["section"],
                        content=info["content"],
                        confidence=info["confidence"],
                        reasoning=f"Information trouvée dans [[{linked_note.title}]]",
                        metadata={"source_note": linked_note.note_id},
                    )
                )

        return enrichments

    def _extract_from_emails(
        self,
        context: EnrichmentContext,
    ) -> list[Enrichment]:
        """Extract relevant information from recent emails"""
        enrichments = []

        for email in context.recent_emails:
            # Look for updates about the person/entity
            updates = self._extract_email_updates(context.note, email)
            for update in updates:
                enrichments.append(
                    Enrichment(
                        source=EnrichmentSource.EMAIL_CONTEXT,
                        section=update["section"],
                        content=update["content"],
                        confidence=update["confidence"],
                        reasoning=f"Information extraite de l'email: {email.get('subject', 'N/A')}",
                        metadata={"email_id": email.get("id")},
                    )
                )

        return enrichments

    async def _web_research(
        self,
        _context: EnrichmentContext,
    ) -> list[Enrichment]:
        """Search web for relevant information"""
        # This will be implemented with web search integration
        # For now, return empty list
        return []

    def _identify_gaps(self, context: EnrichmentContext) -> list[str]:
        """Identify missing information based on note type"""
        gaps = []
        note = context.note
        metadata = context.metadata
        content = note.content.lower()

        # Type-specific gap detection
        if metadata.note_type == NoteType.PERSONNE:
            required_sections = [
                ("contact", "Informations de contact"),
                ("rôle", "Rôle / Fonction"),
                ("entreprise", "Entreprise / Organisation"),
            ]
            for keyword, description in required_sections:
                if keyword not in content:
                    gaps.append(f"Section manquante: {description}")

        elif metadata.note_type == NoteType.PROJET:
            required_sections = [
                ("objectif", "Objectifs du projet"),
                ("statut", "Statut actuel"),
                ("étape", "Prochaines étapes"),
            ]
            for keyword, description in required_sections:
                if keyword not in content:
                    gaps.append(f"Section manquante: {description}")

        elif metadata.note_type == NoteType.REUNION:
            required_sections = [
                ("participant", "Liste des participants"),
                ("décision", "Décisions prises"),
                ("action", "Actions à suivre"),
            ]
            for keyword, description in required_sections:
                if keyword not in content:
                    gaps.append(f"Section manquante: {description}")

        # Check for stale dates (use pre-compiled regex)
        dates = DATE_PATTERN.findall(content)
        if dates:
            try:
                latest_date = max(
                    datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    for d in dates
                )
                days_old = (datetime.now(timezone.utc) - latest_date).days
                if days_old > 90:
                    gaps.append(
                        f"Dates potentiellement obsolètes (dernière: {latest_date.strftime('%Y-%m-%d')})"
                    )
            except ValueError:
                pass

        return gaps

    def _parse_sections(self, content: str) -> dict[str, str]:
        """Parse markdown sections from content using pre-compiled regex"""
        sections = {}
        current_section = "Introduction"
        current_content: list[str] = []

        for line in content.split("\n"):
            match = SECTION_HEADER_PATTERN.match(line)
            if match:
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                # Start new section (extract title from regex group 2)
                current_section = match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _extract_relevant_info(
        self,
        target_note: Note,
        source_note: Note,
    ) -> list[dict[str, Any]]:
        """Extract information from source note relevant to target"""
        relevant = []

        # Look for mentions of target note's title in source
        target_title = target_note.title.lower()
        source_content = source_note.content

        # Find paragraphs mentioning the target
        paragraphs = source_content.split("\n\n")
        for para in paragraphs:
            if target_title in para.lower() and len(para) > 50:
                # This paragraph might contain relevant info
                relevant.append(
                        {
                            "section": "Contexte",
                            "content": f"Mentionné dans [[{source_note.title}]]: {para[:200]}...",
                            "confidence": CONFIDENCE_EXISTING_SECTION,
                        }
                    )

        return relevant[:3]  # Limit suggestions

    def _extract_email_updates(
        self,
        note: Note,
        email: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract updates from an email relevant to the note"""
        updates = []

        # This would typically use NLP to extract relevant information
        # For now, simple keyword matching

        note_title = note.title.lower()
        email_body = email.get("body", "").lower()

        if note_title in email_body:
            # Found mention of note subject
            updates.append(
                {
                    "section": "Dernières interactions",
                    "content": f"Email reçu le {email.get('date', 'N/A')}: {email.get('subject', 'Sans sujet')}",
                    "confidence": CONFIDENCE_NEW_SECTION,
                }
            )

        return updates


class EnrichmentPipeline:
    """
    Pipeline for processing multiple enrichments

    Manages the flow of enrichments through validation,
    prioritization, and application.
    """

    def __init__(self, enricher: NoteEnricher):
        self.enricher = enricher

    async def process_batch(
        self,
        notes: list[tuple[Note, NoteMetadata]],
        max_enrichments_per_note: int = 5,
        max_concurrent: int = 10,
    ) -> dict[str, EnrichmentResult]:
        """
        Process enrichments for a batch of notes in parallel

        Args:
            notes: List of (Note, NoteMetadata) tuples
            max_enrichments_per_note: Maximum enrichments to keep per note
            max_concurrent: Maximum concurrent enrichment tasks

        Returns:
            Dictionary mapping note_id to EnrichmentResult
        """
        results: dict[str, EnrichmentResult] = {}

        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_note(note: Note, metadata: NoteMetadata) -> tuple[str, EnrichmentResult]:
            async with semaphore:
                result = await self.enricher.enrich(note, metadata)

                # Filter and sort enrichments by confidence
                result.enrichments = sorted(
                    result.enrichments,
                    key=lambda e: e.confidence,
                    reverse=True,
                )[:max_enrichments_per_note]

                return note.note_id, result

        # Create tasks for all notes
        tasks = [enrich_note(note, metadata) for note, metadata in notes]

        # Execute all tasks in parallel with exception handling
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for task_result in task_results:
            if isinstance(task_result, Exception):
                logger.warning(
                    "Enrichment task failed",
                    extra={"error": str(task_result)}
                )
                continue
            note_id, enrichment_result = task_result
            results[note_id] = enrichment_result

        return results

    def filter_high_confidence(
        self,
        result: EnrichmentResult,
        threshold: float = 0.85,
    ) -> list[Enrichment]:
        """Filter enrichments above confidence threshold"""
        return [e for e in result.enrichments if e.confidence >= threshold]

    def filter_by_source(
        self,
        result: EnrichmentResult,
        sources: list[EnrichmentSource],
    ) -> list[Enrichment]:
        """Filter enrichments by source"""
        return [e for e in result.enrichments if e.source in sources]
