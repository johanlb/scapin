"""
Multi-Pass Analyzer — Workflow v3.0 (Four Valets)

Analyseur d'événements utilisant le pipeline des "Quatre Valets" :
Grimaud → Bazin → Planchet → Mousqueton.

Ce module implémente la phase d'analyse du pipeline v3.0 :
1. Grimaud : Extraction silencieuse (raw facts)
2. Bazin : Enrichissement contextuel (PKM context)
3. Planchet : Critique et validation (cross-check)
4. Mousqueton : Arbitrage final (resolution)

Usage:
    analyzer = MultiPassAnalyzer(ai_router, context_searcher)
    result = await analyzer.analyze(event)

Part of Sancho's Four Valets extraction system.
See ADR-005 for design decisions.
"""

import json
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

from dateutil import parser as date_parser

from src.core.events.universal_event import PerceivedEvent
from src.monitoring.logger import get_logger
from src.sancho.context_searcher import ContextSearcher, StructuredContext
from src.sancho.convergence import (
    AnalysisContext,
    DecomposedConfidence,
    Extraction,
    ExtractionConfidence,
    MultiPassConfig,
    PassResult,
    PassType,
    ValetType,
    is_high_stakes,
)
from src.sancho.model_selector import ModelTier
from src.sancho.router import AIModel, AIRouter, _repair_json_with_library, clean_json_string
from src.sancho.template_renderer import TemplateRenderer, get_template_renderer

if TYPE_CHECKING:
    from src.passepartout.context_loader import CanevasStatus
    from src.passepartout.entity_search import EntitySearcher
    from src.passepartout.note_manager import NoteManager
    from src.sancho.coherence_validator import CoherenceResult, CoherenceService

logger = get_logger("multi_pass_analyzer")

# Age thresholds for action adjustments
# Emails older than this get "flag" downgraded to "archive"
OLD_EMAIL_THRESHOLD_DAYS = 90  # 3 months
# Emails older than this don't get OmniFocus tasks created
VERY_OLD_EMAIL_THRESHOLD_DAYS = 365  # 1 year

# Types d'extraction avec valeur historique intrinsèque (ne jamais réduire la confiance)
HISTORICAL_VALUE_TYPES = {"reference", "montant", "relation"}

# Patterns de noms propres à exclure de la détection de contenu critique
# Ces patterns correspondent à des noms de famille ou entités qui contiennent
# des mots-clés juridiques mais ne sont pas des documents légaux
PROPER_NAME_EXCLUSIONS = {
    "le bail",  # Nom de famille (Johan Le Bail)
    "bail web",  # Site de généalogie Le Bail
}

# Patterns de disclaimers automatiques à ignorer dans la détection de contenu sensible
# Ces patterns apparaissent dans les footers d'emails et ne sont pas du contenu sensible réel
EMAIL_DISCLAIMER_PATTERNS = {
    "this email is confidential",
    "this message is confidential",
    "confidential and may be privileged",
    "confidential information",
    "cet email est confidentiel",
    "ce message est confidentiel",
    "information confidentielle",
    "strictly confidential",
    "private and confidential",
}

# Mots-clés indiquant une valeur contractuelle/historique dans le contenu
HISTORICAL_KEYWORDS = {
    # Contractuel
    "bail", "contrat", "signature", "signé", "résilié", "résiliation",
    "achat", "vente", "vendu", "acheté", "acquisition",
    # Relations locatives/immobilières
    "locataire", "propriétaire", "loyer", "caution", "dépôt",
    # Périodes
    "début", "fin", "période", "durée", "terme",
    # Événements de vie
    "naissance", "décès", "mariage", "divorce",
    # Références
    "facture", "devis", "commande", "livraison",
}


class MultiPassAnalyzerError(Exception):
    """Base exception for multi-pass analyzer errors"""

    pass


class PromptRenderError(MultiPassAnalyzerError):
    """Error rendering the prompt template"""

    pass


class APICallError(MultiPassAnalyzerError):
    """Error calling the AI API"""

    pass


class ParseError(MultiPassAnalyzerError):
    """Error parsing the AI response"""

    pass


class MaxPassesReachedError(MultiPassAnalyzerError):
    """Maximum number of passes reached without convergence"""

    pass


class CanevasIncompleteError(MultiPassAnalyzerError):
    """Canevas is incomplete and restriction is enabled (v3.2)."""

    def __init__(self, status: "CanevasStatus"):
        self.status = status
        from src.passepartout.context_loader import CanevasFileStatus

        missing = [f.name for f in status.files if f.status == CanevasFileStatus.MISSING]
        partial = [f.name for f in status.files if f.status in (CanevasFileStatus.PARTIAL, CanevasFileStatus.EMPTY)]
        msg_parts = []
        if missing:
            msg_parts.append(f"fichiers manquants: {missing}")
        if partial:
            msg_parts.append(f"fichiers partiels: {partial}")
        super().__init__(f"Canevas incomplet: {', '.join(msg_parts)}")


@dataclass
class MultiPassResult:
    """Final result of multi-pass analysis"""

    # Final extraction result
    extractions: list[Extraction]
    action: str
    confidence: DecomposedConfidence
    entities_discovered: set[str]

    # Analysis metadata
    passes_count: int
    total_duration_ms: float
    total_tokens: int
    final_model: str
    escalated: bool

    # Pass history for transparency
    pass_history: list[PassResult] = field(default_factory=list)

    # Stop reason
    stop_reason: str = ""

    # High-stakes indicator
    high_stakes: bool = False

    # Draft reply (if action is reply)
    draft_reply: Optional[str] = None

    # Coherence validation metadata (v2.2+)
    coherence_validated: bool = False
    coherence_corrections: int = 0
    coherence_duplicates_detected: int = 0
    coherence_confidence: float = 1.0
    coherence_warnings: list[dict] = field(default_factory=list)

    # Retrieved context for transparency (v2.2.2+)
    retrieved_context: Optional[dict[str, Any]] = None

    # Context influence from last contextual pass (v2.2.2+)
    context_influence: Optional[dict[str, Any]] = None

    # Four Valets v3.0 fields
    critique: Optional[dict[str, Any]] = None
    arbitrage: Optional[dict[str, Any]] = None
    memory_hint: Optional[dict[str, Any]] = None
    confidence_assessment: Optional[dict[str, Any]] = None
    stopped_at: Optional[str] = None  # "grimaud", "planchet", "mousqueton"

    # Strategic questions accumulated from all valets (v3.1)
    # Questions requiring human decision, organized by source valet and target note
    strategic_questions: list[dict[str, Any]] = field(default_factory=list)

    # Canevas status for visibility (v3.2)
    canevas_status: Optional[dict[str, Any]] = None

    @property
    def four_valets_mode(self) -> bool:
        """True si analysé avec Four Valets v3.0."""
        return self.stopped_at is not None

    @property
    def high_confidence(self) -> bool:
        """Check if result is high confidence (>= 90%)"""
        return self.confidence.overall >= 0.90

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "extractions": [
                {
                    "info": e.info,
                    "type": e.type,
                    "importance": e.importance,
                    "note_cible": e.note_cible,
                    "note_action": e.note_action,
                    "omnifocus": e.omnifocus,
                    "calendar": e.calendar,
                    "date": e.date,
                    "time": e.time,
                    "timezone": e.timezone,
                    "duration": e.duration,
                    "required": e.required,
                    "confidence": e.confidence,
                }
                for e in self.extractions
            ],
            "action": self.action,
            "confidence": self.confidence.to_dict(),
            "entities_discovered": list(self.entities_discovered),
            "passes_count": self.passes_count,
            "total_duration_ms": self.total_duration_ms,
            "total_tokens": self.total_tokens,
            "final_model": self.final_model,
            "escalated": self.escalated,
            "stop_reason": self.stop_reason,
            "high_stakes": self.high_stakes,
            "high_confidence": self.high_confidence,
            "pass_history": [p.to_dict() for p in self.pass_history],
            "draft_reply": self.draft_reply,
            # Coherence validation (v2.2+)
            "coherence_validated": self.coherence_validated,
            "coherence_corrections": self.coherence_corrections,
            "coherence_duplicates_detected": self.coherence_duplicates_detected,
            "coherence_confidence": self.coherence_confidence,
            "coherence_warnings": self.coherence_warnings,
            # Retrieved context for transparency (v2.2.2+)
            "retrieved_context": self.retrieved_context,
            "context_influence": self.context_influence,
            # Four Valets v3.0 fields
            "stopped_at": self.stopped_at,
            "four_valets_mode": self.four_valets_mode,
            # Strategic questions v3.1
            "strategic_questions": self.strategic_questions,
            # Canevas status v3.2
            "canevas_status": self.canevas_status,
        }


