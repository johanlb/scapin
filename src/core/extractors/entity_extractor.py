"""
Entity Extractor

Multi-strategy entity extraction from text:
1. Regex patterns (high precision, fast)
2. Heuristics (names, organizations)
3. Optional AI validation (enrichment)

Supports French and English text.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from src.core.entities import Entity, EntitySource, EntityType
from src.monitoring.logger import get_logger

logger = get_logger("core.entity_extractor")


@dataclass
class EntityExtractor:
    """
    Extraction d'entités multi-stratégie.

    Utilise une combinaison de regex, heuristiques et optionnellement
    validation IA pour extraire des entités structurées du texte.
    """

    # Confidence scores for different extraction methods
    REGEX_CONFIDENCE: float = 0.95
    HEURISTIC_CONFIDENCE: float = 0.80
    METADATA_CONFIDENCE: float = 0.98

    # Regex patterns
    EMAIL_PATTERN: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )
    )

    PHONE_FR_PATTERN: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"(?:\+33|0)\s*[1-9](?:[\s.-]*\d{2}){4}"
        )
    )

    PHONE_INTL_PATTERN: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"\+\d{1,3}[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9}"
        )
    )

    URL_PATTERN: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
        )
    )

    # Amount patterns (EUR, USD, etc.)
    AMOUNT_PATTERN: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"(\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d{1,2})?)\s*(€|EUR|euros?|USD|\$|dollars?|k€|K€|M€)",
            re.IGNORECASE,
        )
    )

    # Date patterns (French)
    DATE_FR_PATTERNS: list[tuple[re.Pattern[str], str]] = field(
        default_factory=lambda: [
            # "15 janvier 2026", "15 jan 2026"
            (
                re.compile(
                    r"(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|"
                    r"août|septembre|octobre|novembre|décembre|"
                    r"jan|fév|mar|avr|mai|juin|juil|août|sept|oct|nov|déc)\.?\s+(\d{4})",
                    re.IGNORECASE,
                ),
                "full_date",
            ),
            # "15/01/2026", "15-01-2026"
            (re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})"), "numeric_date"),
            # "demain", "aujourd'hui", "lundi prochain"
            (
                re.compile(
                    r"\b(demain|aujourd'hui|après-demain|"
                    r"lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s*(prochain|dernier)?\b",
                    re.IGNORECASE,
                ),
                "relative_date",
            ),
            # "d'ici le 15", "avant le 20"
            (
                re.compile(
                    r"(d'ici|avant|pour)\s+le\s+(\d{1,2})(?:\s+(janvier|février|mars|avril|mai|juin|"
                    r"juillet|août|septembre|octobre|novembre|décembre))?",
                    re.IGNORECASE,
                ),
                "deadline",
            ),
        ]
    )

    # Date patterns (English)
    DATE_EN_PATTERNS: list[tuple[re.Pattern[str], str]] = field(
        default_factory=lambda: [
            # "January 15, 2026", "Jan 15 2026"
            (
                re.compile(
                    r"(January|February|March|April|May|June|July|August|September|"
                    r"October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                    r"\.?\s+(\d{1,2}),?\s+(\d{4})",
                    re.IGNORECASE,
                ),
                "full_date",
            ),
            # "2026-01-15" (ISO format)
            (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "iso_date"),
            # "01/15/2026" (US format)
            (re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"), "numeric_date_us"),
            # "tomorrow", "next Monday"
            (
                re.compile(
                    r"\b(tomorrow|today|next\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))\b",
                    re.IGNORECASE,
                ),
                "relative_date",
            ),
            # "by the 15th", "before January 20"
            (
                re.compile(
                    r"(by|before|until)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?(?:\s+of\s+)?"
                    r"(January|February|March|April|May|June|July|August|September|"
                    r"October|November|December)?",
                    re.IGNORECASE,
                ),
                "deadline",
            ),
        ]
    )

    # Greeting patterns for person extraction
    GREETING_PATTERNS: list[re.Pattern[str]] = field(
        default_factory=lambda: [
            # French greetings (with hyphenated names like Jean-Pierre)
            re.compile(r"(?:Bonjour|Bonsoir|Salut|Cher|Chère|Hello)\s+([A-Z][a-zéèêëàâùûôîïç]+(?:-[A-Z][a-zéèêëàâùûôîïç]+)?)", re.UNICODE),
            # English greetings (with hyphenated names)
            re.compile(r"(?:Dear|Hi|Hello)\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)"),
            # Signature patterns
            re.compile(r"(?:Cordialement|Bien\s+cordialement|Best\s+regards|Regards),?\s*\n\s*([A-Z][a-zéèêëàâùûôîïç]+(?:-[A-Z][a-zéèêëàâùûôîïç]+)?\s+[A-Z][a-zéèêëàâùûôîïç]+(?:-[A-Z][a-zéèêëàâùûôîïç]+)?)", re.UNICODE),
        ]
    )

    # Organization patterns
    ORG_PATTERNS: list[re.Pattern[str]] = field(
        default_factory=lambda: [
            # Company suffixes
            re.compile(r"([A-Z][A-Za-z0-9\s&]+)\s+(?:SA|SAS|SARL|SNC|GmbH|Ltd|Inc|LLC|Corp|Pty|BV|AG)\b"),
            # Common organization words
            re.compile(r"(?:chez|at|@)\s+([A-Z][A-Za-z0-9\s&]+(?:Group|Company|Corporation|Organization|Team|Department)?)", re.IGNORECASE),
        ]
    )

    def extract(
        self,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Entity]:
        """
        Extract entities from text.

        Args:
            text: Text content to analyze
            metadata: Optional email metadata (sender, recipients, etc.)

        Returns:
            List of extracted entities
        """
        if not text:
            return []

        entities: list[Entity] = []

        # Pass 1: Extract from metadata (highest confidence)
        if metadata:
            entities.extend(self._extract_from_metadata(metadata))

        # Pass 2: Regex extraction (high precision)
        entities.extend(self._extract_emails(text))
        entities.extend(self._extract_phones(text))
        entities.extend(self._extract_urls(text))
        entities.extend(self._extract_amounts(text))
        entities.extend(self._extract_dates(text))

        # Pass 3: Heuristic extraction
        entities.extend(self._extract_persons_heuristic(text))
        entities.extend(self._extract_organizations(text))

        # Deduplicate
        entities = self._deduplicate(entities)

        logger.debug(f"Extracted {len(entities)} entities from text")
        return entities

    def _extract_from_metadata(self, metadata: dict[str, Any]) -> list[Entity]:
        """Extract entities from email metadata (sender, recipients)."""
        entities = []

        # Sender
        if sender := metadata.get("sender"):
            # Handle malformed sender (string instead of dict)
            if not isinstance(sender, dict):
                logger.warning(f"Malformed sender in metadata: {type(sender)}")
                return entities
            name = sender.get("name", "")
            email = sender.get("email", "")
            if name or email:
                entities.append(
                    Entity(
                        type=EntityType.PERSON,
                        value=name or email,
                        normalized=name if name else None,
                        confidence=self.METADATA_CONFIDENCE,
                        source=EntitySource.EXTRACTION,
                        metadata={"email": email, "role": "sender"},
                    )
                )

        # Recipients (To)
        for recipient in metadata.get("recipients", []):
            name = recipient.get("name", "")
            email = recipient.get("email", "")
            if name or email:
                entities.append(
                    Entity(
                        type=EntityType.PERSON,
                        value=name or email,
                        normalized=name if name else None,
                        confidence=self.METADATA_CONFIDENCE,
                        source=EntitySource.EXTRACTION,
                        metadata={"email": email, "role": "recipient"},
                    )
                )

        # CC
        for cc in metadata.get("cc", []):
            name = cc.get("name", "")
            email = cc.get("email", "")
            if name or email:
                entities.append(
                    Entity(
                        type=EntityType.PERSON,
                        value=name or email,
                        normalized=name if name else None,
                        confidence=self.METADATA_CONFIDENCE * 0.95,  # Slightly lower for CC
                        source=EntitySource.EXTRACTION,
                        metadata={"email": email, "role": "cc"},
                    )
                )

        return entities

    def _extract_emails(self, text: str) -> list[Entity]:
        """Extract email addresses from text."""
        entities = []
        for match in self.EMAIL_PATTERN.finditer(text):
            email = match.group()
            # Extract domain for metadata
            domain = email.split("@")[1] if "@" in email else ""
            entities.append(
                Entity(
                    type=EntityType.PERSON,  # Email implies a person
                    value=email,
                    confidence=self.REGEX_CONFIDENCE,
                    source=EntitySource.EXTRACTION,
                    metadata={"email": email, "domain": domain, "role": "mentioned"},
                )
            )
        return entities

    def _extract_phones(self, text: str) -> list[Entity]:
        """Extract phone numbers from text."""
        entities = []

        # French phone numbers
        for match in self.PHONE_FR_PATTERN.finditer(text):
            phone = match.group()
            # Normalize: remove spaces/dashes
            normalized = re.sub(r"[\s.-]", "", phone)
            entities.append(
                Entity(
                    type=EntityType.PHONE,
                    value=phone,
                    normalized=normalized,
                    confidence=self.REGEX_CONFIDENCE,
                    source=EntitySource.EXTRACTION,
                    metadata={"country": "FR", "formatted": self._format_phone_fr(normalized)},
                )
            )

        # International phone numbers
        for match in self.PHONE_INTL_PATTERN.finditer(text):
            phone = match.group()
            normalized = re.sub(r"[\s.-]", "", phone)
            # Skip if already captured as FR
            if not any(e.normalized == normalized for e in entities):
                entities.append(
                    Entity(
                        type=EntityType.PHONE,
                        value=phone,
                        normalized=normalized,
                        confidence=self.REGEX_CONFIDENCE * 0.9,  # Slightly lower for intl
                        source=EntitySource.EXTRACTION,
                        metadata={"type": "international"},
                    )
                )

        return entities

    def _format_phone_fr(self, phone: str) -> str:
        """Format French phone number."""
        # Remove +33 prefix and normalize to 0X XX XX XX XX
        if phone.startswith("+33"):
            phone = "0" + phone[3:]
        if len(phone) == 10:
            return f"{phone[0:2]} {phone[2:4]} {phone[4:6]} {phone[6:8]} {phone[8:10]}"
        return phone

    def _extract_urls(self, text: str) -> list[Entity]:
        """Extract URLs from text."""
        entities = []
        for match in self.URL_PATTERN.finditer(text):
            url = match.group()
            # Add https:// if missing
            if url.startswith("www."):
                url = "https://" + url
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                entities.append(
                    Entity(
                        type=EntityType.URL,
                        value=url,
                        normalized=url,
                        confidence=self.REGEX_CONFIDENCE,
                        source=EntitySource.EXTRACTION,
                        metadata={"domain": domain, "path": parsed.path},
                    )
                )
            except Exception:
                # Invalid URL, skip
                pass
        return entities

    def _extract_amounts(self, text: str) -> list[Entity]:
        """Extract monetary amounts from text."""
        entities = []
        for match in self.AMOUNT_PATTERN.finditer(text):
            value_str = match.group(1)
            currency_str = match.group(2)

            # Normalize value
            value_str = value_str.replace(" ", "").replace(",", ".")
            try:
                value = float(value_str)
            except ValueError:
                continue

            # Normalize currency
            currency = self._normalize_currency(currency_str)

            # Handle k€, M€ multipliers
            if currency_str.lower() in ("k€", "k€"):
                value *= 1000
            elif currency_str.lower() in ("m€",):
                value *= 1_000_000

            entities.append(
                Entity(
                    type=EntityType.AMOUNT,
                    value=match.group(),
                    normalized=f"{value:.2f} {currency}",
                    confidence=self.REGEX_CONFIDENCE,
                    source=EntitySource.EXTRACTION,
                    metadata={"value": value, "currency": currency},
                )
            )

        return entities

    def _normalize_currency(self, currency: str) -> str:
        """Normalize currency string to ISO code."""
        currency_lower = currency.lower()
        if currency_lower in ("€", "eur", "euro", "euros", "k€", "m€"):
            return "EUR"
        elif currency_lower in ("$", "usd", "dollar", "dollars"):
            return "USD"
        return currency.upper()

    def _extract_dates(self, text: str) -> list[Entity]:
        """Extract dates from text."""
        entities = []

        # French patterns
        for pattern, date_type in self.DATE_FR_PATTERNS:
            for match in pattern.finditer(text):
                entities.append(
                    Entity(
                        type=EntityType.DATE,
                        value=match.group(),
                        confidence=self.REGEX_CONFIDENCE if date_type == "full_date" else self.HEURISTIC_CONFIDENCE,
                        source=EntitySource.EXTRACTION,
                        metadata={"type": date_type, "language": "fr"},
                    )
                )

        # English patterns
        for pattern, date_type in self.DATE_EN_PATTERNS:
            for match in pattern.finditer(text):
                # Avoid duplicates with French
                if not any(e.value == match.group() for e in entities):
                    entities.append(
                        Entity(
                            type=EntityType.DATE,
                            value=match.group(),
                            confidence=self.REGEX_CONFIDENCE if date_type == "full_date" else self.HEURISTIC_CONFIDENCE,
                            source=EntitySource.EXTRACTION,
                            metadata={"type": date_type, "language": "en"},
                        )
                    )

        return entities

    def _extract_persons_heuristic(self, text: str) -> list[Entity]:
        """Extract person names using heuristics."""
        entities = []

        for pattern in self.GREETING_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if len(name) > 1:  # Avoid single letters
                    entities.append(
                        Entity(
                            type=EntityType.PERSON,
                            value=name,
                            confidence=self.HEURISTIC_CONFIDENCE,
                            source=EntitySource.EXTRACTION,
                            metadata={"extraction_method": "greeting_pattern"},
                        )
                    )

        return entities

    def _extract_organizations(self, text: str) -> list[Entity]:
        """Extract organization names."""
        entities = []

        for pattern in self.ORG_PATTERNS:
            for match in pattern.finditer(text):
                org_name = match.group(1).strip() if match.lastindex else match.group().strip()
                if len(org_name) > 2:  # Avoid very short matches
                    entities.append(
                        Entity(
                            type=EntityType.ORGANIZATION,
                            value=org_name,
                            confidence=self.HEURISTIC_CONFIDENCE,
                            source=EntitySource.EXTRACTION,
                            metadata={"extraction_method": "org_pattern"},
                        )
                    )

        return entities

    def _deduplicate(self, entities: list[Entity]) -> list[Entity]:
        """
        Deduplicate entities, keeping highest confidence version.

        Merges entities with same type and similar value.
        """
        seen: dict[tuple[EntityType, str], Entity] = {}

        for entity in entities:
            # Normalize key for comparison
            key = (entity.type, entity.value.lower().strip())

            if key in seen:
                # Keep the one with higher confidence
                if entity.confidence > seen[key].confidence:
                    # Merge metadata
                    merged_metadata = {**seen[key].metadata, **entity.metadata}
                    entity.metadata = merged_metadata
                    seen[key] = entity
                else:
                    # Merge metadata into existing
                    seen[key].metadata.update(entity.metadata)
            else:
                seen[key] = entity

        return list(seen.values())


# Singleton instance
_extractor: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """Get the singleton EntityExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor
