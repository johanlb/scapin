"""
Retouche Reviewer — Memory Cycles (v2)

AI-powered automatic note improvement system.
Implements the Retouche cycle: automated quality enhancement of notes.

Actions:
1. enrich — Add missing information
2. structure — Reorganize sections
3. summarize — Generate summary header
4. score — Calculate quality score (0-100)
5. inject_questions — Add questions for Johan
6. restructure_graph — Suggest splitting/merging (high confidence only)

Phase 1 of Retouche implementation uses AnalysisEngine for AI calls.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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
    CycleType,
)
from src.sancho.analysis_engine import (
    AICallError,
    AICallResult,
    AnalysisEngine,
    JSONParseError,
    ModelTier,
)
from src.sancho.template_renderer import get_template_renderer

if TYPE_CHECKING:
    from src.sancho.router import AIRouter

logger = get_logger("passepartout.retouche_reviewer")

# Maximum regex matches to process per pattern to prevent DoS on large documents
MAX_REGEX_MATCHES = 100


@dataclass
class HygieneMetrics:
    """Structural health metrics for a note (migré de NoteReviewer)"""

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


class RetoucheAction(str, Enum):
    """Types of Retouche actions"""

    ENRICH = "enrich"  # Enrichir contenu
    STRUCTURE = "structure"  # Réorganiser sections
    SUMMARIZE = "summarize"  # Générer résumé
    SCORE = "score"  # Évaluer qualité
    INJECT_QUESTIONS = "inject_questions"  # Ajouter questions pour Johan
    RESTRUCTURE_GRAPH = "restructure_graph"  # Scinder/fusionner (suggestion)
    # Phase 3: Actions avancées
    SUGGEST_LINKS = "suggest_links"  # Proposer des wikilinks [[Note]]
    CLEANUP = "cleanup"  # Supprimer contenu obsolète
    PROFILE_INSIGHT = "profile_insight"  # Ajouter analyse comportementale
    CREATE_OMNIFOCUS = "create_omnifocus"  # Créer tâche OmniFocus
    # Phase 4: Cycle de vie des notes (v3)
    FLAG_OBSOLETE = "flag_obsolete"  # Marquer note obsolète → Filage (toujours)
    MERGE_INTO = "merge_into"  # Fusionner dans une autre note → Auto/Filage
    MOVE_TO_FOLDER = "move_to_folder"  # Classer dans le bon dossier → Auto
    # Hygiene actions (migré de NoteReviewer)
    FORMAT = "format"  # Corrections formatage (espaces, headers)
    VALIDATE = "validate"  # Validation frontmatter
    FIX_LINKS = "fix_links"  # Corriger liens cassés


@dataclass
class RetoucheActionResult:
    """Result of a single Retouche action"""

    action_type: RetoucheAction
    target: str  # Section or content being targeted
    content: Optional[str] = None  # New/modified content
    confidence: float = 0.5  # 0.0 - 1.0
    reasoning: str = ""
    applied: bool = False
    model_used: str = "haiku"  # Which model performed this action
    # Pour MERGE_INTO: note cible
    target_note_id: Optional[str] = None
    target_note_title: Optional[str] = None
    # Pour actions en attente de confirmation (Filage)
    requires_confirmation: bool = False


@dataclass
class RetoucheResult:
    """Complete result of a Retouche cycle"""

    note_id: str
    success: bool
    quality_before: Optional[int]  # 0-100
    quality_after: int  # 0-100
    actions: list[RetoucheActionResult] = field(default_factory=list)
    questions_added: int = 0
    tasks_created: int = 0  # OmniFocus tasks created
    model_used: str = "haiku"  # Final model used
    escalated: bool = False  # Whether we escalated to a higher model
    reasoning: str = ""
    error: Optional[str] = None
    hygiene: Optional[HygieneMetrics] = None  # Métriques d'hygiène structurelle


@dataclass
class RetoucheContext:
    """Context collected for Retouche analysis"""

    note: Note
    metadata: NoteMetadata
    linked_notes: list[Note] = field(default_factory=list)
    linked_note_excerpts: dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    has_summary: bool = False
    section_count: int = 0
    question_count: int = 0


class RetoucheReviewer:
    """
    AI-powered automatic note improvement system.

    The Retouche cycle:
    1. Loads note + context (linked notes)
    2. Analyzes with Haiku (fast, cheap)
    3. Escalates to Sonnet if confidence < 0.7
    4. Escalates to Opus if confidence < 0.5
    5. Applies improvement actions
    6. Updates SM-2 retouche scheduling

    Uses AnalysisEngine for AI calls with automatic escalation and JSON parsing.
    """

    # Confidence thresholds for model escalation
    ESCALATE_TO_SONNET_THRESHOLD = 0.7
    ESCALATE_TO_OPUS_THRESHOLD = 0.5

    # Auto-apply thresholds
    AUTO_APPLY_THRESHOLD = 0.85
    RESTRUCTURE_THRESHOLD = 0.95  # Very high for destructive suggestions

    # System prompt (cacheable by Anthropic API)
    # This is the static part of the prompt, optimized for cache hits
    SYSTEM_PROMPT = """Tu es Scapin, l'assistant cognitif de Johan.

Mission : Améliorer la qualité des notes de sa base de connaissances personnelle.

## Règles absolues
1. JAMAIS inventer d'information - enrichir uniquement avec ce qui est implicite dans le contenu
2. Respecter le ton et style existant de Johan
3. Privilégier la concision
4. Confiance > 0.85 pour actions auto-applicables

## Actions disponibles

