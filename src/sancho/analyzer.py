"""
Event Analyzer — Workflow v2.1

Analyseur d'événements avec escalade automatique Haiku → Sonnet.

Ce module implémente la phase d'analyse du pipeline v2.1 :
1. Rendu du prompt avec contexte
2. Appel Haiku (rapide, économique)
3. Si confiance < seuil : escalade vers Sonnet
4. Parsing et validation du résultat

Usage:
    analyzer = EventAnalyzer(ai_router, template_manager, config)
    result = await analyzer.analyze(event, context_notes)
"""

import json
import time
from typing import Optional

from src.core.config_manager import WorkflowV2Config
from src.core.events.universal_event import PerceivedEvent
from src.core.models.v2_models import (
    AnalysisResult,
    ContextNote,
    EmailAction,
    Extraction,
    ExtractionType,
    ImportanceLevel,
    NoteAction,
)
from src.monitoring.logger import get_logger
from src.sancho.router import AIModel, AIRouter, clean_json_string

logger = get_logger("analyzer")


class AnalyzerError(Exception):
    """Base exception for analyzer errors"""

    pass


class PromptRenderError(AnalyzerError):
    """Error rendering the prompt template"""

    pass


class APICallError(AnalyzerError):
    """Error calling the AI API"""

    pass


class ParseError(AnalyzerError):
    """Error parsing the AI response"""

    pass


