"""
Email Analyzer

Wraps AI analysis functionality for email processing.

Responsibilities:
- Call AI router for email analysis
- Handle AI-specific errors
- Provide clean analysis interface
"""

from typing import Optional

from src.core.exceptions import AIAnalysisError, RateLimitError
from src.core.schemas import EmailAnalysis, EmailContent, EmailMetadata
from src.monitoring.logger import get_logger

logger = get_logger("email_analyzer")


class EmailAnalyzer:
    """
    Analyzes emails using AI

    Provides a clean interface to AI analysis with proper error handling.
    Delegates actual AI calls to AIRouter.

    Usage:
        from src.ai.router import get_ai_router

        analyzer = EmailAnalyzer(get_ai_router())
        analysis = analyzer.analyze(metadata, content)
    """

    def __init__(self, ai_router):
        """
        Initialize analyzer

        Args:
            ai_router: AIRouter instance for making AI calls
        """
        self.ai_router = ai_router

    def analyze(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        preview_mode: bool = False
    ) -> Optional[EmailAnalysis]:
        """
        Analyze email using AI

        Args:
            metadata: Email metadata
            content: Prepared email content
            preview_mode: If True, use faster/cheaper AI model

        Returns:
            EmailAnalysis result, or None if analysis fails

        Raises:
            RateLimitError: If rate limit is exceeded
            AIAnalysisError: If analysis fails for other reasons
        """
        try:
            # Delegate to AI router
            analysis = self.ai_router.analyze_email(
                metadata=metadata,
                content=content,
                preview_mode=preview_mode
            )

            if analysis is None:
                logger.warning(
                    f"AI analysis returned None for email {metadata.message_id}"
                )
                return None

            logger.debug(
                "Email analyzed successfully",
                extra={
                    "email_id": metadata.message_id,
                    "action": analysis.action,
                    "confidence": analysis.confidence
                }
            )

            return analysis

        except RateLimitError:
            logger.warning(
                "Rate limit exceeded during analysis",
                extra={"email_id": metadata.message_id}
            )
            raise

        except Exception as e:
            logger.error(
                f"Analysis failed for email {metadata.message_id}: {e}",
                exc_info=True
            )
            # Wrap in AIAnalysisError for consistent error handling
            raise AIAnalysisError(
                f"Failed to analyze email: {e}",
                details={"email_id": metadata.message_id}
            ) from e