### Actions d'amélioration (auto si confiance >= 0.85)
- score : Évaluer qualité 0-100 (structure, complétude, liens)
- structure : Réorganiser les sections pour plus de clarté
- enrich : Compléter les informations manquantes mais implicites
- summarize : Générer un résumé en-tête (> **Résumé** : ...)
- inject_questions : Poser des questions stratégiques pour Johan
- suggest_links : Proposer des wikilinks [[Note]] pertinents
- cleanup : Identifier le contenu obsolète à supprimer

### Actions de cycle de vie

#### Critères de fragmentarité
Note **fragmentaire** = TOUTES ces conditions :
- Moins de 200 mots
- Moins de 2 sections (##)

#### Règle MERGE > DELETE
**IMPORTANT** : Pour une note fragmentaire :
1. D'abord chercher une note cible pertinente pour merge_into
2. Proposer merge_into si cible existe
3. flag_obsolete SEULEMENT si aucune cible pertinente

Une note fragmentaire n'est JAMAIS supprimée sans avoir évalué un merge.

- flag_obsolete : Marquer la note comme obsolète.
  TOUJOURS nécessite validation humaine (Filage). Fournir "reasoning" détaillé.
  Utiliser si : contenu périmé, note dupliquée sans valeur, contenu incompréhensible.
  **NE PAS utiliser pour notes fragmentaires sans avoir évalué merge_into.**
- merge_into : Fusionner cette note dans une autre.
  Auto si confiance >= 0.85, sinon Filage.
  Fournir "target_note_title" (titre de la note cible) dans le JSON.
  Utiliser si : contenu redondant avec une autre note, fragment à consolider.
  **PRIVILÉGIER cette action pour les notes fragmentaires.**
- move_to_folder : Classer la note dans le bon dossier.
  Auto si confiance >= 0.85.
  Fournir le dossier cible dans "content".
  Dossiers possibles : Personnes, Projets, Entités, Réunions, Processus, Événements, Souvenirs

### Actions avancées
- restructure_graph : Proposer split/merge (confiance 0.95 requise)

## Format de réponse JSON
{
  "quality_score": 0-100,
  "reasoning": "Analyse globale de la note",
  "actions": [
    {
      "type": "action_type",
      "target": "section ou champ ciblé",
      "content": "nouveau contenu (si applicable)",
      "confidence": 0.0-1.0,
      "reasoning": "justification de cette action",
      "target_note_title": "titre note cible (pour merge_into uniquement)"
    }
  ]
}

## Règles par type de note
- PERSONNE : Priorité structure > enrichir > liens
- PROJET : Priorité structure > nettoyer > questions
- RÉUNION : Priorité structure > enrichir > liens
- ENTITÉ : Priorité enrichir > liens > structure
- SOUVENIR : Aucune modification (scoring uniquement)
"""

    def __init__(
        self,
        note_manager: NoteManager,
        metadata_store: NoteMetadataStore,
        scheduler: NoteScheduler,
        ai_router: Optional["AIRouter"] = None,
    ):
        """
        Initialize Retouche reviewer

        Args:
            note_manager: Note manager for accessing notes
            metadata_store: Store for metadata
            scheduler: Scheduler for updating review times
            ai_router: AI router for analysis (Sancho)
        """
        self.notes = note_manager
        self.store = metadata_store
        self.scheduler = scheduler
        self.ai_router = ai_router

        # Initialize AnalysisEngine for AI calls if router available
        self._analysis_engine: Optional[AnalysisEngine] = None
        if ai_router:
            self._analysis_engine = _RetoucheAnalysisEngine(
                ai_router=ai_router,
                escalation_thresholds={
                    "sonnet": self.ESCALATE_TO_SONNET_THRESHOLD,
                    "opus": self.ESCALATE_TO_OPUS_THRESHOLD,
                },
            )

    async def review_note(self, note_id: str) -> RetoucheResult:
        """
        Perform a Retouche review of a note

        Args:
            note_id: Note to review

        Returns:
            RetoucheResult with actions taken
        """
        logger.info(f"Starting Retouche for note {note_id}")

        # Load note
        note = self.notes.get_note(note_id)
        if note is None:
            return RetoucheResult(
                note_id=note_id,
                success=False,
                quality_before=None,
                quality_after=0,
                error="Note not found",
            )

        # Load or create metadata
        metadata = self.store.get(note_id)
        if metadata is None:
            from src.passepartout.note_types import detect_note_type_from_path

            note_type = detect_note_type_from_path(str(note.file_path) if note.file_path else "")
            metadata = self.store.create_for_note(
                note_id=note_id,
                note_type=note_type,
                content=note.content,
            )

        quality_before = metadata.quality_score

        # Build context
        context = await self._load_context(note, metadata)

        # Analyze with progressive model escalation
        analysis_result = await self._analyze_with_escalation(context)

        # Process actions
        actions = []
        questions_added = 0
        updated_content = note.content

        for action in analysis_result.actions:
            if action.applied:
                actions.append(action)
                if action.action_type == RetoucheAction.INJECT_QUESTIONS:
                    questions_added += action.content.count("?") if action.content else 0

        # Apply content changes
        tasks_created = 0
        moves_applied = 0
        pending_actions: list[dict] = []

        for action in actions:
            if action.action_type == RetoucheAction.CREATE_OMNIFOCUS:
                # Handle OmniFocus task creation separately
                if action.content:
                    success = await self.create_omnifocus_task(
                        task_name=action.content,
                        note_id=note_id,
                        note_title=note.title,
                    )
                    if success:
                        tasks_created += 1

            elif action.action_type == RetoucheAction.MOVE_TO_FOLDER:
                # Déplacer la note vers le bon dossier
                if action.content and action.applied:
                    target_folder = f"Personal Knowledge Management/{action.content}"
                    try:
                        self.notes.move_note(note_id, target_folder)
                        moves_applied += 1
                        logger.info(
                            f"Note moved to {target_folder}",
                            extra={"note_id": note_id, "folder": action.content},
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to move note: {e}",
                            extra={"note_id": note_id, "folder": action.content},
                        )

            elif action.action_type == RetoucheAction.MERGE_INTO:
                # MERGE_INTO avec auto-apply : fusionner et archiver
                if action.applied and action.target_note_title:
                    merged = await self._execute_merge(
                        source_note_id=note_id,
                        target_note_title=action.target_note_title,
                        source_content=note.content,
                    )
                    if merged:
                        logger.info(
                            f"Note merged into {action.target_note_title}",
                            extra={"note_id": note_id},
                        )

            elif action.content and action.action_type in (
                RetoucheAction.ENRICH,
                RetoucheAction.STRUCTURE,
                RetoucheAction.SUMMARIZE,
                RetoucheAction.SUGGEST_LINKS,
                RetoucheAction.CLEANUP,
                RetoucheAction.PROFILE_INSIGHT,
                RetoucheAction.INJECT_QUESTIONS,
            ):
                updated_content = self._apply_action(updated_content, action)

        # Collecter les actions en attente de confirmation (Filage)
        for action in analysis_result.actions:
            if action.requires_confirmation:
                pending_actions.append({
                    "action_id": f"{note_id}_{action.action_type.value}_{datetime.now(timezone.utc).timestamp()}",
                    "action_type": action.action_type.value,
                    "target": action.target,
                    "content": action.content,
                    "confidence": action.confidence,
                    "reasoning": action.reasoning,
                    "target_note_id": action.target_note_id,
                    "target_note_title": action.target_note_title,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

        # Calculate new quality score
        quality_after = self._calculate_quality_score(context, analysis_result)

        # Save updated note if changes were made
        if updated_content != note.content:
            self.notes.update_note(
                note_id=note_id,
                content=updated_content,
            )

        # Update metadata with new quality score and questions
        metadata.quality_score = quality_after
        if questions_added > 0:
            metadata.questions_pending = True
            metadata.questions_count += questions_added

        # Store pending actions for Filage confirmation
        if pending_actions:
            # Append to existing pending_actions if any
            existing_pending = getattr(metadata, "pending_actions", []) or []
            metadata.pending_actions = existing_pending + pending_actions
            logger.info(
                f"Added {len(pending_actions)} pending actions for Filage",
                extra={"note_id": note_id, "actions": [a["action_type"] for a in pending_actions]},
            )

        # Record actions in enrichment_history
        now = datetime.now(timezone.utc)
        for action in actions:
            record = EnrichmentRecord(
                timestamp=now,
                action_type=action.action_type.value,
                target=action.target,
                content=action.content,
                confidence=action.confidence,
                applied=action.applied,
                reasoning=f"[{action.model_used}] {action.reasoning}",
            )
            metadata.enrichment_history.append(record)

        # Schedule Lecture after first successful Retouche
        if metadata.lecture_next is None and quality_after >= 50:
            # Schedule first Lecture for 24h from now
            metadata.lecture_next = datetime.now(timezone.utc) + timedelta(hours=24)

        # Record Retouche review (updates SM-2)
        self.scheduler.record_review(
            note_id=note_id,
            quality=self._quality_to_sm2(quality_after),
            metadata=metadata,
            cycle_type=CycleType.RETOUCHE,
        )

        logger.info(
            f"Retouche complete for {note_id}: "
            f"quality={quality_before or 0}→{quality_after}, "
            f"actions={len(actions)}, questions={questions_added}, "
            f"tasks={tasks_created}, model={analysis_result.model_used}"
        )

        return RetoucheResult(
            note_id=note_id,
            success=True,
            quality_before=quality_before,
            quality_after=quality_after,
            actions=actions,
            questions_added=questions_added,
            tasks_created=tasks_created,
            model_used=analysis_result.model_used,
            escalated=analysis_result.escalated,
            reasoning=analysis_result.reasoning,
        )

    async def _load_context(
        self,
        note: Note,
        metadata: NoteMetadata,
    ) -> RetoucheContext:
        """Load context for Retouche analysis"""

        # Find linked notes via wikilinks
        wikilinks = self._extract_wikilinks(note.content)
        linked_notes = []
        linked_excerpts = {}

        for link in wikilinks[:10]:  # Limit to 10 linked notes
            linked_note_results = self.notes.search_notes(query=link, top_k=1)
            if linked_note_results:
                if isinstance(linked_note_results[0], tuple):
                    linked_note_obj = linked_note_results[0][0]
                else:
                    linked_note_obj = linked_note_results[0]
                linked_notes.append(linked_note_obj)
                linked_excerpts[link] = linked_note_obj.content[:500]

        # Calculate basic metrics
        word_count = len(note.content.split())
        has_summary = self._has_summary(note.content)
        section_count = len(re.findall(r"^##\s", note.content, re.MULTILINE))
        question_count = note.content.count("?")

        return RetoucheContext(
            note=note,
            metadata=metadata,
            linked_notes=linked_notes,
            linked_note_excerpts=linked_excerpts,
            word_count=word_count,
            has_summary=has_summary,
            section_count=section_count,
            question_count=question_count,
        )

    def _extract_wikilinks(self, content: str) -> list[str]:
        """Extract wikilinks from content"""
        pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        return re.findall(pattern, content)

    def _has_summary(self, content: str) -> bool:
        """Check if content has a summary section"""
        summary_patterns = [
            r"^##?\s*(Résumé|Summary|TL;DR|En bref)",
            r"^>\s*\*\*Résumé",
        ]
        for pattern in summary_patterns:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return True
        return False

    def _scrub_content(self, content: str) -> str:
        """
        Scrub media links and large binary-like patterns from content.

        Replaces ![image](path) or other media markers with placeholders.
        Saves tokens during AI analysis.
        """
        # Replace Markdown images/attachments: ![alt](path)
        scrubbed = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"[MEDIA: \1]", content)

        # Replace HTML images: <img src="...">
        scrubbed = re.sub(r"<img[^>]+src=[\"'][^\"']+[\"'][^>]*>", "[IMAGE]", scrubbed)

        return scrubbed

    def _calculate_hygiene_metrics(self, note: Note) -> HygieneMetrics:
        """
        Calculate structural health metrics for a note (migré de NoteReviewer).

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
        frontmatter_issues: list[str] = []
        frontmatter_valid = True

        required_fields = ["title", "created_at", "updated_at"]
        for field_name in required_fields:
            if field_name not in note.metadata or not note.metadata.get(field_name):
                frontmatter_issues.append(f"Missing: {field_name}")
                frontmatter_valid = False

        # Detect broken wikilinks
        broken_links: list[str] = []
        wikilinks = self._extract_wikilinks(note.content)
        for link in wikilinks[:20]:  # Limit checks to avoid slowdown
            search_result = self.notes.search_notes(query=link, top_k=3)
            if not search_result:
                # No match found
                similar = self.notes.search_notes(query=link, top_k=1)
                if similar:
                    similar_note = similar[0][0] if isinstance(similar[0], tuple) else similar[0]
                    broken_links.append(f"{link} -> suggest: {similar_note.title}")
                else:
                    broken_links.append(link)
            elif isinstance(search_result[0], tuple):
                score = search_result[0][1] if len(search_result[0]) > 1 else 1.0
                if score < 0.7:
                    broken_links.append(f"{link} (low confidence)")

        # Check heading hierarchy
        heading_issues: list[str] = []
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
        duplicate_candidates: list[tuple[str, float]] = []
        try:
            similar_notes = self.notes.search_notes(query=note.content[:500], top_k=5)
            for result in similar_notes:
                if isinstance(result, tuple):
                    similar_note, score = result[0], result[1] if len(result) > 1 else 0.0
                else:
                    similar_note, score = result, 0.0

                if similar_note.note_id == note.note_id:
                    continue
                if score > 0.8:
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

    def _check_temporal_references(
        self,
        content: str,
        criteria: ConservationCriteria | None = None,
    ) -> list[dict]:
        """
        Check for outdated temporal references (migré de NoteReviewer).

        Args:
            content: Note content to analyze
            criteria: Conservation criteria with keep patterns

        Returns:
            List of issues with text, confidence, and reason
        """
        if criteria is None:
            criteria = DEFAULT_CONSERVATION_CRITERIA

        issues: list[dict] = []

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
                context_str = content[max(0, match.start() - 50) : match.end() + 50]
                should_keep = any(
                    re.search(keep_pattern, context_str, re.IGNORECASE)
                    for keep_pattern in criteria.keep_patterns
                )

                if not should_keep:
                    confidence = min(0.85, 0.5 + (days_threshold / 100))
                    issues.append({
                        "text": match.group(0),
                        "confidence": confidence,
                        "reason": f"Référence temporelle potentiellement obsolète: '{match.group(0)}'",
                    })

        return issues

    def _check_completed_tasks(self, content: str) -> list[dict]:
        """
        Check for completed minor tasks (migré de NoteReviewer).

        Args:
            content: Note content to analyze

        Returns:
            List of tasks with text, confidence, and reason
        """
        tasks: list[dict] = []

        pattern = r"\[x\]\s*(.+?)(?:\n|$)"
        matches = re.finditer(pattern, content, re.IGNORECASE)

        for i, match in enumerate(matches):
            if i >= MAX_REGEX_MATCHES:
                logger.warning(f"Hit regex match limit ({MAX_REGEX_MATCHES}) for completed tasks")
                break
            task_text = match.group(1).strip()

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
                tasks.append({
                    "text": match.group(0),
                    "confidence": 0.75,
                    "reason": f"Tâche mineure terminée: '{task_text[:30]}...'",
                })

        return tasks

    def _check_missing_links(
        self,
        content: str,
        _linked_notes: list[Note],
    ) -> list[dict]:
        """
        Check for entities that could be linked (migré de NoteReviewer).

        Args:
            content: Note content to analyze
            _linked_notes: Currently linked notes (for context)

        Returns:
            List of suggestions with entity, confidence, and reason
        """
        suggestions: list[dict] = []

        existing_links = set(self._extract_wikilinks(content))

        pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
        potential_entities = set(re.findall(pattern, content))

        for entity in potential_entities:
            if entity in existing_links:
                continue
            if len(entity) < 3:
                continue

            search_results = self.notes.search_notes(query=entity, top_k=1)
            if search_results:
                suggestions.append({
                    "entity": entity,
                    "confidence": 0.7,
                    "reason": f"Entité '{entity}' pourrait être liée à une note existante",
                })

        return suggestions[:5]

    def _check_formatting(self, content: str) -> list[dict]:
        """
        Check for formatting issues (migré de NoteReviewer).

        Args:
            content: Note content to analyze

        Returns:
            List of issues with location, fix, and reason
        """
        issues: list[dict] = []

        headers = re.findall(r"^(#+)\s", content, re.MULTILINE)
        if headers:
            levels = [len(h) for h in headers]
            if levels and levels[0] != 1:
                issues.append({
                    "location": "headers",
                    "fix": None,
                    "reason": "Le premier titre devrait être de niveau 1 (#)",
                })

        if re.search(r"[ \t]+$", content, re.MULTILINE):
            issues.append({
                "location": "whitespace",
                "fix": re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE),
                "reason": "Espaces en fin de ligne détectés",
            })

        return issues

    def find_related_notes(
        self,
        note: "Note",
        top_k: int = 5,
        exclude_linked: bool = True,
    ) -> list[tuple[str, float]]:
        """
        Find semantically related notes for suggest_links action.

        Uses vector search to find notes similar to the current note,
        optionally excluding already linked notes.

        Args:
            note: The note to find relations for
            top_k: Maximum number of suggestions
            exclude_linked: Whether to exclude already linked notes

        Returns:
            List of (note_title, similarity_score) tuples
        """
        # Get existing links to exclude
        existing_links = set()
        if exclude_linked:
            existing_links = set(self._extract_wikilinks(note.content))
            existing_links.add(note.title)  # Exclude self

        # Search for similar notes using note content
        try:
            results = self.notes.search_notes(
                query=f"{note.title} {note.content[:500]}",
                top_k=top_k + len(existing_links),  # Get extra to filter
                return_scores=True,
            )

            # Filter and format results
            suggestions = []
            for result_note, score in results:
                if result_note.title not in existing_links:
                    suggestions.append((result_note.title, score))
                    if len(suggestions) >= top_k:
                        break

            return suggestions

        except Exception as e:
            logger.warning(f"Failed to find related notes: {e}")
            return []

    async def create_omnifocus_task(
        self,
        task_name: str,
        note_id: str,
        note_title: str,
        project_name: Optional[str] = None,
        due_date: Optional[str] = None,
    ) -> bool:
        """
        Create an OmniFocus task via Figaro.

        Args:
            task_name: Name of the task to create
            note_id: ID of the related note
            note_title: Title of the related note
            project_name: Optional OmniFocus project
            due_date: Optional due date (ISO format)

        Returns:
            True if task was created successfully
        """
        try:
            from src.figaro.actions.tasks import CreateTaskAction

            # Build task note with link to PKM note
            task_note = f"Lié à la note: [[{note_title}]]\nNote ID: {note_id}"

            action = CreateTaskAction(
                name=task_name,
                note=task_note,
                project_name=project_name,
                due_date=due_date,
                tags=["scapin", "retouche"],
            )

            # Validate and execute
            validation = action.validate()
            if not validation.is_valid:
                logger.warning(f"Task validation failed: {validation.errors}")
                return False

            result = action.execute()
            if result.success:
                logger.info(f"Created OmniFocus task: {task_name}")
                return True
            else:
                logger.warning(f"Failed to create task: {result.error}")
                return False

        except ImportError:
            logger.warning("OmniFocus integration not available")
            return False
        except Exception as e:
            logger.error(f"Failed to create OmniFocus task: {e}")
            return False

    async def _analyze_with_escalation(
        self,
        context: RetoucheContext,
    ) -> "AnalysisResult":
        """
        Analyze note with progressive model escalation

        Starts with Haiku, escalates to Sonnet then Opus if confidence is low.
        """
        # Start with Haiku
        result = await self._analyze_with_model(context, model="haiku")

        # Escalate to Sonnet if confidence too low
        if result.confidence < self.ESCALATE_TO_SONNET_THRESHOLD:
            logger.info(
                f"Escalating to Sonnet (confidence={result.confidence:.2f} < {self.ESCALATE_TO_SONNET_THRESHOLD})"
            )
            result = await self._analyze_with_model(context, model="sonnet")
            result.escalated = True

            # Escalate to Opus if still too low
            if result.confidence < self.ESCALATE_TO_OPUS_THRESHOLD:
                logger.info(
                    f"Escalating to Opus (confidence={result.confidence:.2f} < {self.ESCALATE_TO_OPUS_THRESHOLD})"
                )
                result = await self._analyze_with_model(context, model="opus")

        return result

    async def _analyze_with_model(
        self,
        context: RetoucheContext,
        model: str = "haiku",
    ) -> "AnalysisResult":
        """Analyze note with a specific model"""

        # If no AI router, use rule-based analysis
        if self.ai_router is None:
            return self._rule_based_analysis(context)

        try:
            # Build prompt for Retouche analysis
            prompt = self._build_retouche_prompt(context)

            # Call AI router with specified model
            response = await self._call_ai_router(prompt, model)

            # Parse response into actions
            actions = self._parse_ai_response(response, model)

            # Calculate overall confidence
            confidence = sum(a.confidence for a in actions) / len(actions) if actions else 0.8

            return AnalysisResult(
                actions=actions,
                confidence=confidence,
                model_used=model,
                escalated=False,
                reasoning=response.get("reasoning", "AI analysis complete"),
            )

        except Exception as e:
            logger.warning(f"AI analysis failed with {model}: {e}")
            return self._rule_based_analysis(context)

    def _rule_based_analysis(self, context: RetoucheContext) -> "AnalysisResult":
        """
        Fallback rule-based analysis when AI is unavailable.

        Applies hygiene checks migrated from NoteReviewer:
        - Temporal references (obsolete dates)
        - Completed tasks cleanup
        - Missing wikilinks
        - Formatting issues
        """
        actions: list[RetoucheActionResult] = []
        content = context.note.content

        # === Hygiene checks (migré de NoteReviewer) ===

        # Check for outdated temporal references
        temporal_issues = self._check_temporal_references(content)
        for issue in temporal_issues:
            actions.append(
                RetoucheActionResult(
                    action_type=RetoucheAction.CLEANUP,
                    target=issue["text"],
                    confidence=issue["confidence"],
                    reasoning=issue["reason"],
                    applied=issue["confidence"] >= self.AUTO_APPLY_THRESHOLD,
                    model_used="rules",
                )
            )

        # Check for completed tasks that could be cleaned
        completed_tasks = self._check_completed_tasks(content)
        for task in completed_tasks:
            actions.append(
                RetoucheActionResult(
                    action_type=RetoucheAction.CLEANUP,
                    target=task["text"],
                    confidence=task["confidence"],
                    reasoning=task["reason"],
                    applied=task["confidence"] >= self.AUTO_APPLY_THRESHOLD,
                    model_used="rules",
                )
            )

        # Check for missing links
        missing_links = self._check_missing_links(content, context.linked_notes)
        for link in missing_links:
            actions.append(
                RetoucheActionResult(
                    action_type=RetoucheAction.SUGGEST_LINKS,
                    target=link["entity"],
                    content=f"[[{link['entity']}]]",
                    confidence=link["confidence"],
                    reasoning=link["reason"],
                    applied=link["confidence"] >= self.AUTO_APPLY_THRESHOLD,
                    model_used="rules",
                )
            )

        # Check formatting issues
        format_issues = self._check_formatting(content)
        for issue in format_issues:
            actions.append(
                RetoucheActionResult(
                    action_type=RetoucheAction.FORMAT,
                    target=issue["location"],
                    content=issue["fix"],
                    confidence=0.95,
                    reasoning=issue["reason"],
                    applied=True,  # Formatting is safe to auto-apply
                    model_used="rules",
                )
            )

        # === Original rule-based checks ===

        # Check if summary is needed
        if not context.has_summary and context.word_count > 200:
            actions.append(
                RetoucheActionResult(
                    action_type=RetoucheAction.SUMMARIZE,
                    target="header",
                    confidence=0.9,
                    reasoning="Note has sufficient content but no summary",
                    applied=True,
                    model_used="rules",
                )
            )

        # Check if structure improvements are needed
        if context.word_count > 500 and context.section_count < 2:
            actions.append(
                RetoucheActionResult(
                    action_type=RetoucheAction.STRUCTURE,
                    target="content",
                    confidence=0.8,
                    reasoning="Long content with few sections",
                    applied=False,  # Structure changes need review
                    model_used="rules",
                )
            )

        # Always include quality scoring
        actions.append(
            RetoucheActionResult(
                action_type=RetoucheAction.SCORE,
                target="quality",
                confidence=0.95,
                reasoning="Quality assessment",
                applied=True,
                model_used="rules",
            )
        )

        # Calculate overall confidence
        avg_confidence = (
            sum(a.confidence for a in actions) / len(actions) if actions else 0.75
        )

        return AnalysisResult(
            actions=actions,
            confidence=avg_confidence,
            model_used="rules",
            escalated=False,
            reasoning="Rule-based analysis with hygiene checks",
        )

    def _build_retouche_prompt(self, context: RetoucheContext) -> str:
        """
        Build user prompt for AI Retouche analysis using Jinja2 templates.

        Uses specialized templates per note type for focused instructions.
        The static instructions are in SYSTEM_PROMPT (cacheable).

        Args:
            context: RetoucheContext with note and metadata

        Returns:
            User prompt string with note data
        """
        # Get note type safely
        note_type = "inconnu"
        if context.metadata and context.metadata.note_type:
            note_type = context.metadata.note_type.value

        # Extract frontmatter from content
        frontmatter = None
        if context.note.content.startswith("---"):
            parts = context.note.content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()

        # Get quality score from metadata
        quality_score = context.metadata.quality_score if context.metadata else None

        # Get updated_at from metadata or note
        updated_at = None
        if context.metadata and context.metadata.updated_at:
            updated_at = context.metadata.updated_at.isoformat()

        # Use TemplateRenderer for specialized prompts per note type
        renderer = get_template_renderer()
        return renderer.render_retouche(
            note=context.note,
            note_type=note_type,
            word_count=context.word_count,
            content=context.note.content,
            quality_score=quality_score,
            updated_at=updated_at,
            frontmatter=frontmatter,
            linked_notes=context.linked_note_excerpts,
        )

    async def _call_ai_router(
        self,
        prompt: str,
        model: str,
    ) -> dict[str, Any]:
        """
        Call AI router with specified model using AnalysisEngine.

        Uses SYSTEM_PROMPT for cache optimization (Anthropic prompt caching).
        The system prompt is static and cacheable (~90% cost reduction).

        Args:
            prompt: User prompt with note data (dynamic)
            model: Model name ("haiku", "sonnet", "opus")

        Returns:
            Parsed JSON response dict

        Raises:
            AICallError: If AI call fails
            JSONParseError: If response parsing fails
        """
        if self._analysis_engine is None:
            logger.warning("No analysis engine available, returning empty response")
            return {"reasoning": "AI unavailable", "actions": []}

        # Map model string to ModelTier
        model_map = {
            "haiku": ModelTier.HAIKU,
            "sonnet": ModelTier.SONNET,
            "opus": ModelTier.OPUS,
        }
        model_tier = model_map.get(model.lower(), ModelTier.HAIKU)

        try:
            # Call AI using AnalysisEngine with cacheable system prompt
            result = await self._analysis_engine.call_ai(
                prompt=prompt,
                model=model_tier,
                max_tokens=2048,
                system_prompt=self.SYSTEM_PROMPT,  # Cacheable
            )

            # Parse JSON response
            data = self._analysis_engine.parse_json_response(result.response)

            # Log with cache info
            cache_info = ""
            if result.cache_hit:
                cache_info = f", cache_hit={result.cache_read_tokens} tokens"
            elif result.cache_write:
                cache_info = f", cache_write={result.cache_creation_tokens} tokens"

            logger.info(
                f"Retouche AI call: model={model}, tokens={result.tokens_used}, "
                f"duration={result.duration_ms:.0f}ms{cache_info}"
            )

            return data

        except (AICallError, JSONParseError) as e:
            logger.warning(f"Retouche AI call failed: {e}")
            raise

    def _parse_ai_response(
        self,
        response: dict[str, Any],
        model: str,
    ) -> list[RetoucheActionResult]:
        """Parse AI response into RetoucheActionResult list"""
        actions = []

        for action_data in response.get("actions", []):
            action_type_str = action_data.get("type", "score")
            try:
                action_type = RetoucheAction(action_type_str)
            except ValueError:
                action_type = RetoucheAction.SCORE

            confidence = float(action_data.get("confidence", 0.5))
            should_apply = confidence >= self.AUTO_APPLY_THRESHOLD
            requires_confirmation = False

            # Restructure actions need very high confidence
            if action_type == RetoucheAction.RESTRUCTURE_GRAPH:
                should_apply = confidence >= self.RESTRUCTURE_THRESHOLD

            # FLAG_OBSOLETE : TOUJOURS nécessite confirmation humaine
            elif action_type == RetoucheAction.FLAG_OBSOLETE:
                should_apply = False  # Jamais auto
                requires_confirmation = True

            # MERGE_INTO : Auto si >= 0.85, sinon Filage
            elif action_type == RetoucheAction.MERGE_INTO:
                should_apply = confidence >= self.AUTO_APPLY_THRESHOLD
                requires_confirmation = confidence < self.AUTO_APPLY_THRESHOLD

            # MOVE_TO_FOLDER : Auto si >= 0.85
            elif action_type == RetoucheAction.MOVE_TO_FOLDER:
                should_apply = confidence >= self.AUTO_APPLY_THRESHOLD

            actions.append(
                RetoucheActionResult(
                    action_type=action_type,
                    target=action_data.get("target", ""),
                    content=action_data.get("content"),
                    confidence=confidence,
                    reasoning=action_data.get("reasoning", ""),
                    applied=should_apply,
                    model_used=model,
                    target_note_id=action_data.get("target_note_id"),
                    target_note_title=action_data.get("target_note_title"),
                    requires_confirmation=requires_confirmation,
                )
            )

        return actions

    def _apply_action(self, content: str, action: RetoucheActionResult) -> str:
        """Apply a Retouche action to content"""

        if action.action_type == RetoucheAction.SUMMARIZE:
            # Add summary at the beginning after frontmatter
            summary = f"\n> **Résumé**: {action.content or 'À compléter'}\n"
            if content.startswith("---"):
                # Insert after frontmatter
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return f"---{parts[1]}---{summary}{parts[2]}"
            return summary + content

        if action.action_type == RetoucheAction.ENRICH:
            # Append enrichment content
            if action.content:
                return f"{content.rstrip()}\n\n{action.content}"
            return content

        if action.action_type == RetoucheAction.STRUCTURE:
            # For now, just log - full restructuring is complex
            logger.info(f"Structure suggestion: {action.reasoning}")
            return content

        if action.action_type == RetoucheAction.INJECT_QUESTIONS:
            # Add questions section
            if action.content:
                questions_section = f"\n\n## Questions pour Johan\n\n{action.content}\n"
                return f"{content.rstrip()}{questions_section}"
            return content

        if action.action_type == RetoucheAction.SUGGEST_LINKS:
            # Add suggested wikilinks section
            if action.content:
                links_section = f"\n\n## Liens suggérés\n\n{action.content}\n"
                return f"{content.rstrip()}{links_section}"
            return content

        if action.action_type == RetoucheAction.CLEANUP:
            # Content cleanup - mark obsolete sections or remove them
            # The AI provides the cleaned content directly
            if action.content:
                # If confidence is high enough, replace content
                if action.confidence >= self.AUTO_APPLY_THRESHOLD:
                    logger.info(f"Cleanup applied: {action.reasoning}")
                    return action.content
                # Otherwise, add a warning comment
                warning = f"\n\n<!-- CLEANUP SUGGÉRÉ ({action.confidence:.0%}): {action.reasoning} -->\n"
                return f"{content.rstrip()}{warning}"
            return content

        if action.action_type == RetoucheAction.PROFILE_INSIGHT:
            # Add behavioral/psychological insight section
            if action.content:
                insight_section = f"\n\n## Insights\n\n{action.content}\n"
                return f"{content.rstrip()}{insight_section}"
            return content

        if action.action_type == RetoucheAction.CREATE_OMNIFOCUS:
            # OmniFocus task creation is handled separately, not content modification
            # Just log it - actual creation happens in review_note
            logger.info(f"OmniFocus task to create: {action.content}")
            return content

        if action.action_type == RetoucheAction.FLAG_OBSOLETE:
            # FLAG_OBSOLETE ne modifie pas le contenu
            # L'action est stockée dans pending_actions et traitée via Filage
            logger.info(f"Note flagged as obsolete: {action.reasoning}")
            return content

        if action.action_type == RetoucheAction.MERGE_INTO:
            # MERGE_INTO ne modifie pas le contenu de la note source
            # L'action est appliquée via le service (append à la cible + soft delete source)
            logger.info(
                f"Merge requested into: {action.target_note_title or action.target}"
            )
            return content

        if action.action_type == RetoucheAction.MOVE_TO_FOLDER:
            # MOVE_TO_FOLDER ne modifie pas le contenu
            # Le déplacement est géré par NoteManager.move_note() dans review_note
            logger.info(f"Move to folder requested: {action.content}")
            return content

        return content

    def _determine_merge_master(
        self, note_a: Note, note_b: Note
    ) -> tuple[Note, Note]:
        """
        Determine which note should be the master in a merge.

        Rules:
        1. Note in "Personal Knowledge Management" folder = master
        2. Otherwise, oldest note = master

        Args:
            note_a: First note
            note_b: Second note

        Returns:
            Tuple of (master, follower) notes
        """
        a_in_pkm = "Personal Knowledge Management" in str(note_a.file_path or "")
        b_in_pkm = "Personal Knowledge Management" in str(note_b.file_path or "")

        if a_in_pkm and not b_in_pkm:
            return (note_a, note_b)
        if b_in_pkm and not a_in_pkm:
            return (note_b, note_a)

        # Same PKM status: oldest wins
        if note_a.created_at <= note_b.created_at:
            return (note_a, note_b)
        return (note_b, note_a)

    async def _execute_merge(
        self,
        source_note_id: str,
        target_note_title: str,
        _source_content: str,
    ) -> bool:
        """
        Execute automatic merge of source note into target note.

        Uses _determine_merge_master to decide which note becomes the master:
        - Note in PKM folder takes priority
        - Otherwise, oldest note is master

        Args:
            source_note_id: ID of the note requesting merge
            target_note_title: Title of the suggested target note
            _source_content: Unused, kept for API compatibility

        Returns:
            True if merge was successful
        """
        try:
            # Get source note
            source_note = self.notes.get_note(source_note_id)
            if not source_note:
                logger.warning(
                    f"Merge source not found: {source_note_id}",
                )
                return False

            # Find target note by title
            target_results = self.notes.search_notes(query=target_note_title, top_k=1)
            if not target_results:
                logger.warning(
                    f"Merge target not found: {target_note_title}",
                    extra={"source_note_id": source_note_id},
                )
                return False

            target_note = target_results[0]
            if isinstance(target_note, tuple):
                target_note = target_note[0]

            # Determine master/follower based on PKM priority and age
            master, follower = self._determine_merge_master(source_note, target_note)

            # Merge follower content into master
            merged_content = (
                f"{master.content.rstrip()}\n\n---\n\n"
                f"## Contenu fusionné depuis [[{follower.title}]]\n\n"
                f"{follower.content}"
            )
            self.notes.update_note(
                note_id=master.note_id,
                content=merged_content,
            )

            # Soft delete follower note (move to _Supprimées)
            self.notes.delete_note(follower.note_id)

            logger.info(
                f"Merge completed: {follower.note_id} → {master.note_id}",
                extra={
                    "follower_id": follower.note_id,
                    "follower_title": follower.title,
                    "master_id": master.note_id,
                    "master_title": master.title,
                },
            )
            return True

        except Exception as e:
            logger.error(
                f"Merge failed: {e}",
                extra={"source_note_id": source_note_id, "target_title": target_note_title},
                exc_info=True,
            )
            return False

    def _calculate_quality_score(
        self,
        context: RetoucheContext,
        analysis: "AnalysisResult",
    ) -> int:
        """
        Calculate quality score (0-100) — v2 formula

        Factors:
        - Contenu (max 30 pts): seuils à 50, 200, 500 mots
        - Structure (max 25 pts): résumé + sections
        - Liens (max 15 pts): wikilinks sortants
        - Complétude IA (max 30 pts): bonus si peu d'actions proposées

        Base à 0 (note vide = 0, pas 50).
        """
        score = 0  # Base neutre

        # === Contenu (max 30 pts) ===
        if context.word_count >= 50:
            score += 10
        if context.word_count >= 200:
            score += 10
        if context.word_count >= 500:
            score += 10

        # === Structure (max 25 pts) ===
        if context.has_summary:
            score += 15
        score += min(10, context.section_count * 3)

        # === Liens (max 15 pts) ===
        # Compter les wikilinks dans le contenu
        outgoing_links = self._extract_wikilinks(context.note.content)
        score += min(15, len(outgoing_links) * 3)

        # === Complétude IA (max 30 pts) ===
        # Moins d'actions proposées = note déjà bien formée
        # 0 actions = +30, 1 action = +20, 2 = +10, 3+ = 0
        proposed_actions = [a for a in analysis.actions if a.action_type != RetoucheAction.SCORE]
        completeness_bonus = max(0, 30 - (len(proposed_actions) * 10))
        score += completeness_bonus

        # Ensure score is in valid range
        return max(0, min(100, score))

    def _quality_to_sm2(self, quality_score: int) -> int:
        """Convert quality score (0-100) to SM-2 quality (0-5)"""
        if quality_score >= 90:
            return 5
        if quality_score >= 75:
            return 4
        if quality_score >= 60:
            return 3
        if quality_score >= 40:
            return 2
        if quality_score >= 20:
            return 1
        return 0


@dataclass
class AnalysisResult:
    """Internal result of AI/rule-based analysis"""

    actions: list[RetoucheActionResult]
    confidence: float
    model_used: str
    escalated: bool
    reasoning: str


class _RetoucheAnalysisEngine(AnalysisEngine):
    """
    Internal AnalysisEngine implementation for Retouche.

    Provides AI call functionality with escalation and JSON parsing.
    This is a minimal implementation - the actual prompt building and
    result processing are handled by RetoucheReviewer.
    """

    def _build_prompt(self, context: Any) -> str:
        """Not used - prompts are built by RetoucheReviewer."""
        raise NotImplementedError("Use RetoucheReviewer._build_retouche_prompt()")

    def _process_result(self, result: dict[str, Any], call_result: AICallResult) -> Any:
        """Not used - results are processed by RetoucheReviewer."""
        raise NotImplementedError("Use RetoucheReviewer._parse_ai_response()")