class EventAnalyzer:
    """
    Analyse les événements avec l'API Claude.

    Implémente une stratégie d'escalade automatique :
    - Essaie d'abord avec Haiku (rapide, ~$0.25/1M tokens)
    - Si confiance < seuil (default 0.7), escalade vers Sonnet (~$3/1M tokens)

    Attributes:
        ai_router: Router pour les appels API Claude
        config: Configuration Workflow v2.1

    Example:
        >>> analyzer = EventAnalyzer(router, config)
        >>> result = await analyzer.analyze(event, context_notes)
        >>> if result.high_confidence:
        ...     # Auto-apply extractions
        ...     pass
    """

    # Model mapping
    MODEL_MAP = {
        "haiku": AIModel.CLAUDE_HAIKU,
        "sonnet": AIModel.CLAUDE_SONNET,
        "opus": AIModel.CLAUDE_OPUS,
    }

    def __init__(
        self,
        ai_router: AIRouter,
        config: Optional[WorkflowV2Config] = None,
    ):
        """
        Initialize the analyzer.

        Args:
            ai_router: AIRouter instance for API calls
            config: WorkflowV2Config (uses defaults if None)
        """
        self.ai_router = ai_router
        self.config = config or WorkflowV2Config()

        # Lazy load template manager to avoid circular imports
        self._template_manager = None

    @property
    def template_manager(self):
        """Lazy-loaded template manager"""
        if self._template_manager is None:
            from src.sancho.templates import get_template_manager

            self._template_manager = get_template_manager()
        return self._template_manager

    async def analyze(
        self,
        event: PerceivedEvent,
        context_notes: Optional[list[ContextNote]] = None,
    ) -> AnalysisResult:
        """
        Analyse un événement avec escalade automatique.

        1. Rend le prompt avec le contexte
        2. Appelle Haiku
        3. Si confidence < escalation_threshold, escalade vers Sonnet
        4. Retourne le résultat final

        Args:
            event: Événement perçu à analyser
            context_notes: Notes de contexte optionnelles

        Returns:
            AnalysisResult avec extractions et métadonnées

        Raises:
            PromptRenderError: Si le rendu du prompt échoue
            APICallError: Si l'appel API échoue
            ParseError: Si le parsing de la réponse échoue
        """
        context_notes = context_notes or []

        # Render prompt
        prompt = self._render_prompt(event, context_notes)

        # Try with default model (Haiku)
        default_model = self.MODEL_MAP.get(
            self.config.default_model, AIModel.CLAUDE_HAIKU
        )
        result = await self._call_model(prompt, default_model)

        # Check if escalation is needed
        if result.confidence < self.config.escalation_threshold:
            logger.info(
                f"Escalating from {self.config.default_model} to {self.config.escalation_model} "
                f"(confidence {result.confidence:.2f} < {self.config.escalation_threshold})"
            )

            escalation_model = self.MODEL_MAP.get(
                self.config.escalation_model, AIModel.CLAUDE_SONNET
            )

            # Call with stronger model
            escalated_result = await self._call_model(prompt, escalation_model)
            escalated_result.escalated = True
            return escalated_result

        return result

    def _render_prompt(
        self,
        event: PerceivedEvent,
        context_notes: list[ContextNote],
    ) -> str:
        """
        Render the extraction prompt.

        Args:
            event: Event to analyze
            context_notes: Context notes for enrichment

        Returns:
            Rendered prompt string

        Raises:
            PromptRenderError: If template rendering fails
        """
        try:
            # Convert ContextNote dataclasses to dicts for template
            context_dicts = [
                {
                    "title": note.title,
                    "type": note.type,
                    "content_summary": note.content_summary,
                    "note_id": note.note_id,
                }
                for note in context_notes
            ]

            return self.template_manager.render(
                "ai/v2/extraction",
                event=event,
                context=context_dicts,
                max_content_chars=self.config.event_content_max_chars,
                max_context_notes=self.config.context_notes_count,
                max_note_chars=self.config.context_note_max_chars,
            )
        except Exception as e:
            logger.error(f"Failed to render extraction prompt: {e}", exc_info=True)
            raise PromptRenderError(f"Template rendering failed: {e}") from e

    async def _call_model(
        self,
        prompt: str,
        model: AIModel,
    ) -> AnalysisResult:
        """
        Call the AI model and parse the response.

        Args:
            prompt: Rendered prompt
            model: AI model to use

        Returns:
            Parsed AnalysisResult

        Raises:
            APICallError: If API call fails
            ParseError: If response parsing fails
        """
        start_time = time.time()

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
                model=model.value,
                usage=usage,
                duration_ms=duration_ms,
            )

        except (PromptRenderError, ParseError):
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"API call failed: {e}", exc_info=True)
            raise APICallError(f"API call failed: {e}") from e

    def _parse_response(
        self,
        response: str,
        model: str,
        usage: dict,
        duration_ms: float,
    ) -> AnalysisResult:
        """
        Parse the JSON response into AnalysisResult.

        Args:
            response: Raw response text from Claude
            model: Model name used
            usage: Token usage dict
            duration_ms: API call duration in milliseconds

        Returns:
            Parsed AnalysisResult

        Raises:
            ParseError: If JSON parsing fails
        """
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)

            # Clean and parse
            cleaned = clean_json_string(json_str)
            data = json.loads(cleaned)

            # Parse extractions
            extractions = self._parse_extractions(data.get("extractions", []))

            # Parse action
            action_str = data.get("action", "rien")
            try:
                action = EmailAction(action_str)
            except ValueError:
                logger.warning(f"Unknown action '{action_str}', defaulting to 'rien'")
                action = EmailAction.RIEN

            # Get confidence
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

            return AnalysisResult(
                extractions=extractions,
                action=action,
                confidence=confidence,
                raisonnement=data.get("raisonnement", ""),
                model_used=model,
                tokens_used=usage.get("total_tokens", 0),
                duration_ms=duration_ms,
                escalated=False,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nResponse: {response[:500]}")
            raise ParseError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            logger.error(f"Parse error: {e}", exc_info=True)
            raise ParseError(f"Failed to parse response: {e}") from e

    def _extract_json(self, response: str) -> str:
        """
        Extract JSON object from response text.

        Handles cases where Claude adds explanation before/after the JSON.

        Args:
            response: Raw response text

        Returns:
            Extracted JSON string

        Raises:
            ParseError: If no valid JSON found
        """
        # Find first { and last }
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start == -1 or json_end <= json_start:
            raise ParseError("No JSON object found in response")

        return response[json_start:json_end]

    def _parse_extractions(self, extractions_data: list) -> list[Extraction]:
        """
        Parse extractions list from JSON data.

        Args:
            extractions_data: List of extraction dicts from JSON

        Returns:
            List of validated Extraction objects
        """
        extractions = []

        for ext_data in extractions_data:
            try:
                # Validate required fields
                info = ext_data.get("info", "").strip()
                if not info:
                    logger.warning("Skipping extraction with empty info")
                    continue

                note_cible = ext_data.get("note_cible", "").strip()
                if not note_cible:
                    logger.warning(f"Skipping extraction with empty note_cible: {info}")
                    continue

                # Parse enums with fallbacks
                ext_type = self._parse_extraction_type(ext_data.get("type", "fait"))
                importance = self._parse_importance(
                    ext_data.get("importance", "moyenne")
                )
                note_action = self._parse_note_action(
                    ext_data.get("note_action", "enrichir")
                )

                extraction = Extraction(
                    info=info,
                    type=ext_type,
                    importance=importance,
                    note_cible=note_cible,
                    note_action=note_action,
                    omnifocus=bool(ext_data.get("omnifocus", False)),
                )
                extractions.append(extraction)

            except Exception as e:
                logger.warning(f"Failed to parse extraction: {e}")
                continue

        return extractions

    def _parse_extraction_type(self, type_str: str) -> ExtractionType:
        """Parse extraction type with fallback"""
        try:
            return ExtractionType(type_str.lower())
        except ValueError:
            logger.warning(f"Unknown extraction type '{type_str}', defaulting to 'fait'")
            return ExtractionType.FAIT

    def _parse_importance(self, importance_str: str) -> ImportanceLevel:
        """Parse importance level with fallback"""
        importance_lower = importance_str.lower().strip()

        # Handle 'basse' as 'moyenne' (AI sometimes returns this)
        if importance_lower == "basse":
            return ImportanceLevel.MOYENNE

        try:
            return ImportanceLevel(importance_lower)
        except ValueError:
            logger.warning(
                f"Unknown importance '{importance_str}', defaulting to 'moyenne'"
            )
            return ImportanceLevel.MOYENNE

    def _parse_note_action(self, action_str: str) -> NoteAction:
        """Parse note action with fallback"""
        try:
            return NoteAction(action_str.lower())
        except ValueError:
            logger.warning(
                f"Unknown note action '{action_str}', defaulting to 'enrichir'"
            )
            return NoteAction.ENRICHIR


# Factory function for convenience
def create_analyzer(
    ai_router: Optional[AIRouter] = None,
    config: Optional[WorkflowV2Config] = None,
) -> EventAnalyzer:
    """
    Create an EventAnalyzer with default or provided dependencies.

    Args:
        ai_router: AIRouter instance (creates default if None)
        config: WorkflowV2Config (uses defaults if None)

    Returns:
        Configured EventAnalyzer instance
    """
    if ai_router is None:
        from src.core.config_manager import get_config

        app_config = get_config()
        ai_router = AIRouter(app_config.ai)

    return EventAnalyzer(ai_router=ai_router, config=config)
