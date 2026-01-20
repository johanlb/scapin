"""
AI Router

Routes AI requests to appropriate models with rate limiting and retry logic.
"""

import asyncio
import json
import re
import threading
import time
from collections import deque
from typing import Any, Optional

from src.core.config_manager import AIConfig
from src.core.schemas import EmailAnalysis, EmailContent, EmailMetadata, NoteAnalysis
from src.monitoring.logger import get_logger
from src.passepartout.context_loader import ContextLoader
from src.passepartout.note_manager import Note
from src.passepartout.note_metadata import NoteMetadata
from src.sancho.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.sancho.cost_calculator import AIModel, calculate_cost
from src.sancho.rate_limiter import RateLimiter

logger = get_logger("ai_router")


def clean_json_string(json_str: str) -> str:
    """
    Clean a JSON string by fixing common issues from LLM responses.

    Handles:
    - Trailing commas before ] or }
    - Missing commas between properties/elements
    - Single-line comments (// ...)
    - Multi-line comments (/* ... */)
    - Markdown code blocks (```json ... ```)
    - Extra text before/after JSON

    Args:
        json_str: Raw JSON string that might be malformed

    Returns:
        Cleaned JSON string
    """
    # Remove markdown code blocks if present
    json_str = re.sub(r"```json\s*", "", json_str)
    json_str = re.sub(r"```\s*$", "", json_str)
    json_str = re.sub(r"```", "", json_str)

    # Remove single-line comments (// ...)
    json_str = re.sub(r"//[^\n]*", "", json_str)

    # Remove multi-line comments (/* ... */)
    json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

    # Remove trailing commas before ] or }
    # Pattern: comma followed by optional whitespace, then ] or }
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

    # Fix missing commas between properties (any whitespace including spaces):
    # Pattern: "value" followed by any whitespace then "key"
    # e.g., '"value"   "key"' or '"value"\n    "key"' → '"value", "key"'
    json_str = re.sub(r'"\s+(")', r'", \1', json_str)

    # Fix missing commas after numbers/booleans/null before "
    # e.g., '95   "reasoning"' or '95\n    "reasoning"' → '95, "reasoning"'
    json_str = re.sub(r'(\d+)\s+(")', r"\1, \2", json_str)
    json_str = re.sub(r'(true|false|null)\s+(")', r"\1, \2", json_str)

    # Fix missing commas after ] or } before " or [ or {
    # e.g., ']   "key"' or '}\n    "key"' → '], "key"'
    json_str = re.sub(r'(\])\s+("|\[|\{)', r"\1, \2", json_str)
    json_str = re.sub(r'(\})\s+("|\[|\{)', r"\1, \2", json_str)

    # Fix missing commas between array elements (objects in arrays):
    # e.g., '}\n    {' → '}, {'  (between objects in an array)
    json_str = re.sub(r"(\})\s*\n\s*(\{)", r"\1, \2", json_str)
    json_str = re.sub(r"(\])\s*\n\s*(\[)", r"\1, \2", json_str)

    return json_str


def _repair_json_with_library(json_str: str) -> tuple[str, bool]:
    """
    Use json-repair library for robust JSON repair.

    This handles complex cases like:
    - Missing commas in nested structures
    - Unquoted strings
    - Trailing commas
    - Single quotes instead of double quotes

    Args:
        json_str: Malformed JSON string

    Returns:
        Tuple of (repaired JSON string, success boolean)
    """
    try:
        from json_repair import repair_json

        repaired = repair_json(json_str)
        return repaired, True
    except ImportError:
        logger.warning("json-repair library not installed, falling back to regex")
        return json_str, False
    except Exception as e:
        logger.warning(f"json-repair failed: {e}")
        return json_str, False


