"""
Analysis Engine — Base Class for AI-Powered Analysis

Provides shared functionality for multi-pass analysis and retouche:
- Model escalation (Haiku → Sonnet → Opus)
- Robust JSON parsing with multi-level repair
- Error handling with typed exceptions
- Metrics tracking

Part of Sancho's analysis infrastructure.
Phase 0 of Retouche implementation.
"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from src.monitoring.logger import get_logger
from src.sancho.cost_calculator import AIModel
from src.sancho.json_utils import clean_json_string, repair_json_with_library

if TYPE_CHECKING:
    from src.sancho.router import AIRouter

logger = get_logger("sancho.analysis_engine")


class AnalysisError(Exception):
    """Base exception for analysis errors."""

    pass


class AICallError(AnalysisError):
    """Error calling the AI API."""

    pass


class JSONParseError(AnalysisError):
    """Error parsing AI response JSON."""

    pass


class EscalationExhaustedError(AnalysisError):
    """All model escalation attempts failed."""

    pass


class ModelTier(str, Enum):
    """AI model tiers for escalation."""

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


# Model mapping
MODEL_MAP = {
    ModelTier.HAIKU: AIModel.CLAUDE_HAIKU,
    ModelTier.SONNET: AIModel.CLAUDE_SONNET,
    ModelTier.OPUS: AIModel.CLAUDE_OPUS,
}

# Default escalation thresholds
DEFAULT_ESCALATION_THRESHOLDS = {
    "sonnet": 0.7,  # Escalate to Sonnet if confidence < 0.7
    "opus": 0.5,  # Escalate to Opus if confidence < 0.5
}


@dataclass
class AICallResult:
    """Result of an AI API call."""

    response: str
    model_used: ModelTier
    model_id: str
    tokens_used: int
    duration_ms: float
    cache_hit: bool = False
    cache_write: bool = False

    # Token breakdown
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


@dataclass
class AnalysisMetrics:
    """Metrics for an analysis run."""

    total_calls: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    escalations: int = 0
    parse_retries: int = 0
    errors: list[str] = field(default_factory=list)


class AnalysisEngine(ABC):
    """
    Abstract base class for AI-powered analysis.

    Provides common functionality:
    - Model escalation with configurable thresholds
    - Robust JSON parsing with multi-level repair
    - Error handling with typed exceptions
    - Metrics tracking

    Subclasses must implement:
    - _build_prompt(): Build the prompt for analysis
    - _process_result(): Process the parsed JSON result
    """

    def __init__(
        self,
        ai_router: "AIRouter",
        escalation_thresholds: Optional[dict[str, float]] = None,
    ):
        """
        Initialize the analysis engine.

        Args:
            ai_router: AIRouter instance for API calls
            escalation_thresholds: Custom thresholds for model escalation
        """
        self.ai_router = ai_router
        self.escalation_thresholds = escalation_thresholds or DEFAULT_ESCALATION_THRESHOLDS
        self._metrics = AnalysisMetrics()

    @property
    def metrics(self) -> AnalysisMetrics:
        """Get current metrics."""
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset metrics to zero."""
        self._metrics = AnalysisMetrics()

    # ==================== AI Call Methods ====================

    async def call_ai(
        self,
        prompt: str,
        model: ModelTier = ModelTier.HAIKU,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> AICallResult:
        """
        Call the AI model with a prompt.

        Args:
            prompt: User prompt to send
            model: Model tier to use
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt (enables caching)

        Returns:
            AICallResult with response and metadata

        Raises:
            AICallError: If API call fails
        """
        start_time = time.time()
        ai_model = MODEL_MAP[model]

        try:
            if system_prompt:
                # Use cached call for system prompt
                response, usage = self.ai_router._call_claude_with_cache(
                    user_prompt=prompt,
                    system_prompt=system_prompt,
                    model=ai_model,
                    max_tokens=max_tokens,
                )
            else:
                # Use standard call
                response, usage = self.ai_router._call_claude(
                    prompt=prompt,
                    model=ai_model,
                    max_tokens=max_tokens,
                )

            duration_ms = (time.time() - start_time) * 1000

            if response is None:
                raise AICallError("API returned None response")

            # Update metrics
            self._metrics.total_calls += 1
            self._metrics.total_tokens += usage.get("total_tokens", 0)
            self._metrics.total_duration_ms += duration_ms

            # Extract cache info
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_write = usage.get("cache_creation_input_tokens", 0)

            return AICallResult(
                response=response,
                model_used=model,
                model_id=ai_model.value,
                tokens_used=usage.get("total_tokens", 0),
                duration_ms=duration_ms,
                cache_hit=cache_read > 0,
                cache_write=cache_write > 0,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cache_read_tokens=cache_read,
                cache_creation_tokens=cache_write,
            )

        except Exception as e:
            self._metrics.errors.append(f"AI call failed: {e}")
            logger.error(f"AI call failed with {model.value}: {e}", exc_info=True)
            raise AICallError(f"API call failed: {e}") from e

    async def call_with_escalation(
        self,
        prompt: str,
        initial_model: ModelTier = ModelTier.HAIKU,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        get_confidence: Optional[callable] = None,
    ) -> tuple[AICallResult, dict[str, Any]]:
        """
        Call AI with automatic model escalation based on confidence.

        Starts with initial_model, escalates to Sonnet/Opus if confidence
        is below thresholds.

        Args:
            prompt: User prompt to send
            initial_model: Starting model tier
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt (enables caching)
            get_confidence: Optional function to extract confidence from parsed result
                           If None, no escalation happens

        Returns:
            Tuple of (AICallResult, parsed_data dict)

        Raises:
            AICallError: If all attempts fail
            JSONParseError: If response parsing fails
        """
        models_to_try = [initial_model]

        # Add escalation models based on initial model
        if initial_model == ModelTier.HAIKU:
            models_to_try.append(ModelTier.SONNET)
            models_to_try.append(ModelTier.OPUS)
        elif initial_model == ModelTier.SONNET:
            models_to_try.append(ModelTier.OPUS)

        last_error = None
        last_result = None
        last_data = None

        for model in models_to_try:
            try:
                result = await self.call_ai(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    system_prompt=system_prompt,
                )

                # Parse JSON response
                data = self.parse_json_response(result.response)
                last_result = result
                last_data = data

                # Check if we should escalate
                if get_confidence and model != ModelTier.OPUS:
                    confidence = get_confidence(data)
                    threshold_key = "sonnet" if model == ModelTier.HAIKU else "opus"
                    threshold = self.escalation_thresholds.get(threshold_key, 0.5)

                    if confidence < threshold:
                        logger.info(
                            f"Escalating from {model.value}: confidence {confidence:.2f} < {threshold}"
                        )
                        self._metrics.escalations += 1
                        continue

                # Confidence OK or no check needed
                return result, data

            except JSONParseError as e:
                last_error = e
                logger.warning(f"JSON parse failed with {model.value}, will try next model")
                self._metrics.parse_retries += 1
                continue

            except AICallError as e:
                last_error = e
                logger.warning(f"AI call failed with {model.value}: {e}")
                continue

        # All models failed
        if last_result and last_data:
            # Return last successful result even if confidence was low
            return last_result, last_data

        raise EscalationExhaustedError(f"All models failed. Last error: {last_error}")

    # ==================== JSON Parsing ====================

    def parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON from AI response with multi-level repair.

        Uses a 3-level strategy:
        1. Direct parse (fast, ideal case)
        2. json-repair library (robust)
        3. Regex cleaning + json-repair (last resort)

        Args:
            response: Raw response text from AI

        Returns:
            Parsed JSON as dict

        Raises:
            JSONParseError: If all parsing methods fail
        """
        if not response or not response.strip():
            raise JSONParseError("Empty response from AI")

        # Extract JSON from response
        json_str = self._extract_json_block(response)

        # Level 1: Try direct parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Level 2: Try json-repair library
        repaired, repair_success = repair_json_with_library(json_str)
        if repair_success:
            try:
                result = json.loads(repaired)
                logger.debug("JSON repaired using json-repair library")
                return result
            except json.JSONDecodeError:
                pass

        # Level 3: Regex cleaning + json-repair
        cleaned = clean_json_string(json_str)
        try:
            result = json.loads(cleaned)
            logger.debug("JSON parsed after regex cleaning")
            return result
        except json.JSONDecodeError:
            pass

        # Last resort: json-repair on cleaned string
        repaired2, _ = repair_json_with_library(cleaned)
        try:
            result = json.loads(repaired2)
            logger.debug("JSON repaired using regex + json-repair")
            return result
        except json.JSONDecodeError as e:
            preview = json_str[:300].replace("\n", "\\n")
            raise JSONParseError(
                f"All JSON repair methods failed. Error: {e}. Preview: {preview}"
            ) from e

    def _extract_json_block(self, response: str) -> str:
        """
        Extract JSON block from response text.

        Handles:
        - ```json code blocks
        - ``` code blocks
        - Raw JSON (first { to last })

        Args:
            response: Raw response text

        Returns:
            Extracted JSON string

        Raises:
            JSONParseError: If no JSON found
        """
        # Handle ```json code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                extracted = response[start:end].strip()
                if extracted:
                    return extracted

        # Handle ``` code blocks
        if "```" in response:
            start = response.find("```") + 3
            # Skip language identifier
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
            preview = response[:200].replace("\n", "\\n")
            raise JSONParseError(f"No JSON object found. Preview: {preview}")

        return response[json_start:json_end]

    # ==================== Abstract Methods ====================

    @abstractmethod
    def _build_prompt(self, context: Any) -> str:
        """
        Build the prompt for analysis.

        Args:
            context: Analysis context (event, note, etc.)

        Returns:
            Rendered prompt string
        """
        pass

    @abstractmethod
    def _process_result(self, result: dict[str, Any], call_result: AICallResult) -> Any:
        """
        Process the parsed JSON result.

        Args:
            result: Parsed JSON dict from AI response
            call_result: AICallResult with metadata

        Returns:
            Processed analysis result (type depends on subclass)
        """
        pass

    # ==================== Utility Methods ====================

    def handle_ai_error(self, error: Exception) -> dict[str, Any]:
        """
        Handle AI errors gracefully.

        Returns a fallback result dict that can be used when AI fails.

        Args:
            error: The exception that occurred

        Returns:
            Fallback result dict
        """
        logger.warning(f"AI analysis failed, using fallback: {error}")
        return {
            "error": str(error),
            "fallback": True,
            "confidence": 0.5,
            "reasoning": f"Fallback result due to error: {error}",
        }
