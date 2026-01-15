"""
Email Pre-Filter Module

Filters out marketing and transactional emails before analysis to:
- Save API costs (no need to analyze spam/newsletters)
- Reduce noise in the extraction pipeline
- Focus on actionable emails

Filter Categories:
- SKIP: Pure marketing, newsletters, no value (skip entirely)
- PROCESS_LIGHT: Transactional with reference value (invoices, confirmations)
- PROCESS_FULL: Regular emails requiring full analysis

Design Decision:
- Be conservative: when in doubt, PROCESS_FULL
- Invoices and order confirmations need processing for references/amounts
- Newsletters and pure marketing can be skipped
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.core.events.universal_event import PerceivedEvent

logger = get_logger("email_filter")


class FilterResult(Enum):
    """Result of email pre-filtering"""

    SKIP = "skip"  # Skip entirely - pure marketing, no value
    PROCESS_LIGHT = "process_light"  # Light processing - extract refs/amounts only
    PROCESS_FULL = "process_full"  # Full analysis


@dataclass
class FilterDecision:
    """Decision from the email filter"""

    result: FilterResult
    reason: str
    confidence: float  # 0.0 to 1.0
    patterns_matched: list[str]


# Sender patterns that indicate marketing/newsletters (skip entirely)
SKIP_SENDER_PATTERNS = [
    # Generic marketing addresses
    "noreply@",
    "no-reply@",
    "newsletter@",
    "newsletters@",
    "marketing@",
    "promotions@",
    "offers@",
    "digest@",
    "news@",
    "info@",  # Often used for newsletters
    "notifications@",
    "updates@",
    "announce@",
    "bulletin@",
    "campaign@",
    "promo@",
    # Common newsletter services
    "mailchimp.com",
    "sendgrid.net",
    "constantcontact.com",
    "mailgun.org",
    "sendinblue.com",
    "klaviyo.com",
    "hubspot.com",
    "drip.com",
    # Social media notifications
    "linkedin.com",
    "facebookmail.com",
    "twitter.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    # Advertising platforms
    "google-ads@",
    "ads-noreply@",
]

# Sender patterns for transactional emails (process lightly for refs)
TRANSACTIONAL_SENDER_PATTERNS = [
    # Order confirmations
    "order@",
    "orders@",
    "commande@",
    "commandes@",
    "confirmation@",
    "confirmations@",
    # Invoices
    "facture@",
    "factures@",
    "invoice@",
    "invoices@",
    "billing@",
    "facturation@",
    # Account notifications
    "account@",
    "compte@",
    "security@",
    "support@",
    # Shipping
    "shipping@",
    "livraison@",
    "tracking@",
    "suivi@",
]

# Subject patterns for marketing (skip)
SKIP_SUBJECT_PATTERNS = [
    "newsletter",
    "unsubscribe",
    "se désabonner",
    "désinscrire",
    "weekly digest",
    "daily digest",
    "votre sélection",
    "nos offres",
    "soldes",
    "promotion",
    "% off",
    "% de réduction",
    "dernière chance",
    "offre exclusive",
    "vente flash",
    "black friday",
    "cyber monday",
]

# Subject patterns for transactional (process light)
TRANSACTIONAL_SUBJECT_PATTERNS = [
    "confirmation de commande",
    "order confirmation",
    "votre commande",
    "your order",
    "facture",
    "invoice",
    "reçu",
    "receipt",
    "livraison",
    "shipping",
    "expédition",
    "votre compte",
    "your account",
    "mot de passe",
    "password",
    "connexion",
    "login",
    # Banking/Financial
    "votre carte",
    "your card",
    "virement",
    "transfer",
    "prélèvement",
    "direct debit",
    "relevé",
    "statement",
]

# Protected sender domains - NEVER skip these (financial, banking, etc.)
PROTECTED_SENDER_DOMAINS = [
    # French banks
    "ca-paris.fr",
    "credit-agricole.fr",
    "bnpparibas.fr",
    "societegenerale.fr",
    "banquepopulaire.fr",
    "lcl.fr",
    "labanquepostale.fr",
    "cic.fr",
    "hsbc.fr",
    # Mauritian banks
    "afrasiabank.com",
    "mcb.mu",
    "sbmbank.mu",
    "absa.mu",
    # International
    "paypal.com",
    "stripe.com",
    "wise.com",
    "revolut.com",
]


class EmailFilter:
    """
    Pre-filter for emails before analysis.

    Usage:
        filter = EmailFilter()
        decision = filter.should_process(event)
        if decision.result == FilterResult.SKIP:
            # Skip this email entirely
            pass
        elif decision.result == FilterResult.PROCESS_LIGHT:
            # Extract references/amounts only
            pass
        else:
            # Full analysis
            pass
    """

    def __init__(
        self,
        skip_sender_patterns: list[str] | None = None,
        transactional_patterns: list[str] | None = None,
        strict_mode: bool = False,
    ):
        """
        Initialize the email filter.

        Args:
            skip_sender_patterns: Additional patterns to skip (merged with defaults)
            transactional_patterns: Additional transactional patterns
            strict_mode: If True, be more aggressive in filtering (default: conservative)
        """
        self.skip_sender_patterns = SKIP_SENDER_PATTERNS.copy()
        if skip_sender_patterns:
            self.skip_sender_patterns.extend(skip_sender_patterns)

        self.transactional_patterns = TRANSACTIONAL_SENDER_PATTERNS.copy()
        if transactional_patterns:
            self.transactional_patterns.extend(transactional_patterns)

        self.strict_mode = strict_mode

        logger.info(
            "EmailFilter initialized",
            extra={
                "skip_patterns": len(self.skip_sender_patterns),
                "transactional_patterns": len(self.transactional_patterns),
                "strict_mode": strict_mode,
            },
        )

    def should_process(self, event: "PerceivedEvent") -> FilterDecision:
        """
        Determine how to process this email event.

        Args:
            event: The email event to analyze

        Returns:
            FilterDecision with result, reason, and patterns matched
        """
        patterns_matched: list[str] = []

        # Get sender email (lowercase)
        # Handle both PerceivedEvent.from_person (str) and mock sender.email
        sender_email = ""
        if hasattr(event, "from_person") and event.from_person:
            sender_email = event.from_person.lower()
        elif hasattr(event, "sender") and event.sender:
            # For mocks in tests
            sender_email = (event.sender.email or "").lower()

        # Get subject (lowercase)
        subject = (event.title or "").lower()

        # Check for SKIP patterns (marketing/newsletters)
        for pattern in self.skip_sender_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in sender_email:
                patterns_matched.append(f"sender:{pattern}")

        # Check subject skip patterns
        for pattern in SKIP_SUBJECT_PATTERNS:
            pattern_lower = pattern.lower()
            if pattern_lower in subject:
                patterns_matched.append(f"subject:{pattern}")

        # If we matched skip patterns, decide based on count and type
        if patterns_matched:
            # NEVER skip protected domains (banks, financial services)
            if self._is_protected_sender(sender_email):
                logger.info(
                    "Protected sender detected - not skipping",
                    extra={"sender": sender_email, "patterns_matched": patterns_matched},
                )
                # Fall through to transactional check below
            else:
                # Multiple patterns = high confidence skip
                if len(patterns_matched) >= 2:
                    return FilterDecision(
                        result=FilterResult.SKIP,
                        reason=f"Marketing email detected ({len(patterns_matched)} patterns)",
                        confidence=0.95,
                        patterns_matched=patterns_matched,
                    )

                # Single pattern = moderate confidence
                # Check if it might be transactional (don't skip invoices!)
                if not self._is_transactional(sender_email, subject):
                    return FilterDecision(
                        result=FilterResult.SKIP,
                        reason="Likely marketing email",
                        confidence=0.75,
                        patterns_matched=patterns_matched,
                    )

        # Check for transactional patterns
        transactional_patterns: list[str] = []
        for pattern in self.transactional_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in sender_email:
                transactional_patterns.append(f"sender:{pattern}")

        for pattern in TRANSACTIONAL_SUBJECT_PATTERNS:
            pattern_lower = pattern.lower()
            if pattern_lower in subject:
                transactional_patterns.append(f"subject:{pattern}")

        if transactional_patterns:
            return FilterDecision(
                result=FilterResult.PROCESS_LIGHT,
                reason="Transactional email - extract references only",
                confidence=0.80,
                patterns_matched=transactional_patterns,
            )

        # Default: full processing
        return FilterDecision(
            result=FilterResult.PROCESS_FULL,
            reason="Regular email - full analysis",
            confidence=1.0,
            patterns_matched=[],
        )

    def _is_transactional(self, sender_email: str, subject: str) -> bool:
        """Check if email is transactional (invoices, confirmations)"""
        if any(pattern.lower() in sender_email for pattern in self.transactional_patterns):
            return True
        return any(pattern.lower() in subject for pattern in TRANSACTIONAL_SUBJECT_PATTERNS)

    def _is_protected_sender(self, sender_email: str) -> bool:
        """Check if sender is from a protected domain (banks, financial services)"""
        return any(
            domain.lower() in sender_email for domain in PROTECTED_SENDER_DOMAINS
        )


# Singleton instance
_email_filter: EmailFilter | None = None


def get_email_filter() -> EmailFilter:
    """Get the singleton EmailFilter instance"""
    global _email_filter
    if _email_filter is None:
        _email_filter = EmailFilter()
    return _email_filter