class AIRouter:
    """
    AI Router for email analysis

    Features:
    - Claude API integration
    - Rate limiting (40 RPM default)
    - Automatic retries with exponential backoff
    - Response parsing and validation
    - Error handling

    Usage:
        router = AIRouter(config)
        analysis = router.analyze_email(metadata, content)
    """

    def __init__(self, config: AIConfig):
        """
        Initialize AI router

        Args:
            config: AI configuration
        """
        self.config = config
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_per_minute, window_seconds=60
        )
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        # Initialize Context Loader for Dynamic Briefing
        try:
            self.context_loader = ContextLoader()
            logger.info("ContextLoader initialized in AIRouter")
        except Exception as e:
            logger.warning(f"Failed to initialize ContextLoader: {e}")
            self.context_loader = None

        # Metrics tracking
        self._metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "duration_histogram": deque(maxlen=1000),  # Auto-trims at 1000 items
            "errors_by_type": {},
        }
        self._metrics_lock = threading.Lock()

        # Try to import anthropic
        try:
            import anthropic

            self.anthropic = anthropic
            self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            logger.info("Anthropic client initialized")
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}", exc_info=True)
            raise

        logger.info(
            "AI Router initialized",
            extra={
                "rate_limit": config.rate_limit_per_minute,
                "confidence_threshold": config.confidence_threshold,
                "circuit_breaker_threshold": 5,
            },
        )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"AIRouter(model_default={AIModel.CLAUDE_HAIKU.value!r}, "
            f"rate_limit={self.rate_limiter.max_requests}/min, "
            f"circuit_breaker={self.circuit_breaker.state})"
        )

    def analyze_email(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        model: AIModel = AIModel.CLAUDE_HAIKU,
        max_retries: int = 3,
        existing_folders: Optional[list[str]] = None,
        user_instruction: Optional[str] = None,
        learned_suggestions: Optional[list[dict]] = None,
    ) -> Optional[EmailAnalysis]:
        """
        Analyze email with AI


        Args:
            metadata: Email metadata
            content: Email content
            model: AI model to use
            max_retries: Maximum retry attempts
            existing_folders: List of existing IMAP folders for destination suggestions
            user_instruction: Optional user instruction to guide the analysis
            learned_suggestions: Folder suggestions from learning system

        Returns:
            EmailAnalysis or None if analysis fails
        """
        from src.sancho.templates import get_template_manager

        # Acquire rate limit permission
        if not self.rate_limiter.acquire(timeout=30):
            logger.error("Rate limit timeout - could not acquire permission")
            return None

        # Prepare prompt
        tm = get_template_manager()
        try:
            prompt = tm.render(
                "ai/email_analysis",
                subject=metadata.subject,
                from_address=metadata.from_address,
                from_name=metadata.from_name,
                to_addresses=", ".join(metadata.to_addresses),
                body=content.plain_text or content.preview or "",
                has_attachments=metadata.has_attachments,
                date=metadata.date.isoformat(),
                existing_folders=existing_folders or [],
                user_instruction=user_instruction,
                learned_suggestions=learned_suggestions or [],
            )
        except Exception as e:
            logger.error(f"Failed to render email analysis prompt: {e}", exc_info=True)
            return None

        # Make API call with selective retry and circuit breaker
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Calling Claude API (attempt {attempt + 1}/{max_retries})",
                    extra={
                        "model": model.value,
                        "email_id": metadata.id,
                        "subject": metadata.subject,
                    },
                )

                # Use circuit breaker to prevent repeated calls to failing service
                response, api_usage = self.circuit_breaker.call(self._call_claude, prompt, model)

                if response:
                    # Parse response
                    analysis = self._parse_analysis_response(response, metadata)
                    if analysis:
                        # Record successful metrics
                        duration_ms = (time.time() - start_time) * 1000
                        self._record_analysis_metrics(
                            duration_ms=duration_ms,
                            tokens=api_usage.get("total_tokens", 0),
                            input_tokens=api_usage.get("input_tokens", 0),
                            output_tokens=api_usage.get("output_tokens", 0),
                            model=model,
                        )

                        logger.info(
                            "Email analysis successful",
                            extra={
                                "email_id": metadata.id,
                                "action": analysis.action.value,
                                "confidence": analysis.confidence,
                                "duration_ms": duration_ms,
                                "tokens": api_usage.get("total_tokens", 0),
                                "estimated_cost_usd": self._calculate_cost(
                                    model,
                                    api_usage.get("input_tokens", 0),
                                    api_usage.get("output_tokens", 0),
                                ),
                            },
                        )
                        return analysis

            # SELECTIVE RETRY LOGIC: Different strategies for different error types

            except self.anthropic.RateLimitError:
                # RETRIABLE: Rate limit - wait and retry with backoff
                self._record_error_metric("RateLimitError")

                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 60)  # Exponential backoff, cap at 60s
                    logger.warning(
                        f"Rate limit exceeded, retrying in {wait_time}s",
                        extra={"attempt": attempt + 1, "max_retries": max_retries},
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("Max retries exceeded for rate limit")
                    return None

            except self.anthropic.AuthenticationError as e:
                # NON-RETRIABLE: Invalid API key - fail immediately
                self._record_error_metric("AuthenticationError")

                logger.error(
                    f"Authentication failed: {e}. Check API key configuration.", exc_info=True
                )
                return None

            except self.anthropic.PermissionDeniedError as e:
                # NON-RETRIABLE: Permissions issue - fail immediately
                self._record_error_metric("PermissionDeniedError")
                logger.error(f"Permission denied: {e}", exc_info=True)
                return None

            except self.anthropic.BadRequestError as e:
                # NON-RETRIABLE: Invalid request - fail immediately
                self._record_error_metric("BadRequestError")
                logger.error(
                    f"Invalid request: {e}. Check email content or prompt format.", exc_info=True
                )
                return None

            except self.anthropic.APIConnectionError as e:
                # RETRIABLE: Network issue - retry with backoff
                self._record_error_metric("APIConnectionError")
                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 30)
                    logger.warning(
                        f"API connection error, retrying in {wait_time}s: {e}",
                        extra={"attempt": attempt + 1},
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Max retries exceeded for connection error: {e}")
                    return None

            except self.anthropic.InternalServerError as e:
                # RETRIABLE: Server error - retry with backoff
                self._record_error_metric("InternalServerError")
                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 30)
                    logger.warning(
                        f"Server error, retrying in {wait_time}s: {e}",
                        extra={"attempt": attempt + 1},
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Max retries exceeded for server error: {e}")
                    return None

            except self.anthropic.APIError as e:
                # RETRIABLE: Generic API error - cautious retry
                self._record_error_metric("APIError")
                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 10)
                    logger.warning(f"API error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Max retries exceeded for API error: {e}")
                    return None

            except CircuitBreakerOpenError as e:
                # Circuit breaker is open - service unavailable
                self._record_error_metric("CircuitBreakerOpen")
                logger.error(f"Circuit breaker open - service unavailable: {e}")
                return None

            except Exception as e:
                # RETRIABLE: Unknown error - cautious single retry
                self._record_error_metric("UnknownError")
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Unexpected error, retrying once: {e}",
                        exc_info=True,
                        extra={"attempt": attempt + 1},
                    )
                    time.sleep(1)
                    continue
                else:
                    logger.error(f"Failed after {max_retries} attempts: {e}", exc_info=True)
                    return None

        logger.error(f"Failed to analyze email after {max_retries} attempts")
        return None

    def analyze_note(
        self,
        note: Note,
        metadata: NoteMetadata,
        model: AIModel = AIModel.CLAUDE_SONNET,
        max_retries: int = 3,
    ) -> Optional[NoteAnalysis]:
        """
        Analyze note with AI for enrichment

        Args:
            note: Note object
            metadata: Note metadata
            model: AI model to use
            max_retries: Maximum retry attempts

        Returns:
            NoteAnalysis or None if analysis fails
        """
        from src.sancho.templates import get_template_manager

        # Acquire rate limit permission
        if not self.rate_limiter.acquire(timeout=30):
            logger.error("Rate limit timeout - could not acquire permission")
            return None

        # Prepare prompt
        tm = get_template_manager()
        try:
            prompt = tm.render(
                "ai/note_analysis",
                title=note.title,
                note_type=metadata.note_type.value if metadata.note_type else "unknown",
                content=note.content,
            )

            # Inject Global Context (Dynamic Briefing)
            if self.context_loader:
                global_context = self.context_loader.load_context()
                if global_context:
                    # Wrap the task prompt with global context using a template
                    prompt = tm.render(
                        "ai/briefing_system",
                        global_context=global_context,
                        task_prompt=prompt,
                    )
                    logger.debug("Injected global context into note analysis prompt")

        except Exception as e:
            logger.error(f"Failed to render note analysis prompt: {e}", exc_info=True)
            return None

        # Make API call
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Calling Claude API for note (attempt {attempt + 1}/{max_retries})",
                    extra={"model": model.value, "note_id": note.note_id, "title": note.title},
                )

                # Use circuit breaker
                response, api_usage = self.circuit_breaker.call(
                    self._call_claude, prompt, model, 4096
                )

                if response:
                    # Parse response
                    try:
                        # Extract JSON
                        json_start = response.find("{")
                        json_end = response.rfind("}") + 1
                        if json_start == -1 or json_end == 0:
                            raise ValueError("No JSON found in response")

                        json_str = clean_json_string(response[json_start:json_end])
                        data = json.loads(json_str)

                        analysis = NoteAnalysis(**data)

                        # Record metrics
                        duration_ms = (time.time() - start_time) * 1000
                        self._record_analysis_metrics(
                            duration_ms=duration_ms,
                            tokens=api_usage.get("total_tokens", 0),
                            input_tokens=api_usage.get("input_tokens", 0),
                            output_tokens=api_usage.get("output_tokens", 0),
                            model=model,
                        )

                        logger.info(
                            "Note analysis successful",
                            extra={
                                "note_id": note.note_id,
                                "category": analysis.category,
                                "confidence": analysis.confidence,
                                "duration_ms": duration_ms,
                            },
                        )
                        return analysis

                    except Exception as e:
                        logger.warning(f"Failed to parse note analysis: {e}")
                        # Retry on parse error? usually bad JSON from LLM
                        continue

            except Exception as e:
                # Handle general errors (circuit breaker handles its own)
                logger.error(f"Note analysis error: {e}")
                time.sleep(1)

        return None

    def analyze_with_prompt(
        self,
        prompt: str,
        model: AIModel,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        max_retries: int = 3,
    ) -> tuple[str, dict]:
        """
        Analyze with a custom prompt (for Sancho reasoning passes)

        This is a generic interface for making AI calls with custom prompts,
        used by the ReasoningEngine for multi-pass analysis.

        Args:
            prompt: User prompt to send
            model: AI model to use
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            max_retries: Maximum retry attempts

        Returns:
            Tuple of (response_text, usage_stats)

        Raises:
            Exception: If all retries fail
        """
        # Acquire rate limit permission
        if not self.rate_limiter.acquire(timeout=30):
            logger.error("Rate limit timeout - could not acquire permission")
            raise RuntimeError("Rate limit timeout")

        start_time = time.time()

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Calling Claude API with custom prompt (attempt {attempt + 1}/{max_retries})",
                    extra={"model": model.value},
                )

                # Use circuit breaker for resilience
                response, usage = self.circuit_breaker.call(
                    self._call_claude_with_system, prompt, model, system_prompt, max_tokens
                )

                if response:
                    # Record metrics
                    duration_ms = (time.time() - start_time) * 1000
                    self._record_analysis_metrics(
                        duration_ms=duration_ms,
                        tokens=usage.get("total_tokens", 0),
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        model=model,
                    )

                    return response, usage

            except self.anthropic.RateLimitError:
                self._record_error_metric("RateLimitError")
                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 60)
                    logger.warning(f"Rate limit exceeded, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue

            except self.anthropic.APIConnectionError:
                self._record_error_metric("APIConnectionError")
                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 30)
                    logger.warning(f"Connection error, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue

            except CircuitBreakerOpenError as e:
                self._record_error_metric("CircuitBreakerOpen")
                logger.error(f"Circuit breaker open: {e}")
                raise

            except Exception as e:
                self._record_error_metric("UnknownError")
                if attempt < max_retries - 1:
                    logger.warning(f"Error, retrying: {e}")
                    time.sleep(1)
                    continue
                raise

        raise RuntimeError(f"Failed after {max_retries} attempts")

    async def analyze_email_async(
        self,
        email_content: str,
        metadata: EmailMetadata,
        model: AIModel = AIModel.CLAUDE_HAIKU,
        max_retries: int = 3,
    ) -> Optional[EmailAnalysis]:
        """Async wrapper for analyze_email"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.analyze_email(email_content, metadata, model, max_retries),
        )

    async def analyze_note_async(
        self,
        note: Note,
        metadata: NoteMetadata,
        model: AIModel = AIModel.CLAUDE_SONNET,
        max_retries: int = 3,
    ) -> Optional[NoteAnalysis]:
        """Async wrapper for analyze_note"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.analyze_note(note, metadata, model, max_retries),
        )

    async def analyze_with_prompt_async(
        self,
        prompt: str,
        model: AIModel,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        max_retries: int = 3,
    ) -> tuple[str, dict]:
        """Async wrapper for analyze_with_prompt"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.analyze_with_prompt(prompt, model, system_prompt, max_tokens, max_retries),
        )

    def _call_claude_with_system(
        self,
        prompt: str,
        model: AIModel,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> tuple[Optional[str], dict]:
        """
        Call Claude API with optional system prompt

        Args:
            prompt: User prompt
            model: Model to use
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (response text or None, usage dict)
        """
        try:
            # Build request kwargs
            kwargs = {
                "model": model.value,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            message = self._client.messages.create(**kwargs)

            # Extract usage information
            input_tokens = message.usage.input_tokens if hasattr(message, "usage") else 0
            output_tokens = message.usage.output_tokens if hasattr(message, "usage") else 0

            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text, usage

            return None, usage

        except Exception as e:
            logger.error(f"Claude API call failed: {e}", exc_info=True)
            raise

    def _call_claude(
        self, prompt: str, model: AIModel, max_tokens: int = 1024
    ) -> tuple[Optional[str], dict]:
        """
        Call Claude API

        Args:
            prompt: User prompt
            model: Model to use
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (response text or None, usage dict)
        """
        try:
            message = self._client.messages.create(
                model=model.value,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract usage information
            input_tokens = message.usage.input_tokens if hasattr(message, "usage") else 0
            output_tokens = message.usage.output_tokens if hasattr(message, "usage") else 0

            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text, usage

            return None, usage

        except Exception as e:
            logger.error(f"Claude API call failed: {e}", exc_info=True)
            raise

    def _parse_analysis_response(
        self, response: str, metadata: EmailMetadata
    ) -> Optional[EmailAnalysis]:
        """
        Parse AI response into EmailAnalysis

        Supports two formats:
        1. New multi-options format (with "options" array)
        2. Legacy single-action format (backward compatible)

        Args:
            response: Claude response text
            metadata: Email metadata

        Returns:
            EmailAnalysis or None if parsing fails
        """
        try:
            # Extract JSON from response (Claude might add explanation before/after)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in response")
                return None

            json_str = response[json_start:json_end]

            # Multi-level JSON repair strategy:
            # Level 1: Try direct parse (fast, ideal case)
            # Level 2: json-repair library (robust, handles most issues)
            # Level 3: Regex cleaning + json-repair (last resort)
            data = None

            # Level 1: Try direct parse
            try:
                data = json.loads(json_str)
                logger.debug("JSON parsed directly without repair")
            except json.JSONDecodeError as e1:
                # Level 2: Try json-repair library first (handles complex cases better)
                repaired, repair_success = _repair_json_with_library(json_str)
                if repair_success:
                    try:
                        data = json.loads(repaired)
                        logger.debug("JSON repaired successfully using json-repair library")
                    except json.JSONDecodeError:
                        pass  # Will try Level 3

                # Level 3: If json-repair didn't work, try regex + json-repair
                if data is None:
                    cleaned = clean_json_string(json_str)
                    try:
                        data = json.loads(cleaned)
                        logger.debug("JSON repaired using regex cleaning")
                    except json.JSONDecodeError:
                        # Last resort: json-repair on regex-cleaned string
                        repaired2, _ = _repair_json_with_library(cleaned)
                        try:
                            data = json.loads(repaired2)
                            logger.debug("JSON repaired using regex + json-repair")
                        except json.JSONDecodeError:
                            # All methods failed, raise original error
                            raise e1 from None

            if data is None:
                raise json.JSONDecodeError("Failed to parse JSON", json_str, 0)

            # Normalize category to lowercase
            if "category" in data and isinstance(data["category"], str):
                data["category"] = data["category"].lower()

            # Check if this is the new multi-options format
            if "options" in data and isinstance(data["options"], list) and data["options"]:
                # Parse options
                parsed_options = []
                recommended_option = None

                for opt in data["options"]:
                    # Normalize action to lowercase
                    if "action" in opt and isinstance(opt["action"], str):
                        opt["action"] = opt["action"].lower()

                    parsed_options.append(opt)

                    # Find recommended option
                    if opt.get("is_recommended", False):
                        recommended_option = opt

                # If no explicit recommended, use first option
                if not recommended_option and parsed_options:
                    recommended_option = parsed_options[0]
                    parsed_options[0]["is_recommended"] = True

                # Populate main fields from recommended option
                data["options"] = parsed_options
                data["action"] = recommended_option["action"]
                data["confidence"] = recommended_option["confidence"]
                data["reasoning"] = recommended_option["reasoning"]
                data["destination"] = recommended_option.get("destination")

            else:
                # Legacy single-action format
                if "action" in data and isinstance(data["action"], str):
                    data["action"] = data["action"].lower()
                if "priority" in data and isinstance(data["priority"], str):
                    data["priority"] = data["priority"].lower()

                # Create a single option from the legacy format
                data["options"] = [
                    {
                        "action": data["action"],
                        "destination": data.get("destination"),
                        "confidence": data["confidence"],
                        "reasoning": data["reasoning"],
                        "is_recommended": True,
                    }
                ]

            # Create EmailAnalysis from parsed data
            analysis = EmailAnalysis(**data)

            logger.debug(
                "Successfully parsed analysis response",
                extra={
                    "email_id": metadata.id,
                    "options_count": len(analysis.options),
                    "format": "multi-options" if len(data.get("options", [])) > 1 else "legacy",
                },
            )

            return analysis

        except json.JSONDecodeError as e:
            # Log the error and a snippet of the problematic JSON
            snippet = ""
            if json_str and e.pos:
                start = max(0, e.pos - 60)
                end = min(len(json_str), e.pos + 40)
                snippet = json_str[start:end].replace("\n", "\\n")

            logger.error(
                f"Failed to parse JSON response: {e}",
                extra={
                    "email_id": metadata.id,
                    "error_line": e.lineno,
                    "error_col": e.colno,
                    "error_pos": e.pos,
                    "json_snippet": f"...{snippet}..." if snippet else "N/A",
                },
            )
            return None
        except Exception as e:
            logger.error(
                f"Failed to create EmailAnalysis: {e}",
                exc_info=True,
                extra={"email_id": metadata.id},
            )
            return None

    def _calculate_cost(self, model: AIModel, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate API cost in USD

        Args:
            model: AI model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        return calculate_cost(model, input_tokens, output_tokens)

    def _record_analysis_metrics(
        self, duration_ms: float, tokens: int, input_tokens: int, output_tokens: int, model: AIModel
    ) -> None:
        """
        Record metrics for analysis request

        Args:
            duration_ms: Request duration in milliseconds
            tokens: Total tokens used
            input_tokens: Input tokens
            output_tokens: Output tokens
            model: Model used
        """
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        with self._metrics_lock:
            self._metrics["total_requests"] += 1
            self._metrics["total_tokens"] += tokens
            self._metrics["total_cost_usd"] += cost

            # Track duration histogram (deque auto-trims at maxlen=1000)
            self._metrics["duration_histogram"].append(duration_ms)

    def _record_error_metric(self, error_type: str) -> None:
        """
        Record error metric

        Args:
            error_type: Type of error that occurred
        """
        with self._metrics_lock:
            if error_type not in self._metrics["errors_by_type"]:
                self._metrics["errors_by_type"][error_type] = 0
            self._metrics["errors_by_type"][error_type] += 1

    def get_ai_metrics(self) -> dict:
        """
        Get aggregated AI metrics

        Returns:
            Dict with metrics including costs, tokens, duration stats
        """
        with self._metrics_lock:
            # Copy durations from deque to list for calculations
            durations = list(self._metrics["duration_histogram"])

            # Calculate percentiles with edge case handling
            p50 = p95 = p99 = avg_duration = 0.0

            if len(durations) == 0:
                # No data points
                pass
            elif len(durations) == 1:
                # Single data point - all percentiles are the same
                p50 = p95 = p99 = avg_duration = durations[0]
            else:
                # Multiple data points - calculate properly
                sorted_durations = sorted(durations)
                n = len(sorted_durations)

                # Use proper percentile index calculation with bounds checking
                # For percentile p, index = max(0, min(n-1, int(n * p/100)))
                p50_idx = min(int(n * 0.50), n - 1)
                p95_idx = min(int(n * 0.95), n - 1)
                p99_idx = min(int(n * 0.99), n - 1)

                p50 = sorted_durations[p50_idx]
                p95 = sorted_durations[p95_idx]
                p99 = sorted_durations[p99_idx]
                avg_duration = sum(durations) / len(durations)

            return {
                "total_requests": self._metrics["total_requests"],
                "total_tokens": self._metrics["total_tokens"],
                "total_cost_usd": round(self._metrics["total_cost_usd"], 4),
                "avg_duration_ms": round(avg_duration, 2),
                "p50_duration_ms": round(p50, 2),
                "p95_duration_ms": round(p95, 2),
                "p99_duration_ms": round(p99, 2),
                "errors_by_type": self._metrics["errors_by_type"].copy(),
                "rate_limit_status": self.rate_limiter.get_current_usage(),
            }

    def get_rate_limit_status(self) -> dict[str, Any]:
        """
        Get current rate limit status

        Returns:
            Rate limit statistics
        """
        return self.rate_limiter.get_current_usage()


# Global router instance
_ai_router: Optional[AIRouter] = None
_router_lock = threading.Lock()


def get_ai_router(config: Optional[AIConfig] = None) -> AIRouter:
    """
    Get global AI router (thread-safe singleton)

    Args:
        config: AI configuration (required on first call)

    Returns:
        AIRouter instance
    """
    global _ai_router

    # Double-check locking
    if _ai_router is not None:
        return _ai_router

    with _router_lock:
        if _ai_router is None:
            if config is None:
                from src.core.config_manager import get_config

                config = get_config().ai

            _ai_router = AIRouter(config)

        return _ai_router
