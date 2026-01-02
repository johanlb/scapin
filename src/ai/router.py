"""
AI Router

Routes AI requests to appropriate models with rate limiting and retry logic.
"""

import json
import threading
import time
from collections import deque
from enum import Enum
from typing import Any, Optional

from src.core.config_manager import AIConfig
from src.core.schemas import EmailAnalysis, EmailContent, EmailMetadata
from src.monitoring.logger import get_logger

logger = get_logger("ai_router")


class AIModel(str, Enum):
    """Available AI models"""
    CLAUDE_HAIKU = "claude-3-5-haiku-20241022"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_OPUS = "claude-opus-4-20250514"


class CircuitBreakerOpenError(Exception):
    """
    Raised when circuit breaker is open (service unavailable)

    This exception indicates that the circuit breaker has detected
    repeated failures and is blocking requests to prevent cascading failures.
    """
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern for API calls

    Prevents repeated calls to failing services by "opening" the circuit
    after a threshold of failures. After a timeout period, allows a test
    request through ("half-open" state).

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Failure threshold exceeded, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery (half-open)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function raises
        """
        with self._lock:
            # Check if circuit should transition to half-open
            if self.state == "open":
                if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                    self.state = "half-open"
                    logger.info("Circuit breaker entering half-open state (testing recovery)")
                else:
                    remaining = int(self.timeout - (time.time() - (self.last_failure_time or 0)))
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN - service unavailable "
                        f"(timeout: {self.timeout}s, remaining: {remaining}s)"
                    )

        # Attempt the call
        try:
            result = func(*args, **kwargs)

            # Success - reset or close circuit
            with self._lock:
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
                    logger.info("Circuit breaker CLOSED - service recovered")

            return result

        except Exception:
            # Failure - increment counter and potentially open circuit
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.error(
                        f"Circuit breaker OPENED after {self.failure_count} failures",
                        extra={"failure_threshold": self.failure_threshold}
                    )

            raise


class RateLimiter:
    """
    Thread-safe rate limiter

    Implements sliding window rate limiting to prevent API rate limit errors.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: deque = deque()
        self._lock = threading.Lock()

        logger.debug(
            "Rate limiter initialized",
            extra={"max_requests": max_requests, "window_seconds": window_seconds}
        )

    def __repr__(self) -> str:
        """String representation for debugging"""
        with self._lock:
            return (
                f"RateLimiter(max_requests={self.max_requests}, "
                f"window={self.window_seconds}s, "
                f"current={len(self._requests)})"
            )

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()

        while True:
            with self._lock:
                # Remove old requests outside the window
                now = time.time()
                while self._requests and self._requests[0] < now - self.window_seconds:
                    self._requests.popleft()

                # Check if we can make a request
                if len(self._requests) < self.max_requests:
                    self._requests.append(now)
                    return True

            # Check timeout
            if timeout is not None and (time.time() - start_time) >= timeout:
                logger.warning("Rate limit timeout reached")
                return False

            # Wait before retrying
            time.sleep(0.1)

    def get_current_usage(self) -> dict[str, Any]:
        """
        Get current rate limiter usage

        Returns:
            Dict with usage statistics
        """
        with self._lock:
            now = time.time()
            # Clean old requests
            while self._requests and self._requests[0] < now - self.window_seconds:
                self._requests.popleft()

            return {
                "current_requests": len(self._requests),
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "usage_percent": (len(self._requests) / self.max_requests) * 100
            }


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
            max_requests=config.rate_limit_per_minute,
            window_seconds=60
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60
        )

        # Metrics tracking
        self._metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "duration_histogram": deque(maxlen=1000),  # Auto-trims at 1000 items
            "errors_by_type": {}
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
                "circuit_breaker_threshold": 5
            }
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
        max_retries: int = 3
    ) -> Optional[EmailAnalysis]:
        """
        Analyze email with AI

        Args:
            metadata: Email metadata
            content: Email content
            model: AI model to use
            max_retries: Maximum retry attempts

        Returns:
            EmailAnalysis or None if analysis fails
        """
        from src.ai.templates import get_template_manager

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
                date=metadata.date.isoformat()
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
                        "subject": metadata.subject
                    }
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
                            model=model
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
                                    api_usage.get("output_tokens", 0)
                                )
                            }
                        )
                        return analysis

            # SELECTIVE RETRY LOGIC: Different strategies for different error types

            except self.anthropic.RateLimitError:
                # RETRIABLE: Rate limit - wait and retry with backoff
                self._record_error_metric("RateLimitError")

                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 60)  # Exponential backoff, cap at 60s
                    logger.warning(
                        f"Rate limit exceeded, retrying in {wait_time}s",
                        extra={"attempt": attempt + 1, "max_retries": max_retries}
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
                    f"Authentication failed: {e}. Check API key configuration.",
                    exc_info=True
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
                    f"Invalid request: {e}. Check email content or prompt format.",
                    exc_info=True
                )
                return None

            except self.anthropic.APIConnectionError as e:
                # RETRIABLE: Network issue - retry with backoff
                self._record_error_metric("APIConnectionError")
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(
                        f"API connection error, retrying in {wait_time}s: {e}",
                        extra={"attempt": attempt + 1}
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
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(
                        f"Server error, retrying in {wait_time}s: {e}",
                        extra={"attempt": attempt + 1}
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
                    wait_time = min(2 ** attempt, 10)
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
                        extra={"attempt": attempt + 1}
                    )
                    time.sleep(1)
                    continue
                else:
                    logger.error(
                        f"Failed after {max_retries} attempts: {e}",
                        exc_info=True
                    )
                    return None

        logger.error(f"Failed to analyze email after {max_retries} attempts")
        return None

    def analyze_with_prompt(
        self,
        prompt: str,
        model: AIModel,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        max_retries: int = 3
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
                    extra={"model": model.value}
                )

                # Use circuit breaker for resilience
                response, usage = self.circuit_breaker.call(
                    self._call_claude_with_system,
                    prompt,
                    model,
                    system_prompt,
                    max_tokens
                )

                if response:
                    # Record metrics
                    duration_ms = (time.time() - start_time) * 1000
                    self._record_analysis_metrics(
                        duration_ms=duration_ms,
                        tokens=usage.get("total_tokens", 0),
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        model=model
                    )

                    return response, usage

            except self.anthropic.RateLimitError:
                self._record_error_metric("RateLimitError")
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 60)
                    logger.warning(f"Rate limit exceeded, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue

            except self.anthropic.APIConnectionError:
                self._record_error_metric("APIConnectionError")
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)
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

    def _call_claude_with_system(
        self,
        prompt: str,
        model: AIModel,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048
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
                "messages": [{"role": "user", "content": prompt}]
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            message = self._client.messages.create(**kwargs)

            # Extract usage information
            input_tokens = message.usage.input_tokens if hasattr(message, 'usage') else 0
            output_tokens = message.usage.output_tokens if hasattr(message, 'usage') else 0

            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text, usage

            return None, usage

        except Exception as e:
            logger.error(f"Claude API call failed: {e}", exc_info=True)
            raise

    def _call_claude(
        self,
        prompt: str,
        model: AIModel,
        max_tokens: int = 1024
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
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract usage information
            input_tokens = message.usage.input_tokens if hasattr(message, 'usage') else 0
            output_tokens = message.usage.output_tokens if hasattr(message, 'usage') else 0

            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text, usage

            return None, usage

        except Exception as e:
            logger.error(f"Claude API call failed: {e}", exc_info=True)
            raise

    def _parse_analysis_response(
        self,
        response: str,
        metadata: EmailMetadata
    ) -> Optional[EmailAnalysis]:
        """
        Parse AI response into EmailAnalysis

        Expected JSON format:
        {
            "action": "ARCHIVE" | "DELETE" | "TASK" | "REPLY" | "DEFER" | "QUEUE",
            "category": "WORK" | "PERSONAL" | "FINANCE" | "SHOPPING" | "NEWSLETTER" | "SOCIAL" | "SPAM",
            "destination": "Archive/2025/Work",
            "confidence": 95,
            "reasoning": "Work-related project update...",
            "tags": ["work", "project", "update"],
            "entities": {
                "people": ["John Doe"],
                "projects": ["Q1 Project"],
                "dates": ["2025-01-15"]
            },
            "omnifocus_task": {
                "title": "Review Q1 project update",
                "note": "...",
                "defer_date": "2025-01-16",
                "due_date": "2025-01-20",
                "tags": ["work"]
            },
            "needs_full_content": false
        }

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
            data = json.loads(json_str)

            # Normalize enum values to lowercase (AI sometimes returns uppercase)
            if 'action' in data and isinstance(data['action'], str):
                data['action'] = data['action'].lower()
            if 'category' in data and isinstance(data['category'], str):
                data['category'] = data['category'].lower()
            if 'priority' in data and isinstance(data['priority'], str):
                data['priority'] = data['priority'].lower()

            # Create EmailAnalysis from parsed data
            analysis = EmailAnalysis(**data)

            logger.debug(
                "Successfully parsed analysis response",
                extra={"email_id": metadata.id}
            )

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}", exc_info=True)
            logger.debug(f"Response text: {response[:500]}")
            return None
        except Exception as e:
            logger.error(f"Failed to create EmailAnalysis: {e}", exc_info=True)
            return None

    def _calculate_cost(
        self,
        model: AIModel,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate API cost in USD

        Args:
            model: AI model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Pricing as of January 2025
        pricing = {
            AIModel.CLAUDE_OPUS: {
                "input": 15.00 / 1_000_000,   # $15 per MTok
                "output": 75.00 / 1_000_000   # $75 per MTok
            },
            AIModel.CLAUDE_SONNET: {
                "input": 3.00 / 1_000_000,    # $3 per MTok
                "output": 15.00 / 1_000_000   # $15 per MTok
            },
            AIModel.CLAUDE_HAIKU: {
                "input": 0.25 / 1_000_000,    # $0.25 per MTok
                "output": 1.25 / 1_000_000    # $1.25 per MTok
            }
        }

        rates = pricing.get(model, pricing[AIModel.CLAUDE_HAIKU])
        return (input_tokens * rates["input"]) + (output_tokens * rates["output"])

    def _record_analysis_metrics(
        self,
        duration_ms: float,
        tokens: int,
        input_tokens: int,
        output_tokens: int,
        model: AIModel
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
                "rate_limit_status": self.rate_limiter.get_current_usage()
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
