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
from typing import Any, Optional

from src.monitoring.logger import get_logger
from src.passepartout.note_manager import Note
from src.passepartout.note_metadata import NoteMetadata
from src.passepartout.note_types import NoteType

logger = get_logger("passepartout.note_enricher")

# Confidence thresholds for different enrichment types
CONFIDENCE_ENTITY_REFERENCE = 0.6  # Entity found in note content
CONFIDENCE_EXISTING_SECTION = 0.65  # Update to existing section
CONFIDENCE_NEW_SECTION = 0.7  # Suggestion for new section

# Timeout configuration for async operations (seconds)
DEFAULT_AI_TIMEOUT = 30.0  # Timeout for AI gap analysis
DEFAULT_WEB_TIMEOUT = 15.0  # Timeout for web research

# Pre-compiled regex for date extraction (ISO format: YYYY-MM-DD)
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")

# Pre-compiled regex for section header detection (markdown headers)
SECTION_HEADER_PATTERN = re.compile(r"^(#+)\s+(.*)$")


class EnrichmentSource(str, Enum):
    """Sources of enrichment"""

    AI_ANALYSIS = "ai_analysis"  # From AI model analysis
    CROSS_REFERENCE = "cross_reference"  # From linked notes
    EMAIL_CONTEXT = "email_context"  # From email content
    WEB_SEARCH = "web_search"  # From web search