class MultiPassAnalyzer:
    """
    Multi-pass event analyzer with Four Valets architecture (v3.0).

    Implements the Four Valets pipeline:
    1. Grimaud: Silent extraction (raw facts)
    2. Bazin: Context enrichment (PKM knowledge)
    3. Planchet: Critique and validation
    4. Mousqueton: Final arbitration

    Attributes:
        ai_router: Router for Claude API calls
        context_searcher: Searcher for PKM context
        template_renderer: Jinja2 template renderer
        config: Multi-pass configuration

    Example:
        >>> analyzer = MultiPassAnalyzer(router, context_searcher)
        >>> result = await analyzer.analyze(event)
        >>> if result.high_confidence:
        ...     # Auto-apply extractions
        ...     pass
    """

    # Model tier mapping
    MODEL_MAP = {
        ModelTier.HAIKU: AIModel.CLAUDE_HAIKU,
        ModelTier.SONNET: AIModel.CLAUDE_SONNET,
        ModelTier.OPUS: AIModel.CLAUDE_OPUS,
    }

    # Ephemeral content detection constants
    # Financial documents that must ALWAYS be archived (never ephemeral)
    FINANCIAL_INDICATORS = frozenset(
        [
            "bilan",
            "bilan financier",
            "bilan annuel",
            "annual report",
            "financial statement",
            "financial report",
            "rapport financier",
            "comptes annuels",
            "états financiers",
            "compte de résultat",
            "résumé financier",
            "financial summary",
            "audit",
            "comptes",
            "rapport annuel",
            "yearly report",
            "fiscal year",
            "clôture comptable",
            "exercice comptable",
            "year end",
        ]
    )

    # Legal/corporate documents that must ALWAYS be archived (never ephemeral)
    LEGAL_INDICATORS = frozenset(
        [
            "contrat",
            "contract",
            "facture",
            "invoice",
            "bon de commande",
            "purchase order",
            "devis signé",
            "procès-verbal",
            "pv de réunion",
            "procuration",
            "power of attorney",
            "statuts sociaux",
            "bylaws",
            "certificat",
            "certificate",
            "attestation officielle",
            "déclaration fiscale",
            "companies act",
            "accord commercial",
            "accord signé",
            "legal agreement",
            "avenant au contrat",
            "amendment",
            "résiliation",
            "termination notice",
            "licence commerciale",
            "business license",
            "permis de construire",
            # Real estate / rental documents
            "bail",
            "lease",
            "locataire",
            "tenant",
            "location",
            "rental",
            "préavis",
            "notice period",
            "fin de bail",
            "end of lease",
            "renouvellement",
            "renewal",
            "loyer",
            "rent",
            "propriétaire",
            "landlord",
        ]
    )

    # Sensitive content indicators (conflicts, HR issues, strategic decisions)
    # These require careful handling → escalate to Opus
    SENSITIVE_INDICATORS = frozenset(
        [
            # Conflicts and heated discussions
            "conflit",
            "conflict",
            "dispute",
            "litige",
            "désaccord",
            "disagreement",
            "plainte",
            "complaint",
            "réclamation",
            "claim",
            "mécontentement",
            "dissatisfaction",
            "insatisfait",
            "unhappy",
            "inacceptable",
            "unacceptable",
            "mise en demeure",
            "formal notice",
            # HR and employment issues
            "licenciement",
            "dismissal",
            "layoff",
            "fin de contrat",
            "end of contract",
            "démission",
            "resignation",
            "rupture conventionnelle",
            "avertissement",
            "warning",
            "sanction",
            "entretien préalable",
            "disciplinary",
            # Negotiations and strategic decisions
            "négociation",
            "negotiation",
            "proposition commerciale",
            "offre ferme",
            "firm offer",
            "contre-proposition",
            "counter-offer",
            "décision stratégique",
            "strategic decision",
            "partenariat",
            "partnership",
            "acquisition",
            "fusion",
            "merger",
            # Urgency and critical issues
            "urgent",
            "critique",
            "critical",
            "priorité absolue",
            "top priority",
            "deadline impérative",
            "immédiat",
            "immediate",
            "asap",
            # Confidential and sensitive data
            "confidentiel",
            "confidential",
            "secret",
            "ne pas diffuser",
            "do not share",
            "strictement personnel",
            "strictly personal",
            "données personnelles",
            "personal data",
            "rgpd",
            "gdpr",
        ]
    )

    # Newsletter/digest indicators (periodic content, no lasting value)
    NEWSLETTER_INDICATORS = frozenset(
        [
            "newsletter",
            "digest",
            "daily",
            "weekly",
            "monthly",
            "highlights",
            "roundup",
            "recap",
            "summary",
            "bulletin",
            "noreply",
            "no-reply",
            "mailer",
            "news@",
            "updates@",
            "medium",
            "substack",
            "mailchimp",
            "sendinblue",
        ]
    )

    # OTP/verification code indicators (always ephemeral)
    OTP_INDICATORS = frozenset(
        [
            "otp",
            "one-time password",
            "code de vérification",
            "verification code",
            "code d'authentification",
            "authentication code",
            "code de sécurité",
            "security code",
            "code de confirmation",
            "confirmation code",
            "code à usage unique",
            "single-use code",
            "2fa",
            "two-factor",
            "mot de passe temporaire",
            "temporary password",
            "code pin",
            "entrer le code",
            "enter the code",
            "saisissez le code",
            "pour vous authentifier",
            "to authenticate",
            "pour confirmer",
            "code suivant",
            "following code",
            "voici votre code",
        ]
    )

    # Event/invitation indicators (time-bound content)
    EVENT_INDICATORS = frozenset(
        [
            "vous invite",
            "invitation",
            "événement",
            "event",
            "rendez-vous",
            "rencontrer",
            "découvrir",
            "jeudi",
            "vendredi",
            "samedi",
            "dimanche",
            "lundi",
            "mardi",
            "mercredi",
            "à 17h",
            "à 18h",
            "à 19h",
            "à 20h",
            "offre valable",
            "jusqu'au",
            "expire",
            "limited time",
        ]
    )

    # Date patterns for extraction (French/English)
    DATE_PATTERNS = [
        r"\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*\d{0,4}",
        r"\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s*\d{0,4}",
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"\d{4}-\d{2}-\d{2}",
        r"jusqu'au\s+\d{1,2}\s+\w+\s*\d{0,4}",
        r"until\s+\d{1,2}\s+\w+\s*\d{0,4}",
    ]

    # Extraction types that indicate time-bound content
    TIME_BOUND_TYPES = frozenset(["evenement", "deadline", "fait"])

    def __init__(
        self,
        ai_router: AIRouter,
        context_searcher: Optional["ContextSearcher"] = None,
        template_renderer: Optional[TemplateRenderer] = None,
        config: Optional[MultiPassConfig] = None,
        note_manager: Optional["NoteManager"] = None,
        entity_searcher: Optional["EntitySearcher"] = None,
        enable_coherence_pass: bool = True,
    ):
        """
        Initialize the multi-pass analyzer.

        Args:
            ai_router: AIRouter instance for API calls
            context_searcher: ContextSearcher for PKM context (optional)
            template_renderer: TemplateRenderer for prompts (optional, uses singleton)
            config: MultiPassConfig (uses defaults if None)
            note_manager: NoteManager for coherence validation (optional, enables coherence pass)
            entity_searcher: EntitySearcher for finding similar notes (optional)
            enable_coherence_pass: Whether to run coherence validation (default: True)
        """
        self.ai_router = ai_router
        self._context_searcher = context_searcher
        self._template_renderer = template_renderer
        self.config = config or MultiPassConfig()
        self._note_manager = note_manager
        self._entity_searcher = entity_searcher
        self._enable_coherence_pass = enable_coherence_pass
        self._coherence_service: "CoherenceService | None" = None  # noqa: UP037

    @property
    def context_searcher(self) -> Optional["ContextSearcher"]:
        """Get context searcher (lazy load if needed)"""
        return self._context_searcher

    @property
    def template_renderer(self) -> TemplateRenderer:
        """Get template renderer (singleton if not provided)"""
        if self._template_renderer is None:
            self._template_renderer = get_template_renderer()
        return self._template_renderer

    @property
    def coherence_service(self) -> Optional["CoherenceService"]:
        """
        Get coherence service (lazy initialization).

        Returns None if note_manager is not configured or coherence pass is disabled.
        """
        if not self._enable_coherence_pass or self._note_manager is None:
            return None

        if self._coherence_service is None:
            from src.sancho.coherence_validator import CoherenceService

            self._coherence_service = CoherenceService(
                note_manager=self._note_manager,
                ai_router=self.ai_router,
                entity_searcher=self._entity_searcher,
                template_renderer=self.template_renderer,
            )
        return self._coherence_service

    async def analyze(
        self,
        event: PerceivedEvent,
        sender_importance: str = "normal",
    ) -> MultiPassResult:
        """
        Analyze an event using the Four Valets v3.0 pipeline.

        Pipeline: Grimaud → Bazin → Planchet → Mousqueton.

        Args:
            event: Perceived event to analyze
            sender_importance: Sender importance level (normal, important, vip)

        Returns:
            MultiPassResult with extractions and metadata

        Raises:
            MultiPassAnalyzerError: If analysis fails
        """
        # Always use Four Valets v3.0 pipeline
        try:
            return await self._run_four_valets_pipeline(event, sender_importance)
        except Exception as e:
            logger.error(f"Four Valets analysis failed: {e}", exc_info=True)
            raise MultiPassAnalyzerError(f"Analysis failed: {e}") from e

    async def _run_coherence_pass(
        self,
        extractions: list[Extraction],
        event: PerceivedEvent,
    ) -> tuple[list[Extraction], Optional["CoherenceResult"]]:
        """
        Run the coherence validation pass on extractions.

        This pass:
        1. Loads FULL content of target notes (not snippets)
        2. Validates enrichir vs creer decisions
        3. Detects duplicates
        4. Suggests appropriate sections
        5. Corrects note targets when needed

        Args:
            extractions: Extractions to validate
            event: Original event for context

        Returns:
            Tuple of (validated_extractions, coherence_result)
            If coherence service is not available, returns original extractions
            and None for coherence_result.
        """
        if not self.coherence_service or not extractions:
            return extractions, None

        # Only validate extractions that have a note target
        extractions_with_targets = [e for e in extractions if e.note_cible]
        if not extractions_with_targets:
            return extractions, None

        logger.info(f"Running coherence pass on {len(extractions_with_targets)} extractions")

        try:
            # Run coherence validation (asynchronous)
            coherence_result = await self.coherence_service.validate_extractions(
                extractions_with_targets, event
            )

            # Convert validated extractions back to Extraction objects
            validated_extractions = self._apply_coherence_validations(extractions, coherence_result)

            logger.info(
                f"Coherence pass completed: {coherence_result.coherence_summary.corrected} corrected, "
                f"{coherence_result.coherence_summary.duplicates_detected} duplicates"
            )

            return validated_extractions, coherence_result

        except Exception as e:
            logger.error(f"Coherence pass failed: {e}", exc_info=True)
            # Return original extractions on failure
            return extractions, None

    def _apply_coherence_validations(
        self,
        original_extractions: list[Extraction],
        coherence_result: "CoherenceResult",
    ) -> list[Extraction]:
        """
        Apply coherence validations to create updated Extraction list.

        Maps validated extractions back to Extraction objects,
        updating note targets and filtering duplicates.

        Args:
            original_extractions: Original extraction list
            coherence_result: Result from coherence validation

        Returns:
            Updated list of Extraction objects
        """

        # Create a map of original extractions by info for matching
        original_map: dict[str, Extraction] = {e.info: e for e in original_extractions}

        validated_extractions = []
        validated_set = set()  # Track which originals were validated

        for ve in coherence_result.validated_extractions:
            # Skip duplicates
            if ve.is_duplicate:
                logger.debug(f"Skipping duplicate extraction: {ve.info[:50]}...")
                continue

            # Find the original extraction
            original = original_map.get(ve.info)
            if not original:
                # Try to find by fuzzy match if exact match fails
                for key, ext in original_map.items():
                    if key not in validated_set and ve.info[:30] in key:
                        original = ext
                        break

            if original:
                validated_set.add(original.info)

                # Create updated extraction with validated values
                updated = Extraction(
                    info=original.info,
                    type=original.type,
                    importance=original.importance,
                    note_cible=ve.validated_note_cible or original.note_cible,
                    note_action=ve.note_action or original.note_action,
                    omnifocus=original.omnifocus,
                    calendar=original.calendar,
                    date=original.date,
                    time=original.time,
                    timezone=original.timezone,
                    duration=original.duration,
                    required=original.required,
                    confidence=original.confidence,
                    # Add suggested section if available (store in generic_title field for now)
                    generic_title=original.generic_title,
                )
                validated_extractions.append(updated)
            else:
                logger.warning(f"Could not match validated extraction: {ve.info[:50]}...")

        # Add extractions that weren't part of coherence validation
        # (those without note targets)
        for ext in original_extractions:
            if ext.info not in validated_set and not ext.note_cible:
                validated_extractions.append(ext)

        return validated_extractions

    async def _call_model(
        self,
        prompt: str,
        model_tier: ModelTier,
        pass_number: int,
        pass_type: PassType,
    ) -> PassResult:
        """
        Call the AI model and parse the response.

        Args:
            prompt: Rendered prompt
            model_tier: Model tier to use
            pass_number: Current pass number
            pass_type: Type of pass

        Returns:
            Parsed PassResult

        Raises:
            APICallError: If API call fails
            ParseError: If response parsing fails
        """
        start_time = time.time()
        model = self.MODEL_MAP[model_tier]

        try:
            # Call Claude via router
            response, usage = self.ai_router._call_claude(
                prompt=prompt,
                model=model,
                max_tokens=2048,
            )

            duration_ms = (time.time() - start_time) * 1000

            if response is None:
                raise APICallError("API returned None response")

            # Parse response
            return self._parse_response(
                response=response,
                model_tier=model_tier,
                model_id=model.value,
                pass_number=pass_number,
                pass_type=pass_type,
                usage=usage,
                duration_ms=duration_ms,
            )

        except ParseError:
            logger.warning("Failed to parse response, will retry on next pass")
            raise

        except Exception as e:
            logger.error(f"API call failed: {e}", exc_info=True)
            raise APICallError(f"API call failed: {e}") from e

    async def _call_model_with_cache(
        self,
        system_prompt: str,
        user_prompt: str,
        model_tier: ModelTier,
        pass_number: int,
        pass_type: PassType,
    ) -> PassResult:
        """
        Call the AI model with prompt caching enabled.

        Uses Anthropic's prompt caching feature to cache the system prompt,
        reducing costs by ~90% on cached tokens and improving latency.

        Args:
            system_prompt: Static system prompt (will be cached)
            user_prompt: Dynamic user prompt
            model_tier: Model tier to use
            pass_number: Current pass number
            pass_type: Type of pass

        Returns:
            Parsed PassResult

        Raises:
            APICallError: If API call fails
            ParseError: If response parsing fails
        """
        start_time = time.time()
        model = self.MODEL_MAP[model_tier]

        try:
            # Call Claude via router with cache
            response, usage = self.ai_router._call_claude_with_cache(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                model=model,
                max_tokens=2048,
            )

            duration_ms = (time.time() - start_time) * 1000

            if response is None:
                raise APICallError("API returned None response")

            # Log cache stats
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_write = usage.get("cache_creation_input_tokens", 0)
            if cache_read > 0:
                logger.info(
                    f"Pass {pass_number} ({pass_type.value}): Cache HIT - "
                    f"{cache_read} tokens from cache"
                )
            elif cache_write > 0:
                logger.info(
                    f"Pass {pass_number} ({pass_type.value}): Cache WRITE - "
                    f"{cache_write} tokens written to cache"
                )

            # Parse response
            return self._parse_response(
                response=response,
                model_tier=model_tier,
                model_id=model.value,
                pass_number=pass_number,
                pass_type=pass_type,
                usage=usage,
                duration_ms=duration_ms,
            )

        except ParseError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"API call failed for Pass {pass_number}: {e}", exc_info=True)
            raise APICallError(f"API call failed: {e}") from e

    def _parse_response(
        self,
        response: str,
        model_tier: ModelTier,
        model_id: str,
        pass_number: int,
        pass_type: PassType,
        usage: dict,
        duration_ms: float,
    ) -> PassResult:
        """
        Parse the JSON response into PassResult.

        Args:
            response: Raw response text from Claude
            model_tier: Model tier used
            model_id: Full model ID
            pass_number: Pass number
            pass_type: Pass type
            usage: Token usage dict
            duration_ms: API call duration

        Returns:
            Parsed PassResult

        Raises:
            ParseError: If JSON parsing fails
        """
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)

            # Multi-level JSON repair strategy (same as router.py)
            # Level 1: Direct parse (ideal case)
            # Level 2: json-repair library (robust, handles most issues)
            # Level 3: Regex cleaning + json-repair (last resort)
            data = None
            parse_method = "direct"

            # Level 1: Try direct parse
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Level 2: Try json-repair library first
                repaired, repair_success = _repair_json_with_library(json_str)
                if repair_success:
                    try:
                        data = json.loads(repaired)
                        parse_method = "json-repair"
                        logger.debug("JSON repaired successfully using json-repair library")
                    except json.JSONDecodeError:
                        pass

                # Level 3: If json-repair didn't work, try regex + json-repair
                if data is None:
                    cleaned = clean_json_string(json_str)
                    try:
                        data = json.loads(cleaned)
                        parse_method = "regex-clean"
                        logger.debug("JSON parsed after regex cleaning")
                    except json.JSONDecodeError:
                        # Last resort: json-repair on regex-cleaned string
                        repaired2, _ = _repair_json_with_library(cleaned)
                        try:
                            data = json.loads(repaired2)
                            parse_method = "regex+json-repair"
                            logger.debug("JSON repaired using regex + json-repair")
                        except json.JSONDecodeError as e:
                            # All methods failed, raise with details
                            preview = json_str[:300].replace("\n", "\\n")
                            raise ParseError(
                                f"All JSON repair methods failed. Error: {e}. Preview: {preview}"
                            ) from e

            if parse_method != "direct":
                logger.info(f"Pass {pass_number} JSON parsed using method: {parse_method}")

            # Parse confidence FIRST (so we can use global confidence as default for extractions)
            confidence = self._parse_confidence(data.get("confidence", {}))

            # Parse extractions (passing global confidence as default for per-extraction confidence)
            extractions = self._parse_extractions(
                data.get("extractions", []), default_confidence=confidence.overall
            )

            # Get entities discovered
            entities = set(data.get("entities_discovered", []))

            # Get changes made
            changes = data.get("changes_made", [])

            # Get reasoning
            reasoning = data.get("reasoning", "")

            # Get thinking (for Opus Pass 5)
            thinking = data.get("thinking", "")

            # Get context influence (v2.2.2+ - only in Pass 2+)
            context_influence = data.get("context_influence")

            # Get explicit questions for next pass (v2.3)
            next_pass_questions = data.get("next_pass_questions", [])

            # Get strategic questions for human (v3.1)
            strategic_questions = data.get("strategic_questions", [])

            # Four Valets v3.0 fields
            early_stop = bool(data.get("early_stop", False))
            early_stop_reason = data.get("early_stop_reason")
            needs_mousqueton = bool(data.get("needs_mousqueton", True))
            notes_used = data.get("notes_used", [])
            notes_ignored = data.get("notes_ignored", [])
            critique = data.get("critique")
            arbitrage = data.get("arbitrage")
            memory_hint = data.get("memory_hint")

            confidence_assessment = data.get("confidence_assessment")

            return PassResult(
                pass_number=pass_number,
                pass_type=pass_type,
                model_used=model_tier.value,
                model_id=model_id,
                extractions=extractions,
                action=data.get("action", "rien"),
                confidence=confidence,
                entities_discovered=entities,
                changes_made=changes,
                reasoning=reasoning,
                tokens_used=usage.get("total_tokens", 0),
                duration_ms=duration_ms,
                thinking=thinking,
                context_influence=context_influence,
                next_pass_questions=next_pass_questions,
                strategic_questions=strategic_questions,
                # Four Valets v3.0 fields
                early_stop=early_stop,
                early_stop_reason=early_stop_reason,
                needs_mousqueton=needs_mousqueton,
                notes_used=notes_used,
                notes_ignored=notes_ignored,
                critique=critique,
                arbitrage=arbitrage,
                memory_hint=memory_hint,
                confidence_assessment=confidence_assessment,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in Pass {pass_number}: {e}\nResponse: {response[:500]}")
            raise ParseError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            logger.error(f"Parse error in Pass {pass_number}: {e}", exc_info=True)
            raise ParseError(f"Failed to parse response: {e}") from e

    def _extract_json(self, response: str) -> str:
        """
        Extract JSON object from response text.

        Uses multiple strategies to find valid JSON:
        1. Look for ```json code blocks
        2. Look for ``` code blocks
        3. Find first { and last }
        4. Handle edge cases (empty response, text-only response)

        Args:
            response: Raw response text

        Returns:
            Extracted JSON string

        Raises:
            ParseError: If no valid JSON found
        """
        if not response or not response.strip():
            raise ParseError("Empty response from AI")

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
            # Skip language identifier if present (e.g., ```javascript)
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
            # Last resort: check if the response is just text without JSON
            # Log the actual response for debugging
            preview = response[:200].replace("\n", "\\n")
            logger.warning(f"No JSON braces found in response. Preview: {preview}...")
            raise ParseError(
                f"No JSON object found in response. Response starts with: {response[:100]}"
            )

        return response[json_start:json_end]

    def _parse_extractions(
        self, extractions_data: list, default_confidence: float = 0.8
    ) -> list[Extraction]:
        """
        Parse extractions list from JSON data.

        Args:
            extractions_data: List of extraction dicts from JSON
            default_confidence: Default confidence to use if not specified per-extraction
                               (typically the global analysis confidence)

        Returns:
            List of validated Extraction objects
        """
        extractions = []

        for ext_data in extractions_data:
            try:
                # Validate required fields (handle None values)
                info = (ext_data.get("info") or "").strip()
                if not info:
                    logger.warning("Skipping extraction with empty info")
                    continue

                # CRITICAL: Reject extractions targeting the owner
                # Use owner_names from config (defaults to Johan variations)
                note_cible = (ext_data.get("note_cible") or "").strip()
                if note_cible:
                    note_cible_lower = note_cible.lower()
                    if note_cible_lower in self.config.owner_names:
                        logger.warning(
                            f"Rejecting extraction targeting owner '{note_cible}': {info}"
                        )
                        continue

                # Determine if this extraction should be required based on type/importance
                # if not explicitly set
                ext_type = ext_data.get("type", "fait")
                importance = ext_data.get("importance", "moyenne")
                explicit_required = ext_data.get("required")

                # Auto-determine required if not explicitly set
                if explicit_required is None:
                    required = self._should_be_required(ext_type, importance)
                else:
                    required = bool(explicit_required)

                # Get confidence for this extraction (4 dimensions or single score)
                ext_confidence_data = ext_data.get("confidence")
                if ext_confidence_data is None:
                    # Use global confidence as default
                    ext_confidence = ExtractionConfidence.from_single_score(default_confidence)
                elif isinstance(ext_confidence_data, dict):
                    # New format: 4 dimensions
                    ext_confidence = ExtractionConfidence.from_dict(ext_confidence_data)
                elif isinstance(ext_confidence_data, (int, float)):
                    # Backwards compatibility: single score
                    ext_confidence = ExtractionConfidence.from_single_score(
                        float(ext_confidence_data)
                    )
                else:
                    ext_confidence = ExtractionConfidence.from_single_score(default_confidence)

                # Check for past dates and adjust confidence with nuanced rules (Option D)
                ext_date = ext_data.get("date")
                obsolete_date_reason = ""
                if ext_date and self._is_date_obsolete(ext_date):
                    ext_confidence, should_require, obsolete_date_reason = (
                        self._adjust_confidence_for_obsolete_date(
                            ext_confidence, ext_type, importance, info, ext_date
                        )
                    )
                    # Only override required if the adjustment says not to require
                    if not should_require:
                        required = False

                extraction = Extraction(
                    info=info,
                    type=ext_type,
                    importance=importance,
                    note_cible=ext_data.get("note_cible"),
                    note_action=ext_data.get("note_action", "enrichir"),
                    omnifocus=bool(ext_data.get("omnifocus", False)),
                    calendar=bool(ext_data.get("calendar", False)),
                    date=ext_date,
                    time=ext_data.get("time"),
                    timezone=ext_data.get("timezone"),
                    duration=ext_data.get("duration"),
                    required=required,
                    confidence=ext_confidence,
                    generic_title=bool(ext_data.get("generic_title", False)),
                )
                extractions.append(extraction)

            except Exception as e:
                logger.warning(f"Failed to parse extraction: {e}")
                continue

        return extractions

    def _parse_confidence(self, confidence_data: dict) -> DecomposedConfidence:
        """
        Parse confidence data into DecomposedConfidence.

        Args:
            confidence_data: Dict with confidence scores

        Returns:
            DecomposedConfidence object
        """
        # Handle both old (single score) and new (decomposed) formats
        if isinstance(confidence_data, (int, float)):
            return DecomposedConfidence.from_single_score(float(confidence_data))

        return DecomposedConfidence(
            entity_confidence=float(confidence_data.get("entity_confidence", 0.5)),
            action_confidence=float(confidence_data.get("action_confidence", 0.5)),
            extraction_confidence=float(confidence_data.get("extraction_confidence", 0.5)),
            completeness=float(confidence_data.get("completeness", 0.5)),
        )

    def _should_be_required(self, ext_type: str, importance: str) -> bool:
        """
        Determine if an extraction should be marked as required.

        An extraction is required if losing it would mean losing important
        information when archiving/deleting the email.

        Logic based on type and importance:
        - All deadlines are ALWAYS required (any importance)
        - High importance: decision, engagement, demande, montant, fait, evenement
        - Medium importance: engagement, demande (typically have implicit deadlines)

        Args:
            ext_type: Type of extraction (deadline, engagement, decision, etc.)
            importance: Importance level (haute, moyenne, basse)

        Returns:
            True if extraction should be required for safe archiving
        """
        ext_type = ext_type.lower()
        importance = importance.lower()

        # Deadlines are ALWAYS required regardless of importance
        if ext_type == "deadline":
            return True

        # High importance extractions
        if importance == "haute":
            return ext_type in {
                "decision",
                "engagement",
                "demande",
                "montant",
                "fait",
                "evenement",
            }

        # Medium importance - only engagements and demandes
        # (they typically imply follow-up actions)
        if importance == "moyenne":
            return ext_type in {"engagement", "demande"}

        # Low importance extractions are optional
        return False

    def _is_date_obsolete(self, date_str: str, days_threshold: int = 90) -> bool:
        """
        Check if a date is obsolete (more than N days in the past).

        Args:
            date_str: Date string in YYYY-MM-DD format
            days_threshold: Number of days after which a date is considered obsolete

        Returns:
            True if the date is more than days_threshold days in the past
        """
        if not date_str:
            return False

        try:
            date_obj = self._parse_date_string(date_str)
            if not date_obj:
                return False

            threshold_date = datetime.now(timezone.utc).date() - timedelta(days=days_threshold)
            return date_obj < threshold_date
        except Exception as e:
            logger.warning(f"Error checking if date is obsolete: {e}")
            return False

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Parse date string robustly handling multiple formats"""
        from dateutil import parser as date_parser

        try:
            # Try ISO format first
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        try:
            # Try robust parser
            dt = date_parser.parse(date_str, fuzzy=True)
            return dt.date()
        except (ValueError, TypeError):
            logger.debug(f"Could not parse date: {date_str}")
            return None

    def _get_date_age_days(self, date_str: str) -> int:
        """
        Calculate how many days ago a date was.

        Args:
            date_str: Date string to check

        Returns:
            Number of days in the past (negative if future), or 0 if parsing fails
        """
        date_obj = self._parse_date_string(date_str)
        if not date_obj:
            return 0

        today = datetime.now(timezone.utc).date()
        return (today - date_obj).days

    def _has_historical_keywords(self, info: str) -> bool:
        """
        Check if extraction info contains keywords indicating historical/contractual value.

        Args:
            info: The extraction info text

        Returns:
            True if historical keywords are found
        """
        info_lower = info.lower()
        return any(keyword in info_lower for keyword in HISTORICAL_KEYWORDS)

    def _adjust_confidence_for_obsolete_date(
        self,
        ext_confidence: ExtractionConfidence,
        ext_type: str,
        importance: str,
        info: str,
        date_str: str,
    ) -> tuple[ExtractionConfidence, bool, str]:
        """
        Adjust extraction confidence based on date obsolescence with nuanced rules (Option D).

        Rules:
        1. Types with intrinsic historical value (reference, montant, relation) → keep original
        2. Content with historical keywords → keep original
        3. High importance → reduce to 50% minimum
        4. Others → reduce to 20% minimum

        Args:
            ext_confidence: Original extraction confidence
            ext_type: Type of extraction (fait, evenement, reference, etc.)
            importance: Importance level (haute, moyenne, basse)
            info: The extraction info text
            date_str: The date string

        Returns:
            Tuple of (adjusted_confidence, should_require, reason)
        """
        age_days = self._get_date_age_days(date_str)

        # Date in the future or recent (< 90 days) → no adjustment needed
        if age_days < 90:
            return ext_confidence, True, ""

        # Rule 1: Types with intrinsic historical value → keep original confidence
        if ext_type in HISTORICAL_VALUE_TYPES:
            logger.debug(
                f"Keeping confidence for historical type '{ext_type}' despite old date ({age_days} days)"
            )
            return ext_confidence, True, f"historical_type:{ext_type}"

        # Rule 2: Historical keywords in content → keep original confidence
        if self._has_historical_keywords(info):
            logger.debug(
                f"Keeping confidence due to historical keywords in: {info[:50]}..."
            )
            return ext_confidence, True, "historical_keywords"

        # Rule 3: High importance → 50% minimum confidence
        if importance == "haute":
            min_confidence = 0.5
            adjusted = ExtractionConfidence(
                quality=max(ext_confidence.quality * 0.5, min_confidence),
                target_match=max(ext_confidence.target_match * 0.5, min_confidence),
                relevance=max(ext_confidence.relevance * 0.5, min_confidence),
                completeness=max(ext_confidence.completeness * 0.5, min_confidence),
            )
            logger.debug(
                f"Reduced confidence to 50% for high-importance extraction with old date ({age_days} days)"
            )
            return adjusted, False, "old_date_high_importance"

        # Rule 4: Others → 20% minimum confidence (allows human review)
        # Scale reduction based on age: 90-365 days → 40%, 1-3 years → 30%, >3 years → 20%
        if age_days < 365:
            reduction_factor = 0.4
        elif age_days < 1095:  # 3 years
            reduction_factor = 0.3
        else:
            reduction_factor = 0.2

        adjusted = ExtractionConfidence(
            quality=max(ext_confidence.quality * reduction_factor, 0.2),
            target_match=max(ext_confidence.target_match * reduction_factor, 0.2),
            relevance=max(ext_confidence.relevance * reduction_factor, 0.2),
            completeness=max(ext_confidence.completeness * reduction_factor, 0.2),
        )
        logger.debug(
            f"Reduced confidence to {reduction_factor*100:.0f}% for extraction with old date ({age_days} days)"
        )
        return adjusted, False, f"old_date_{age_days}d"

    def _collect_strategic_questions(
        self, passes: list[PassResult]
    ) -> list[dict[str, Any]]:
        """
        Collect and deduplicate strategic questions from all valets (v3.1).

        Strategic questions are questions that require human decision/reflection,
        not factual lookups. They are accumulated from all valets and deduplicated
        based on the question text.

        Args:
            passes: List of PassResult from the Four Valets pipeline

        Returns:
            Deduplicated list of strategic questions with source attribution
        """
        # Map valet names by pass number
        valet_names = {1: "grimaud", 2: "bazin", 3: "planchet", 4: "mousqueton"}

        all_questions: list[dict[str, Any]] = []
        seen_questions: set[str] = set()

        for p in passes:
            valet_name = valet_names.get(p.pass_number, f"pass_{p.pass_number}")

            for sq in p.strategic_questions:
                # Handle both dict and raw string formats
                if isinstance(sq, dict):
                    question_text = sq.get("question", "")
                    # Skip if empty or already seen
                    if not question_text or question_text.lower() in seen_questions:
                        continue

                    seen_questions.add(question_text.lower())

                    # Normalize the question structure
                    normalized = {
                        "question": question_text,
                        "target_note": sq.get("target_note"),
                        "category": sq.get("category", "decision"),
                        "context": sq.get("context", ""),
                        "source": sq.get("source", valet_name),
                    }
                    all_questions.append(normalized)
                elif isinstance(sq, str) and sq.strip():
                    # Handle raw string questions (legacy or simplified format)
                    if sq.lower() in seen_questions:
                        continue

                    seen_questions.add(sq.lower())
                    all_questions.append({
                        "question": sq,
                        "target_note": None,
                        "category": "decision",
                        "context": "",
                        "source": valet_name,
                    })

        if all_questions:
            logger.info(
                f"Collected {len(all_questions)} strategic questions from "
                f"{len([p for p in passes if p.strategic_questions])} valets"
            )

        return all_questions

    def _calculate_event_age_days(self, event: PerceivedEvent) -> int:
        """
        Calculate the age of an event in days.

        Uses occurred_at (original event date) if available,
        otherwise falls back to received_at.

        Args:
            event: The event to check

        Returns:
            Age in days (0 if event is from today)
        """
        now = datetime.now(timezone.utc)

        # Get event date and ensure timezone awareness
        event_date = getattr(event, "occurred_at", None) or getattr(event, "received_at", None)

        if event_date is None:
            return 0

        # Convert string to datetime if needed
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Could not parse event date: {event_date}")
                return 0

        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)

        age = now - event_date
        return max(0, age.days)

    # --- Critical content detection (triggers Opus escalation) ---

    # Threshold for high-stakes amounts (triggers Opus escalation)
    HIGH_AMOUNT_THRESHOLD = 1000  # EUR

    def _is_critical_content(self, event: PerceivedEvent) -> tuple[bool, Optional[str]]:
        """
        Check if content is critical and requires Opus-level analysis.

        Critical content includes:
        - Legal/contractual documents (bail, contrat, facture, etc.)
        - Financial documents (bilan, rapport financier, etc.)
        - Sensitive content (conflicts, HR issues, negotiations, etc.)
        - High amounts (> 1000€)

        Args:
            event: The event to check

        Returns:
            Tuple of (is_critical, reason)
        """
        title = (getattr(event, "title", "") or "").lower()
        content = (getattr(event, "content", "") or "").lower()
        full_text = f"{title} {content}"

        # Check for proper name exclusions (e.g., "Le Bail" = family name, not legal document)
        has_exclusion = any(excl in full_text for excl in PROPER_NAME_EXCLUSIONS)

        # Check 1: Legal/contractual content (skip if matches a proper name exclusion)
        if not has_exclusion:
            is_legal = any(ind in full_text for ind in self.LEGAL_INDICATORS)
            if is_legal:
                matched = next((ind for ind in self.LEGAL_INDICATORS if ind in full_text), "unknown")
                logger.info(f"Critical content detected: legal/contractual (matched: '{matched}')")
                return True, f"legal_contractual:{matched}"
        else:
            # Log that we skipped due to proper name
            logger.debug(f"Skipped legal/contractual check due to proper name exclusion in: {title[:50]}")

        # Check 2: Financial documents
        is_financial = any(ind in full_text for ind in self.FINANCIAL_INDICATORS)
        if is_financial:
            matched = next((ind for ind in self.FINANCIAL_INDICATORS if ind in full_text), "unknown")
            logger.info(f"Critical content detected: financial document (matched: '{matched}')")
            return True, f"financial_document:{matched}"

        # Check 3: Sensitive content (conflicts, HR, negotiations, confidential)
        # First, check if the sensitive word is just part of a standard email disclaimer
        has_disclaimer = any(pattern in full_text for pattern in EMAIL_DISCLAIMER_PATTERNS)
        is_sensitive = any(ind in full_text for ind in self.SENSITIVE_INDICATORS)
        if is_sensitive:
            matched = next((ind for ind in self.SENSITIVE_INDICATORS if ind in full_text), "unknown")
            # Skip if the match is likely from an email footer disclaimer
            if has_disclaimer and matched in ("confidential", "confidentiel"):
                logger.debug(f"Skipped sensitive content detection - '{matched}' appears in email disclaimer")
            else:
                logger.info(f"Critical content detected: sensitive (matched: '{matched}')")
                return True, f"sensitive:{matched}"

        # Check 4: High amounts (> 1000€)
        amount = self._extract_highest_amount(full_text)
        if amount and amount > self.HIGH_AMOUNT_THRESHOLD:
            logger.info(f"Critical content detected: high amount ({amount}€ > {self.HIGH_AMOUNT_THRESHOLD}€)")
            return True, f"high_amount:{amount}€"

        return False, None

    def _extract_highest_amount(self, text: str) -> Optional[float]:
        """
        Extract the highest monetary amount from text.

        Handles formats like:
        - 1500€, 1 500€, 1500 €
        - 1500 euros, 1 500 EUR
        - 1,500.00€ (US format)
        - 1.500,00€ (EU format)

        Args:
            text: Text to search for amounts

        Returns:
            Highest amount found, or None if no amounts found
        """
        import re

        amounts = []

        # Pattern for amounts with € or euros/EUR
        patterns = [
            r'(\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?|eur)\b',
            r'(?:€|euros?|eur)\s*(\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})?)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Normalize the number
                    num_str = match.strip()
                    # Remove spaces
                    num_str = num_str.replace(" ", "")
                    # Handle EU vs US format
                    if "," in num_str and "." in num_str:
                        # Both present: determine which is decimal
                        if num_str.rfind(",") > num_str.rfind("."):
                            # EU format: 1.500,00
                            num_str = num_str.replace(".", "").replace(",", ".")
                        else:
                            # US format: 1,500.00
                            num_str = num_str.replace(",", "")
                    elif "," in num_str:
                        # Could be EU decimal (1500,00) or thousand sep (1,500)
                        if len(num_str.split(",")[-1]) == 2:
                            num_str = num_str.replace(",", ".")
                        else:
                            num_str = num_str.replace(",", "")

                    amounts.append(float(num_str))
                except ValueError:
                    continue

        return max(amounts) if amounts else None

    # --- Ephemeral content detection helpers ---

    def _is_protected_document(self, full_text: str, from_person: str) -> bool:
        """
        Check if content is a protected document that should NEVER be ephemeral.

        Protected documents include financial reports, legal contracts, invoices, etc.

        Args:
            full_text: Combined title and content in lowercase
            from_person: Sender identifier in lowercase

        Returns:
            True if this is a protected document
        """
        is_financial = any(ind in full_text for ind in self.FINANCIAL_INDICATORS)
        is_legal = any(ind in full_text for ind in self.LEGAL_INDICATORS)

        if is_financial or is_legal:
            matched_ind = next(
                (
                    ind
                    for ind in self.FINANCIAL_INDICATORS | self.LEGAL_INDICATORS
                    if ind in full_text
                ),
                "unknown",
            )
            logger.info(
                f"Protected document detected (NOT ephemeral): matched='{matched_ind}' "
                f"in from='{from_person}'"
            )
            return True
        return False

    def _is_newsletter(self, from_person: str, title: str) -> bool:
        """
        Check if content is a newsletter or digest.

        Args:
            from_person: Sender identifier in lowercase
            title: Email title in lowercase

        Returns:
            True if this appears to be a newsletter/digest
        """
        return any(ind in from_person or ind in title for ind in self.NEWSLETTER_INDICATORS)

    def _is_otp_code(self, full_text: str, sender_email: str) -> bool:
        """
        Check if content is an OTP or verification code.

        Args:
            full_text: Combined title and content in lowercase
            sender_email: Sender email address in lowercase

        Returns:
            True if this appears to be an OTP/verification code
        """
        return any(ind in full_text or ind in sender_email for ind in self.OTP_INDICATORS)

    def _extract_dates_from_extractions(
        self,
        extractions: list[Extraction],
        event_date: datetime,
    ) -> tuple[list[datetime], bool]:
        """
        Extract dates from extraction info and detect time-bound content.

        Args:
            extractions: List of extractions to analyze
            event_date: The event date for year inference

        Returns:
            Tuple of (list of parsed dates, has_time_bound_content flag)
        """
        dates_found: list[datetime] = []
        has_time_bound_content = False

        for ext in extractions:
            # Check if extraction type suggests time-bound content
            if ext.type in self.TIME_BOUND_TYPES:
                has_time_bound_content = True

            # Try to extract dates from the extraction info
            info = ext.info or ""

            for pattern in self.DATE_PATTERNS:
                matches = re.findall(pattern, info.lower())
                for match in matches:
                    try:
                        date_str = match
                        if not re.search(r"\d{4}", date_str):
                            date_str = f"{date_str} {event_date.year}"

                        parsed = date_parser.parse(date_str, fuzzy=True, dayfirst=True)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        dates_found.append(parsed)
                    except (ValueError, TypeError):
                        pass

            # Also check the extraction's explicit date field
            if ext.date:
                try:
                    parsed = date_parser.parse(ext.date, fuzzy=True)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    dates_found.append(parsed)
                except (ValueError, TypeError):
                    pass

        return dates_found, has_time_bound_content

    def _check_past_dates(
        self,
        dates_found: list[datetime],
        now: datetime,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if all found dates are in the past.

        Args:
            dates_found: List of parsed dates
            now: Current datetime for comparison

        Returns:
            Tuple of (all_past, reason_string or None)
        """
        if not dates_found:
            return False, None

        all_past = all(d < now for d in dates_found)
        if all_past:
            oldest = min(dates_found)
            days_ago = (now - oldest).days
            return True, f"{oldest.strftime('%Y-%m-%d')} ({days_ago} days ago)"
        return False, None

    def _is_ephemeral_content(
        self,
        extractions: list[Extraction],
        event: PerceivedEvent,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if email contains ephemeral content with no lasting value.

        Detects:
        1. Newsletters/digests (periodic content aggregations)
        2. OTP/verification codes (always ephemeral)
        3. Event invitations with dates that have passed
        4. Time-limited offers that have expired

        NEVER marks as ephemeral:
        - Financial documents (bilans, rapports financiers, etc.)
        - Legal documents (contrats, factures, etc.)
        - Corporate documents (statuts, PV, etc.)

        Args:
            extractions: List of extractions from the email
            event: The event being analyzed (for email date context)

        Returns:
            Tuple of (is_ephemeral, reason)
        """
        # Extract text for analysis
        from_person = (getattr(event, "from_person", "") or "").lower()
        sender_email = from_person
        title = (getattr(event, "title", "") or "").lower()
        content = getattr(event, "content", "") or ""
        full_text = f"{title} {content}".lower()

        # Check 1: Protected documents are NEVER ephemeral
        if self._is_protected_document(full_text, from_person):
            return False, None

        # Check 2: Newsletters/digests
        is_newsletter = self._is_newsletter(from_person, title)
        logger.info(
            f"Ephemeral check: from_person='{from_person}', title='{title[:50]}', "
            f"is_newsletter={is_newsletter}"
        )
        if is_newsletter:
            logger.info(f"Detected newsletter/digest: from_person='{from_person}'")
            return True, "newsletter/digest (periodic content, no lasting value)"

        # Check 3: OTP/verification codes
        if self._is_otp_code(full_text, sender_email):
            return True, "OTP/verification code (expired, no lasting value)"

        # Check 4: Past events/invitations
        now = datetime.now(timezone.utc)
        event_date = getattr(event, "occurred_at", None) or getattr(event, "received_at", now)
        dates_found, has_time_bound_content = self._extract_dates_from_extractions(
            extractions, event_date
        )

        # Check time-bound extraction types (evenement, deadline, fait)
        if has_time_bound_content and dates_found:
            all_past, date_info = self._check_past_dates(dates_found, now)
            if all_past:
                return True, f"event/offer dated {date_info}"

        # Check event indicators in content
        has_event_indicator = any(ind in full_text for ind in self.EVENT_INDICATORS)
        if has_event_indicator and dates_found:
            all_past, date_info = self._check_past_dates(dates_found, now)
            if all_past:
                return True, f"invitation/offer dated {date_info}"

        return False, None

    def _apply_age_adjustments(
        self,
        action: str,
        extractions: list[Extraction],
        age_days: int,
        event: PerceivedEvent,
    ) -> tuple[str, list[Extraction], Optional[str]]:
        """
        Apply age-based adjustments to action and extractions.

        Rules:
        - Emails > 90 days with flag/queue: downgrade to archive/delete
        - Promotional emails > 90 days without extractions: delete
        - Emails > 365 days: Remove OmniFocus tasks (too old for follow-up)
        - Note enrichments are always kept (historical value)

        Args:
            action: Proposed action
            extractions: Proposed extractions
            age_days: Event age in days
            event: The event being analyzed (for sender detection)

        Returns:
            Tuple of (adjusted_action, adjusted_extractions, adjustment_reason)
        """
        adjustment_reason = None
        adjusted_action = action
        adjusted_extractions = extractions

        # Check for valuable extractions (any extraction targeting a note has historical value)
        # An extraction with note_cible is valuable regardless of omnifocus flag
        has_valuable_extractions = any(ext.note_cible for ext in extractions)

        # Rule 1: Downgrade "flag" or "queue" for old emails
        # - Both require active follow-up which is inappropriate for old emails
        # - If has valuable extractions → archive (historical value)
        # - If no extractions → delete (truly obsolete, no point keeping)
        if age_days > OLD_EMAIL_THRESHOLD_DAYS and action in ("flag", "queue"):
            if has_valuable_extractions:
                adjusted_action = "archive"
                adjustment_reason = (
                    f"Action downgraded from '{action}' to 'archive' "
                    f"(email is {age_days} days old, but has historical value)"
                )
            else:
                adjusted_action = "delete"
                adjustment_reason = (
                    f"Action downgraded from '{action}' to 'delete' "
                    f"(email is {age_days} days old, no valuable extractions)"
                )
            logger.info(adjustment_reason)

        # Rule 2: Delete emails with ephemeral content (past events, newsletters)
        # - Event invitations with dates in the past
        # - Newsletters/digests (periodic content with no lasting value)
        # - Time-limited offers that have expired
        is_ephemeral, ephemeral_reason = self._is_ephemeral_content(adjusted_extractions, event)
        if age_days > OLD_EMAIL_THRESHOLD_DAYS and adjusted_action == "archive" and is_ephemeral:
            adjusted_action = "delete"
            # Clear extractions since ephemeral content has no lasting value
            adjusted_extractions = []
            adjustment_reason = (
                f"Ephemeral content upgraded to 'delete' "
                f"(email is {age_days} days old, {ephemeral_reason})"
            )
            logger.info(adjustment_reason)

        # Rule 3: Remove OmniFocus tasks for very old emails
        if age_days > VERY_OLD_EMAIL_THRESHOLD_DAYS:
            original_count = len(extractions)
            adjusted_extractions = []
            for ext in extractions:
                if ext.omnifocus:
                    logger.info(
                        f"Removing OmniFocus task for old email ({age_days} days): "
                        f"{ext.info[:50]}..."
                    )
                    # Keep the extraction but remove OmniFocus flag
                    adjusted_extractions.append(
                        Extraction(
                            info=ext.info,
                            type=ext.type,
                            importance=ext.importance,
                            note_cible=ext.note_cible,
                            note_action=ext.note_action,
                            omnifocus=False,  # Remove OmniFocus
                            calendar=ext.calendar,
                            date=ext.date,
                            time=ext.time,
                            timezone=ext.timezone,
                            duration=ext.duration,
                            required=ext.required,
                            confidence=ext.confidence,
                        )
                    )
                else:
                    adjusted_extractions.append(ext)

            if adjustment_reason:
                adjustment_reason += f"; OmniFocus tasks disabled for {original_count - len([e for e in adjusted_extractions if e.omnifocus])} extractions"
            elif original_count != len([e for e in adjusted_extractions if e.omnifocus]):
                adjustment_reason = (
                    f"OmniFocus tasks disabled (email is {age_days} days old, "
                    f"threshold: {VERY_OLD_EMAIL_THRESHOLD_DAYS})"
                )

        return adjusted_action, adjusted_extractions, adjustment_reason

    async def _build_result(
        self,
        pass_history: list[PassResult],
        start_time: float,
        total_tokens: int,
        stop_reason: str,
        escalated: bool,
        analysis_context: AnalysisContext,
        event: PerceivedEvent,
        context: Optional["StructuredContext"] = None,
    ) -> MultiPassResult:
        """
        Build the final MultiPassResult.

        Args:
            pass_history: All pass results
            start_time: Analysis start time
            total_tokens: Total tokens used
            stop_reason: Reason for stopping
            escalated: Whether model was escalated
            analysis_context: Analysis context
            event: Original event (for age-based adjustments)
            context: Retrieved context for transparency (v2.2.2+)

        Returns:
            MultiPassResult
        """
        last_pass = pass_history[-1]
        total_duration = (time.time() - start_time) * 1000

        # Check for high-stakes
        high_stakes_detected = is_high_stakes(
            last_pass.extractions,
            analysis_context,
            self.config,
        )

        # Collect all entities
        all_entities: set[str] = set()
        for p in pass_history:
            all_entities.update(p.entities_discovered)

        # Apply age-based adjustments
        age_days = self._calculate_event_age_days(event)
        logger.info(f"Age-based check: age_days={age_days}, action={last_pass.action}")
        adjusted_action, adjusted_extractions, age_adjustment = self._apply_age_adjustments(
            last_pass.action,
            last_pass.extractions,
            age_days,
            event,
        )
        if age_adjustment:
            logger.info(f"Age adjustment applied: {age_adjustment}")

        # Run coherence pass on adjusted extractions
        # This validates note targets, detects duplicates, and suggests sections
        coherence_validated = False
        coherence_corrections = 0
        coherence_duplicates = 0
        coherence_confidence = 1.0
        coherence_warnings: list[dict] = []

        if adjusted_extractions:
            validated_extractions, coherence_result = await self._run_coherence_pass(
                adjusted_extractions, event
            )
            if coherence_result is not None:
                adjusted_extractions = validated_extractions
                coherence_validated = True
                coherence_corrections = coherence_result.coherence_summary.corrected
                coherence_duplicates = coherence_result.coherence_summary.duplicates_detected
                coherence_confidence = coherence_result.coherence_confidence
                coherence_warnings = [
                    {"type": w.type, "index": w.extraction_index, "message": w.message}
                    for w in coherence_result.warnings
                ]
                total_tokens += coherence_result.tokens_used

        # Update stop reason if adjustments were made
        final_stop_reason = stop_reason
        if age_adjustment:
            final_stop_reason = f"{stop_reason}; {age_adjustment}"
        if coherence_validated and coherence_corrections > 0:
            final_stop_reason = (
                f"{final_stop_reason}; coherence_pass: {coherence_corrections} corrected"
            )

        # Extract context_influence from last contextual pass (v2.2.2+)
        last_context_influence: Optional[dict[str, Any]] = None
        for p in reversed(pass_history):
            if p.context_influence is not None:
                last_context_influence = p.context_influence
                break

        # Serialize retrieved context for transparency (v2.2.2+)
        serialized_context: Optional[dict[str, Any]] = None
        if context is not None:
            serialized_context = {
                "entities_searched": context.query_entities,
                "sources_searched": context.sources_searched,
                "total_results": context.total_results,
                "notes": [
                    {
                        "note_id": n.note_id,
                        "title": n.title,
                        "note_type": n.note_type,
                        "summary": n.summary[:200] if n.summary else "",
                        "relevance": round(n.relevance, 2),
                        "tags": n.tags,
                        "path": getattr(n, "path", ""),
                    }
                    for n in context.notes
                ],
                "calendar": [
                    {
                        "event_id": e.event_id,
                        "title": e.title,
                        "date": e.date,
                        "time": e.time,
                        "relevance": round(e.relevance, 2),
                    }
                    for e in context.calendar
                ],
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "title": t.title,
                        "project": t.project,
                        "due_date": t.due_date,
                        "relevance": round(t.relevance, 2),
                    }
                    for t in context.tasks
                ],
                "entity_profiles": {
                    name: {
                        "canonical_name": p.canonical_name,
                        "entity_type": p.entity_type,
                        "role": p.role,
                        "relationship": p.relationship,
                        "key_facts": p.key_facts[:3] if p.key_facts else [],
                    }
                    for name, p in context.entity_profiles.items()
                },
                "conflicts": [
                    {
                        "type": c.conflict_type,
                        "description": c.description,
                        "severity": c.severity,
                    }
                    for c in context.conflicts
                ],
            }

        # Get canevas status from template renderer (v3.2)
        canevas_status_dict = None
        if self.template_renderer:
            canevas_status = self.template_renderer.get_canevas_status()
            if canevas_status:
                canevas_status_dict = canevas_status.to_dict()

        return MultiPassResult(
            extractions=adjusted_extractions,
            action=adjusted_action,
            confidence=last_pass.confidence,
            entities_discovered=all_entities,
            passes_count=len(pass_history),
            total_duration_ms=total_duration,
            total_tokens=total_tokens,
            final_model=last_pass.model_used,
            escalated=escalated,
            pass_history=pass_history,
            stop_reason=final_stop_reason,
            high_stakes=high_stakes_detected or analysis_context.high_stakes,
            # Coherence validation metadata
            coherence_validated=coherence_validated,
            coherence_corrections=coherence_corrections,
            coherence_duplicates_detected=coherence_duplicates,
            coherence_confidence=coherence_confidence,
            coherence_warnings=coherence_warnings,
            # Retrieved context for transparency (v2.2.2+)
            retrieved_context=serialized_context,
            context_influence=last_context_influence,
            # Canevas status v3.2
            canevas_status=canevas_status_dict,
        )

    # ==================== Four Valets v3.0 ====================

    async def _run_four_valets_pipeline(
        self,
        event: PerceivedEvent,
        sender_importance: str = "normal",
    ) -> MultiPassResult:
        """
        Four Valets v3.0 pipeline.

        Pipeline:
        1. Grimaud (Pass 1) — Extraction silencieuse
        2. Bazin (Pass 2) — Enrichissement contextuel
        3. Planchet (Pass 3) — Critique et validation
        4. Mousqueton (Pass 4) — Arbitrage final (si nécessaire)

        Args:
            event: Perceived event to analyze
            sender_importance: Sender importance level

        Returns:
            MultiPassResult with extractions and metadata
        """
        start_time = time.time()
        total_tokens = 0
        passes: list[PassResult] = []
        context: Optional[StructuredContext] = None

        logger.info(f"[PERF] Starting Four Valets analysis for event {event.event_id}")

        # === DETECT EPHEMERAL CONTENT (from email_adapter) ===
        # Ephemeral emails: noreply, notifications, newsletters, automated messages
        # These don't need Opus escalation and can use lower confidence thresholds
        is_ephemeral = event.metadata.get("is_ephemeral", False)
        ephemeral_reason = event.metadata.get("ephemeral_reason")
        if is_ephemeral:
            logger.info(f"Ephemeral content detected: {ephemeral_reason} → Fast path enabled")

        # === DETECT CRITICAL CONTENT (triggers Opus escalation) ===
        # Critical content: legal/contractual, financial documents, high amounts (> 1000€)
        # Note: Critical overrides ephemeral — we want careful analysis for legal docs
        is_critical, critical_reason = self._is_critical_content(event)
        if is_critical:
            logger.info(f"Critical content detected: {critical_reason} → Opus escalation enabled")
            is_ephemeral = False  # Critical content is never treated as ephemeral

        # === GRIMAUD (Pass 1) — Extraction silencieuse ===
        grimaud_start = time.time()
        grimaud = await self._run_grimaud(event)
        passes.append(grimaud)
        total_tokens += grimaud.tokens_used
        logger.info(f"[PERF] Grimaud: {(time.time() - grimaud_start)*1000:.0f}ms ({grimaud.model_used})")

        # Check if Grimaud flagged the content as critical/sensitive
        # This allows the AI to signal critical content even if not auto-detected
        grimaud_flagged_critical = getattr(grimaud, "is_critical", False) or (
            grimaud.confidence_assessment
            and grimaud.confidence_assessment.get("is_critical", False)
        )
        if grimaud_flagged_critical and not is_critical:
            is_critical = True
            critical_reason = "grimaud_flagged"
            logger.info("Grimaud flagged content as critical → Opus escalation enabled")

        # Check for early stop (ephemeral content at 95%+ confidence, or old newsletter)
        # Note: is_ephemeral from adapter lowers the threshold to 80%
        if self._should_early_stop(grimaud, event, is_ephemeral):
            total_ms = (time.time() - start_time) * 1000
            logger.info(f"[PERF] Total (early stop Grimaud): {total_ms:.0f}ms, {total_tokens} tokens")
            logger.info(f"Grimaud early stop: {grimaud.early_stop_reason}")
            return await self._finalize_four_valets(
                passes=passes,
                event=event,
                start_time=start_time,
                total_tokens=total_tokens,
                stopped_at="grimaud",
                stop_reason=f"early_stop: {grimaud.early_stop_reason}",
                context=None,
                sender_importance=sender_importance,
            )

        # Get context for Bazin
        # Skip context search for ephemeral content (no point searching notes for spam/newsletters)
        if self.context_searcher and grimaud.entities_discovered and not is_ephemeral:
            context_start = time.time()
            logger.debug(f"Searching context for entities: {grimaud.entities_discovered}")
            context = await self.context_searcher.search_for_entities(
                list(grimaud.entities_discovered),
                sender_email=getattr(event, "from_person", None),
            )
            logger.info(f"[PERF] Context search: {(time.time() - context_start)*1000:.0f}ms ({len(context.notes) if context else 0} notes)")
        elif is_ephemeral:
            logger.info("[PERF] Context search skipped (ephemeral content)")

        # === BAZIN (Pass 2) — Enrichissement contextuel ===
        bazin_start = time.time()
        bazin = await self._run_bazin(event, grimaud, context, is_critical, is_ephemeral)
        passes.append(bazin)
        total_tokens += bazin.tokens_used
        logger.info(f"[PERF] Bazin: {(time.time() - bazin_start)*1000:.0f}ms ({bazin.model_used})")

        # === PLANCHET (Pass 3) — Critique et validation ===
        planchet_start = time.time()
        planchet = await self._run_planchet(event, passes, context, is_critical, is_ephemeral)
        passes.append(planchet)
        total_tokens += planchet.tokens_used
        logger.info(f"[PERF] Planchet: {(time.time() - planchet_start)*1000:.0f}ms ({planchet.model_used})")

        # Check if Planchet can conclude without Mousqueton
        # Note: is_ephemeral lowers the threshold to 80%
        if self._planchet_can_conclude(planchet, is_ephemeral):
            total_ms = (time.time() - start_time) * 1000
            logger.info(f"[PERF] Total (stopped at Planchet): {total_ms:.0f}ms, {total_tokens} tokens")
            logger.info(f"Planchet concludes at {planchet.confidence.overall:.0%} confidence")
            return await self._finalize_four_valets(
                passes=passes,
                event=event,
                start_time=start_time,
                total_tokens=total_tokens,
                stopped_at="planchet",
                stop_reason=f"planchet_confident ({planchet.confidence.overall:.0%})",
                context=context,
                sender_importance=sender_importance,
            )

        # === MOUSQUETON (Pass 4) — Arbitrage final ===
        mousqueton_start = time.time()
        mousqueton = await self._run_mousqueton(event, passes, context, is_critical, is_ephemeral)
        passes.append(mousqueton)
        total_tokens += mousqueton.tokens_used
        logger.info(f"[PERF] Mousqueton: {(time.time() - mousqueton_start)*1000:.0f}ms ({mousqueton.model_used})")

        total_ms = (time.time() - start_time) * 1000
        logger.info(f"[PERF] Total Four Valets: {total_ms:.0f}ms, {total_tokens} tokens")

        return await self._finalize_four_valets(
            passes=passes,
            event=event,
            start_time=start_time,
            total_tokens=total_tokens,
            stopped_at="mousqueton",
            stop_reason="mousqueton_arbitrage",
            context=context,
            sender_importance=sender_importance,
        )

    async def _run_grimaud(self, event: PerceivedEvent) -> PassResult:
        """
        Execute Grimaud (Pass 1) — Extraction silencieuse.

        Like Athos's silent servant, Grimaud extracts raw information
        without context or commentary.

        Uses prompt caching for the static system prompt (~70% of tokens).
        """
        # Use split rendering for cache optimization
        split_prompt = self.template_renderer.render_grimaud_split(
            event=event,
            max_content_chars=self.config.four_valets.grimaud_max_chars,
        )
        model_tier = self._get_valet_model("grimaud")

        result = await self._call_model_with_cache(
            system_prompt=split_prompt.system,
            user_prompt=split_prompt.user,
            model_tier=model_tier,
            pass_number=1,
            pass_type=PassType.GRIMAUD,
        )
        result.valet = ValetType.GRIMAUD
        return result

    async def _run_bazin(
        self,
        event: PerceivedEvent,
        grimaud: PassResult,
        context: Optional[StructuredContext],
        is_critical_content: bool = False,
        is_ephemeral: bool = False,
    ) -> PassResult:
        """
        Execute Bazin (Pass 2) — Enrichissement contextuel.

        Like Aramis's pious servant, Bazin adds wisdom and context
        from the PKM knowledge base.

        Uses prompt caching for the static system prompt (~60% of tokens).
        """
        # Use split rendering for cache optimization
        split_prompt = self.template_renderer.render_bazin_split(
            event=event,
            grimaud_result=grimaud.to_dict(),
            context=context,
            max_content_chars=self.config.four_valets.bazin_max_chars,
            max_context_notes=self.config.four_valets.bazin_max_notes,
        )
        # Pass Grimaud's confidence for adaptive escalation
        # Critical content escalates directly to Opus
        # Ephemeral content blocks Opus escalation
        model_tier = self._get_valet_model(
            "bazin", grimaud.confidence.overall, is_critical_content, is_ephemeral
        )

        result = await self._call_model_with_cache(
            system_prompt=split_prompt.system,
            user_prompt=split_prompt.user,
            model_tier=model_tier,
            pass_number=2,
            pass_type=PassType.BAZIN,
        )
        result.valet = ValetType.BAZIN
        return result

    async def _run_planchet(
        self,
        event: PerceivedEvent,
        previous_passes: list[PassResult],
        context: Optional[StructuredContext],
        is_critical_content: bool = False,
        is_ephemeral: bool = False,
    ) -> PassResult:
        """
        Execute Planchet (Pass 3) — Critique et validation.

        Like d'Artagnan's resourceful servant, Planchet questions
        everything and validates the extractions.

        Uses prompt caching for the static system prompt (~65% of tokens).
        """
        grimaud = previous_passes[0]
        bazin = previous_passes[1] if len(previous_passes) > 1 else grimaud

        # Use split rendering for cache optimization
        split_prompt = self.template_renderer.render_planchet_split(
            event=event,
            grimaud_result=grimaud.to_dict(),
            bazin_result=bazin.to_dict(),
            context=context,
            max_content_chars=getattr(self.config.four_valets, "planchet_max_chars", 8000),
        )
        # Pass Bazin's confidence for adaptive escalation
        # Critical content escalates directly to Opus
        # Ephemeral content blocks Opus escalation
        model_tier = self._get_valet_model(
            "planchet", bazin.confidence.overall, is_critical_content, is_ephemeral
        )

        result = await self._call_model_with_cache(
            system_prompt=split_prompt.system,
            user_prompt=split_prompt.user,
            model_tier=model_tier,
            pass_number=3,
            pass_type=PassType.PLANCHET,
        )
        result.valet = ValetType.PLANCHET
        return result

    async def _run_mousqueton(
        self,
        event: PerceivedEvent,
        previous_passes: list[PassResult],
        context: Optional[StructuredContext],
        is_critical_content: bool = False,
        is_ephemeral: bool = False,
    ) -> PassResult:
        """
        Execute Mousqueton (Pass 4) — Arbitrage final.

        Like Porthos's practical servant, Mousqueton makes the final
        decision when there's disagreement between the valets.

        Uses prompt caching for the static system prompt (~50% of tokens).
        """
        grimaud = previous_passes[0]
        bazin = previous_passes[1] if len(previous_passes) > 1 else grimaud
        planchet = previous_passes[2] if len(previous_passes) > 2 else bazin

        # Use split rendering for cache optimization
        split_prompt = self.template_renderer.render_mousqueton_split(
            event=event,
            grimaud_result=grimaud.to_dict(),
            bazin_result=bazin.to_dict(),
            planchet_result=planchet.to_dict(),
            context=context,
        )
        # Pass Planchet's confidence for adaptive escalation (Sonnet → Opus if needed)
        # Critical content escalates directly to Opus
        # Ephemeral content blocks Opus escalation
        model_tier = self._get_valet_model(
            "mousqueton", planchet.confidence.overall, is_critical_content, is_ephemeral
        )

        result = await self._call_model_with_cache(
            system_prompt=split_prompt.system,
            user_prompt=split_prompt.user,
            model_tier=model_tier,
            pass_number=4,
            pass_type=PassType.MOUSQUETON,
        )
        result.valet = ValetType.MOUSQUETON
        return result

    def _should_early_stop(
        self,
        grimaud: PassResult,
        event: Optional[PerceivedEvent] = None,
        is_ephemeral: bool = False,
    ) -> bool:
        """
        Check if Grimaud requests early stop.

        Early stop is triggered for ephemeral content (OTP codes, newsletters)
        when Grimaud is highly confident (>95%) that the email should be deleted.

        Additionally, very old newsletters (>1 year) trigger early stop even without
        Grimaud explicitly requesting it, as they have no residual value.

        Args:
            grimaud: Result from Grimaud pass
            event: Original event (for age calculation)
            is_ephemeral: If True (from email_adapter), use lower threshold (80%)
        """
        # Use lower threshold for emails detected as ephemeral by adapter
        # This saves expensive escalations for obvious spam/notifications
        threshold = 0.80 if is_ephemeral else self.config.four_valets.grimaud_early_stop_confidence

        # Standard early stop: Grimaud requests it with high confidence
        if (
            grimaud.early_stop
            and grimaud.action == "delete"
            and grimaud.confidence.overall >= threshold
        ):
            return True

        # Fast path for ephemeral content: early stop even without explicit early_stop flag
        # if Grimaud recommends delete/archive with sufficient confidence
        if is_ephemeral and grimaud.action in ("delete", "archive") and grimaud.confidence.overall >= threshold:
            grimaud.early_stop = True
            grimaud.early_stop_reason = grimaud.early_stop_reason or "ephemeral_fast_path"
            logger.info(f"Early stop forced: ephemeral content ({grimaud.confidence.overall:.0%} >= {threshold:.0%})")
            return True

        # Enhanced early stop: Very old newsletters (>1 year) → DELETE directly
        # Even if Grimaud didn't set early_stop, save the escalation cost
        if event and grimaud.action == "delete":
            age_days = self._calculate_event_age_days(event)
            from_person = getattr(event, "from_person", "") or ""
            title = getattr(event, "title", "") or ""
            is_newsletter = self._is_newsletter(from_person.lower(), title.lower())

            if is_newsletter and age_days > 365:
                # Force early stop for very old newsletters
                grimaud.early_stop = True
                grimaud.early_stop_reason = grimaud.early_stop_reason or "old_newsletter"
                logger.info(f"Early stop forced: old newsletter ({age_days} days)")
                return True

        return False

    def _planchet_can_conclude(self, planchet: PassResult, is_ephemeral: bool = False) -> bool:
        """
        Check if Planchet can conclude without Mousqueton.

        Planchet can conclude if:
        - needs_mousqueton is False
        - confidence is above threshold (90%, or 80% for ephemeral content)

        Args:
            planchet: Result from Planchet pass
            is_ephemeral: If True, use lower threshold (80%) for ephemeral content
        """
        # Use lower threshold for ephemeral content
        threshold = 0.80 if is_ephemeral else self.config.four_valets.planchet_stop_confidence
        return not planchet.needs_mousqueton and planchet.confidence.overall >= threshold

    def _get_valet_model(
        self,
        valet: str,
        previous_confidence: Optional[float] = None,
        is_critical_content: bool = False,
        is_ephemeral: bool = False,
    ) -> ModelTier:
        """
        Get the model for a valet, with adaptive escalation if confidence is low.

        Implements the adaptive escalation from FOUR_VALETS_SPEC.md section 5.2:
        - If previous pass confidence < threshold (0.80), escalate to stronger model
        - Escalation map: haiku → sonnet → opus

        Additionally, escalate directly to Opus for critical content:
        - Legal/contractual documents (bail, contrat, facture, etc.)
        - High amounts (> 1000€)

        Args:
            valet: Valet name (grimaud, bazin, planchet, mousqueton)
            previous_confidence: Confidence from the previous pass (triggers escalation if < threshold)
            is_critical_content: If True, escalate directly to Opus (legal/contractual or high amount)
            is_ephemeral: If True, block escalation to Opus (save cost on spam/notifications)

        Returns:
            ModelTier to use for this valet
        """
        # Critical content: escalate directly to Opus for Bazin onwards
        # Legal/contractual documents and high amounts require careful analysis
        if is_critical_content and valet in ("bazin", "planchet", "mousqueton"):
            logger.info(
                f"Critical content escalation for {valet}: direct to Opus "
                f"(legal/contractual content or high amount)"
            )
            return ModelTier.OPUS

        # Get default model for this valet
        model_name = self.config.four_valets.models.get(valet, "haiku")
        base_model = ModelTier(model_name)

        # Check for adaptive escalation based on confidence
        escalation_config = self.config.four_valets.adaptive_escalation
        if (
            escalation_config.enabled
            and previous_confidence is not None
            and previous_confidence < escalation_config.threshold
        ):
            # Escalate to a more powerful model
            escalated_model_name = escalation_config.escalation_map.get(model_name)
            if escalated_model_name:
                # Block Opus escalation for ephemeral content (sonnet max)
                if is_ephemeral and escalated_model_name == "opus":
                    logger.info(
                        f"Escalation capped for {valet}: {model_name} → sonnet "
                        f"(ephemeral content, Opus blocked)"
                    )
                    return ModelTier.SONNET
                logger.info(
                    f"Adaptive escalation for {valet}: {model_name} → {escalated_model_name} "
                    f"(previous confidence {previous_confidence:.0%} < {escalation_config.threshold:.0%})"
                )
                return ModelTier(escalated_model_name)

        return base_model

    def _get_valet_api_params(self, valet: str) -> dict:
        """Get the API parameters for a valet."""
        return self.config.four_valets.api_params.get(valet, {})

    async def _finalize_four_valets(
        self,
        passes: list[PassResult],
        event: PerceivedEvent,
        start_time: float,
        total_tokens: int,
        stopped_at: str,
        stop_reason: str,
        context: Optional[StructuredContext] = None,
        sender_importance: str = "normal",
    ) -> MultiPassResult:
        """
        Build the final MultiPassResult for Four Valets pipeline.

        Similar to _build_result but with Four Valets specific handling.
        """
        last_pass = passes[-1]
        total_duration = (time.time() - start_time) * 1000

        # Build analysis context
        analysis_context = AnalysisContext(
            sender_importance=sender_importance,
            has_attachments=bool(getattr(event, "attachments", None)),
            is_thread=bool(getattr(event, "thread_id", None)),
        )

        # Check for high-stakes
        high_stakes_detected = is_high_stakes(
            last_pass.extractions,
            analysis_context,
            self.config,
        )

        # Collect all entities
        all_entities: set[str] = set()
        for p in passes:
            all_entities.update(p.entities_discovered)

        # Collect and deduplicate strategic questions from all valets (v3.1)
        all_strategic_questions = self._collect_strategic_questions(passes)

        # Apply age-based adjustments
        age_days = self._calculate_event_age_days(event)
        adjusted_action, adjusted_extractions, age_adjustment = self._apply_age_adjustments(
            last_pass.action,
            last_pass.extractions,
            age_days,
            event,
        )
        if age_adjustment:
            logger.info(f"Age adjustment applied: {age_adjustment}")

        # Run coherence pass on adjusted extractions
        coherence_validated = False
        coherence_corrections = 0
        coherence_duplicates = 0
        coherence_confidence = 1.0
        coherence_warnings: list[dict] = []

        if adjusted_extractions:
            validated_extractions, coherence_result = await self._run_coherence_pass(
                adjusted_extractions, event
            )
            if coherence_result is not None:
                adjusted_extractions = validated_extractions
                coherence_validated = True
                coherence_corrections = coherence_result.coherence_summary.corrected
                coherence_duplicates = coherence_result.coherence_summary.duplicates_detected
                coherence_confidence = coherence_result.coherence_confidence
                coherence_warnings = [
                    {"type": w.type, "index": w.extraction_index, "message": w.message}
                    for w in coherence_result.warnings
                ]
                total_tokens += coherence_result.tokens_used

        # Update stop reason
        final_stop_reason = stop_reason
        if age_adjustment:
            final_stop_reason = f"{stop_reason}; {age_adjustment}"
        if coherence_validated and coherence_corrections > 0:
            final_stop_reason = (
                f"{final_stop_reason}; coherence_pass: {coherence_corrections} corrected"
            )

        # Determine if escalated (Mousqueton uses Sonnet)
        escalated = stopped_at == "mousqueton"

        # Serialize context for transparency
        serialized_context: Optional[dict[str, Any]] = None
        if context is not None:
            serialized_context = {
                "entities_searched": context.query_entities,
                "sources_searched": context.sources_searched,
                "total_results": context.total_results,
                "notes": [
                    {
                        "note_id": n.note_id,
                        "title": n.title,
                        "note_type": n.note_type,
                        "summary": n.summary[:200] if n.summary else "",
                        "relevance": round(n.relevance, 2),
                        "tags": n.tags,
                    }
                    for n in context.notes
                ],
            }

        # Extract context_influence from last pass
        last_context_influence = last_pass.context_influence

        # Get canevas status from template renderer (v3.2)
        canevas_status_dict = None
        if self.template_renderer:
            canevas_status = self.template_renderer.get_canevas_status()
            if canevas_status:
                canevas_status_dict = canevas_status.to_dict()

        return MultiPassResult(
            extractions=adjusted_extractions,
            action=adjusted_action,
            confidence=last_pass.confidence,
            entities_discovered=all_entities,
            passes_count=len(passes),
            total_duration_ms=total_duration,
            total_tokens=total_tokens,
            final_model=last_pass.model_used,
            escalated=escalated,
            pass_history=passes,
            stop_reason=final_stop_reason,
            high_stakes=high_stakes_detected,
            # Coherence validation metadata
            coherence_validated=coherence_validated,
            coherence_corrections=coherence_corrections,
            coherence_duplicates_detected=coherence_duplicates,
            coherence_confidence=coherence_confidence,
            coherence_warnings=coherence_warnings,
            # Retrieved context for transparency
            retrieved_context=serialized_context,
            context_influence=last_context_influence,
            # Four Valets v3.0 specific
            stopped_at=stopped_at,
            critique=last_pass.critique,
            arbitrage=last_pass.arbitrage,
            memory_hint=last_pass.memory_hint,
            confidence_assessment=last_pass.confidence_assessment,
            # Strategic questions v3.1
            strategic_questions=all_strategic_questions,
            # Canevas status v3.2
            canevas_status=canevas_status_dict,
        )


# Factory function for convenience
def create_multi_pass_analyzer(
    ai_router: Optional[AIRouter] = None,
    context_searcher: Optional["ContextSearcher"] = None,
    config: Optional[MultiPassConfig] = None,
    note_manager: Optional["NoteManager"] = None,
    entity_searcher: Optional["EntitySearcher"] = None,
    enable_coherence_pass: bool = True,
) -> MultiPassAnalyzer:
    """
    Create a MultiPassAnalyzer with default or provided dependencies.

    Args:
        ai_router: AIRouter instance (creates default if None)
        context_searcher: ContextSearcher instance (optional)
        config: MultiPassConfig (uses defaults if None)
        note_manager: NoteManager for coherence validation (optional)
        entity_searcher: EntitySearcher for finding similar notes (optional)
        enable_coherence_pass: Whether to run coherence validation (default: True)

    Returns:
        Configured MultiPassAnalyzer instance
    """
    if ai_router is None:
        from src.core.config_manager import get_config

        app_config = get_config()
        ai_router = AIRouter(app_config.ai)

    return MultiPassAnalyzer(
        ai_router=ai_router,
        context_searcher=context_searcher,
        config=config,
        note_manager=note_manager,
        entity_searcher=entity_searcher,
        enable_coherence_pass=enable_coherence_pass,
    )