@dataclass
class Enrichment:
    """A single enrichment suggestion. Uses slots=True for memory efficiency."""

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
    """Context for enrichment analysis. Uses slots=True for memory efficiency."""

    note: Note
    metadata: NoteMetadata
    linked_notes: list[Note] = field(default_factory=list)
    recent_emails: list[dict[str, Any]] = field(default_factory=list)
    related_entities: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EnrichmentResult:
    """Result of enrichment analysis. Uses slots=True for memory efficiency."""

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
        ai_router: Optional[Any] = None,
        web_search_enabled: bool = False,
        ai_timeout: float = DEFAULT_AI_TIMEOUT,
        web_timeout: float = DEFAULT_WEB_TIMEOUT,
    ):
        """
        Initialize enricher

        Args:
            ai_router: Optional AI router (Sancho) for analysis
            web_search_enabled: Global flag for web search
            ai_timeout: Timeout for AI gap analysis in seconds
            web_timeout: Timeout for web research in seconds
        """
        self.ai_router = ai_router
        self.web_search_enabled = web_search_enabled
        self.ai_timeout = ai_timeout
        self.web_timeout = web_timeout

    async def enrich(
        self,
        note: Note,
        metadata: NoteMetadata,
        context: Optional[EnrichmentContext] = None,
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

        # 1. Rule-based gap analysis (always runs)
        try:
            rule_enrichments = await self._rule_based_gap_analysis(context)
            enrichments.extend(rule_enrichments)
            if rule_enrichments:
                sources_used.append(EnrichmentSource.AI_ANALYSIS)
        except Exception as e:
            logger.warning("Rule-based gap analysis failed", extra={"error": str(e)})

        # 1b. AI-enhanced gap analysis (if available, with timeout)
        if self.ai_router and metadata.auto_enrich:
            try:
                ai_enrichments = await asyncio.wait_for(
                    self._ai_gap_analysis(context), timeout=self.ai_timeout
                )
                enrichments.extend(ai_enrichments)
                if ai_enrichments and EnrichmentSource.AI_ANALYSIS not in sources_used:
                    sources_used.append(EnrichmentSource.AI_ANALYSIS)
            except asyncio.TimeoutError:
                logger.warning(
                    "AI gap analysis timed out",
                    extra={"note_id": note.note_id, "timeout": self.ai_timeout},
                )
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

        # 4. Web search (if enabled via constructor, with timeout)
        if self.web_search_enabled:
            try:
                web_enrichments = await asyncio.wait_for(
                    self._web_research(context), timeout=self.web_timeout
                )
                enrichments.extend(web_enrichments)
                if web_enrichments:
                    sources_used.append(EnrichmentSource.WEB_SEARCH)
            except asyncio.TimeoutError:
                logger.warning(
                    "Web research timed out",
                    extra={"note_id": note.note_id, "timeout": self.web_timeout},
                )
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

        logger.info("Enrichment complete", extra={"note_id": note.note_id, "summary": summary})

        return EnrichmentResult(
            note_id=note.note_id,
            enrichments=enrichments,
            gaps_identified=gaps,
            sources_used=sources_used,
            analysis_summary=summary,
        )

    async def _rule_based_gap_analysis(
        self,
        context: EnrichmentContext,
    ) -> list[Enrichment]:
        """
        Rule-based gap analysis without AI.
        Detects missing sections and suggests improvements based on note type.
        """
        enrichments = []
        note = context.note
        metadata = context.metadata
        content = note.content
        content_lower = content.lower()

        # 1. Check for empty or minimal sections
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

        # 2. Suggest missing sections based on note type
        type_sections = self._get_required_sections_for_type(metadata.note_type)
        existing_sections_lower = {s.lower() for s in sections}

        for required, description in type_sections:
            if required.lower() not in existing_sections_lower and required.lower() not in content_lower:
                enrichments.append(
                    Enrichment(
                        source=EnrichmentSource.AI_ANALYSIS,
                        section=required,
                        content=f"## {required}\n\n[À compléter]",
                        confidence=CONFIDENCE_NEW_SECTION,
                        reasoning=f"Section recommandée pour une note de type "
                        f"{metadata.note_type.value}: {description}",
                    )
                )

        # 3. Check note length - very short notes need content
        if len(content.strip()) < 100:
            enrichments.append(
                Enrichment(
                    source=EnrichmentSource.AI_ANALYSIS,
                    section="Contenu",
                    content="[Note trop courte - enrichir le contenu principal]",
                    confidence=CONFIDENCE_NEW_SECTION,
                    reasoning="La note contient très peu de contenu",
                )
            )

        # 4. Check for outdated content markers
        outdated_markers = ["à mettre à jour", "obsolète", "ancien", "TODO", "FIXME"]
        for marker in outdated_markers:
            if marker.lower() in content_lower:
                enrichments.append(
                    Enrichment(
                        source=EnrichmentSource.AI_ANALYSIS,
                        section="Mise à jour",
                        content="[Contenu potentiellement obsolète détecté]",
                        confidence=CONFIDENCE_EXISTING_SECTION,
                        reasoning=f"Marqueur '{marker}' trouvé dans le contenu",
                    )
                )
                break  # Only one warning

        return enrichments

    def _get_required_sections_for_type(
        self, note_type: NoteType
    ) -> list[tuple[str, str]]:
        """Return required sections for a note type."""
        sections_by_type = {
            NoteType.PERSONNE: [
                ("Contact", "Coordonnées et moyens de contact"),
                ("Rôle", "Fonction et responsabilités"),
                ("Contexte", "Comment vous vous êtes rencontrés"),
                ("Notes", "Observations et points importants"),
            ],
            NoteType.PROJET: [
                ("Objectifs", "But et résultats attendus"),
                ("Statut", "État actuel du projet"),
                ("Prochaines étapes", "Actions à venir"),
                ("Parties prenantes", "Personnes impliquées"),
            ],
            NoteType.ENTITE: [
                ("Description", "Présentation de l'organisation"),
                ("Contacts", "Personnes clés"),
                ("Historique", "Interactions passées"),
            ],
            NoteType.REUNION: [
                ("Participants", "Liste des participants"),
                ("Ordre du jour", "Sujets abordés"),
                ("Décisions", "Décisions prises"),
                ("Actions", "Prochaines étapes"),
            ],
            NoteType.PROCESSUS: [
                ("Étapes", "Description des étapes du processus"),
                ("Prérequis", "Conditions nécessaires"),
                ("Ressources", "Outils et documents utiles"),
            ],
            NoteType.EVENEMENT: [
                ("Date", "Date et heure de l'événement"),
                ("Lieu", "Localisation"),
                ("Participants", "Personnes présentes"),
                ("Notes", "Points importants"),
            ],
            NoteType.CONCEPT: [
                ("Définition", "Explication claire du concept"),
                ("Principes clés", "Idées fondamentales à retenir"),
                ("Exemples", "Illustrations concrètes"),
                ("Applications", "Quand et comment utiliser"),
                ("Sources", "Références et liens utiles"),
            ],
        }
        return sections_by_type.get(note_type, [])

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
        context: EnrichmentContext,
    ) -> list[Enrichment]:
        """Search web for relevant information using Tavily or DuckDuckGo."""
        from src.passepartout.cross_source.adapters.web_adapter import create_web_adapter

        enrichments = []
        note = context.note

        # Create web adapter (Tavily if available, else DuckDuckGo)
        adapter = create_web_adapter()
        if not adapter.is_available:
            logger.warning("No web adapter available for enrichment")
            return []

        # Build search query from note title and key entities
        query = note.title
        if context.metadata.note_type == NoteType.PERSONNE:
            query = f"{note.title} personne profil"
        elif context.metadata.note_type == NoteType.ENTITE:
            query = f"{note.title} entreprise organisation"
        elif context.metadata.note_type == NoteType.PROJET:
            query = f"{note.title} projet"

        logger.info(
            "Running web search for enrichment",
            extra={"note_id": note.note_id, "query": query},
        )

        # Search the web
        results = await adapter.search(query, max_results=5)

        if not results:
            logger.info("No web results found", extra={"note_id": note.note_id})
            return []

        # Convert results to enrichments
        for result in results:
            # Skip low relevance results
            if result.relevance_score < 0.5:
                continue

            enrichments.append(
                Enrichment(
                    source=EnrichmentSource.WEB_SEARCH,
                    section="Recherche Web",
                    content=f"**{result.title}**\n\n{result.content[:500]}",
                    confidence=min(result.relevance_score, CONFIDENCE_NEW_SECTION),
                    reasoning=f"Résultat web pertinent (score: {result.relevance_score:.2f})",
                    metadata={
                        "url": result.url,
                        "domain": result.metadata.get("domain", ""),
                    },
                )
            )

        logger.info(
            "Web search enrichment complete",
            extra={"note_id": note.note_id, "results": len(enrichments)},
        )

        return enrichments

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
                    datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc) for d in dates
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
                logger.warning("Enrichment task failed", extra={"error": str(task_result)})
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
