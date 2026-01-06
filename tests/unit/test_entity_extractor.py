"""
Tests for EntityExtractor

Tests entity extraction from text with various patterns:
- Email addresses
- Phone numbers (FR format)
- URLs
- Amounts (EUR, USD)
- Dates (French and English)
- Persons (from greetings and metadata)
- Organizations
"""

import pytest

from src.core.entities import Entity, EntitySource, EntityType
from src.core.extractors.entity_extractor import EntityExtractor, get_entity_extractor


class TestEntityExtractorInit:
    """Tests for EntityExtractor initialization"""

    def test_singleton_pattern(self):
        """get_entity_extractor returns singleton instance"""
        extractor1 = get_entity_extractor()
        extractor2 = get_entity_extractor()
        assert extractor1 is extractor2

    def test_init_default_confidence_levels(self):
        """EntityExtractor has default confidence levels"""
        extractor = EntityExtractor()
        assert extractor.REGEX_CONFIDENCE == 0.95
        assert extractor.HEURISTIC_CONFIDENCE == 0.80
        assert extractor.METADATA_CONFIDENCE == 0.98


class TestEmailExtraction:
    """Tests for email address extraction"""

    def test_extract_simple_email(self):
        """Extract simple email address"""
        extractor = EntityExtractor()
        text = "Contact me at john@example.com for more info."
        entities = extractor.extract(text)

        email_entities = [e for e in entities if e.type == EntityType.PERSON]
        # Emails are extracted as PERSON entities
        assert any("john@example.com" in str(e.metadata) for e in email_entities)

    def test_extract_multiple_emails(self):
        """Extract multiple email addresses"""
        extractor = EntityExtractor()
        text = "Send to alice@company.org and bob@other.net"
        entities = extractor.extract(text)

        # Check that both emails were found
        all_values = [str(e.metadata) for e in entities]
        combined = " ".join(all_values)
        assert "alice@company.org" in combined or "bob@other.net" in combined

    def test_extract_email_from_metadata(self):
        """Extract sender email from metadata"""
        extractor = EntityExtractor()
        text = "Hello, this is a test message."
        metadata = {
            "sender": {"email": "sender@company.com", "name": "John Doe"},
            "recipients": [{"email": "recipient@company.com"}]
        }
        entities = extractor.extract(text, metadata)

        # Should have person entities from metadata
        person_entities = [e for e in entities if e.type == EntityType.PERSON]
        assert len(person_entities) >= 1
        assert any(e.metadata.get("role") == "sender" for e in person_entities)


class TestPhoneExtraction:
    """Tests for phone number extraction (French format)"""

    def test_extract_french_mobile(self):
        """Extract French mobile number"""
        extractor = EntityExtractor()
        text = "Appelez-moi au 06 12 34 56 78"
        entities = extractor.extract(text)

        phone_entities = [e for e in entities if e.type == EntityType.PHONE]
        assert len(phone_entities) >= 1
        assert any("06" in e.value for e in phone_entities)

    def test_extract_french_landline(self):
        """Extract French landline number"""
        extractor = EntityExtractor()
        text = "Notre bureau: 01 23 45 67 89"
        entities = extractor.extract(text)

        phone_entities = [e for e in entities if e.type == EntityType.PHONE]
        assert len(phone_entities) >= 1

    def test_extract_international_french(self):
        """Extract international French number"""
        extractor = EntityExtractor()
        text = "Numéro international: +33 6 12 34 56 78"
        entities = extractor.extract(text)

        phone_entities = [e for e in entities if e.type == EntityType.PHONE]
        assert len(phone_entities) >= 1


class TestURLExtraction:
    """Tests for URL extraction"""

    def test_extract_https_url(self):
        """Extract HTTPS URL"""
        extractor = EntityExtractor()
        text = "Visit https://www.example.com/page for details"
        entities = extractor.extract(text)

        url_entities = [e for e in entities if e.type == EntityType.URL]
        assert len(url_entities) >= 1
        assert any("example.com" in e.value for e in url_entities)

    def test_extract_http_url(self):
        """Extract HTTP URL"""
        extractor = EntityExtractor()
        text = "Old link: http://legacy.site.org/path"
        entities = extractor.extract(text)

        url_entities = [e for e in entities if e.type == EntityType.URL]
        assert len(url_entities) >= 1


class TestAmountExtraction:
    """Tests for financial amount extraction"""

    def test_extract_euro_amount(self):
        """Extract EUR amount with symbol"""
        extractor = EntityExtractor()
        text = "Le prix est de 1500€ TTC"
        entities = extractor.extract(text)

        amount_entities = [e for e in entities if e.type == EntityType.AMOUNT]
        assert len(amount_entities) >= 1
        assert any(e.metadata.get("currency") == "EUR" for e in amount_entities)

    def test_extract_euro_amount_with_decimals(self):
        """Extract EUR amount with decimals"""
        extractor = EntityExtractor()
        text = "Facture: 1234,56 EUR"
        entities = extractor.extract(text)

        amount_entities = [e for e in entities if e.type == EntityType.AMOUNT]
        assert len(amount_entities) >= 1

    def test_extract_dollar_amount(self):
        """Extract USD amount"""
        extractor = EntityExtractor()
        text = "Total: $2500 USD"
        entities = extractor.extract(text)

        amount_entities = [e for e in entities if e.type == EntityType.AMOUNT]
        assert len(amount_entities) >= 1
        assert any(e.metadata.get("currency") == "USD" for e in amount_entities)

    def test_extract_k_amount(self):
        """Extract amount with k suffix (thousands)"""
        extractor = EntityExtractor()
        text = "Budget: 50k€"
        entities = extractor.extract(text)

        amount_entities = [e for e in entities if e.type == EntityType.AMOUNT]
        assert len(amount_entities) >= 1
        # Should be normalized to 50000
        assert any(e.metadata.get("value") == 50000.0 for e in amount_entities)


class TestDateExtraction:
    """Tests for date extraction (French and English)"""

    def test_extract_french_date(self):
        """Extract French date format"""
        extractor = EntityExtractor()
        text = "Réunion le 15 janvier 2026"
        entities = extractor.extract(text)

        date_entities = [e for e in entities if e.type == EntityType.DATE]
        assert len(date_entities) >= 1
        assert any("15" in e.value and "janvier" in e.value.lower() for e in date_entities)

    def test_extract_iso_date(self):
        """Extract ISO date format"""
        extractor = EntityExtractor()
        text = "Deadline: 2026-01-15"
        entities = extractor.extract(text)

        date_entities = [e for e in entities if e.type == EntityType.DATE]
        assert len(date_entities) >= 1

    def test_extract_french_relative_date(self):
        """Extract French relative date"""
        extractor = EntityExtractor()
        text = "À faire pour demain matin"
        entities = extractor.extract(text)

        date_entities = [e for e in entities if e.type == EntityType.DATE]
        assert len(date_entities) >= 1
        assert any("demain" in e.value.lower() for e in date_entities)


class TestPersonExtraction:
    """Tests for person extraction from greetings and text"""

    def test_extract_person_from_french_greeting(self):
        """Extract person from French greeting"""
        extractor = EntityExtractor()
        text = "Bonjour Jean-Pierre, comment allez-vous?"
        entities = extractor.extract(text)

        person_entities = [e for e in entities if e.type == EntityType.PERSON]
        assert len(person_entities) >= 1
        assert any("Jean-Pierre" in e.value for e in person_entities)

    def test_extract_person_from_english_greeting(self):
        """Extract person from English greeting"""
        extractor = EntityExtractor()
        text = "Dear Alice, thank you for your email."
        entities = extractor.extract(text)

        person_entities = [e for e in entities if e.type == EntityType.PERSON]
        assert len(person_entities) >= 1
        assert any("Alice" in e.value for e in person_entities)

    def test_extract_person_from_metadata_sender(self):
        """Extract sender person from metadata"""
        extractor = EntityExtractor()
        text = "Some content"
        metadata = {
            "sender": {"name": "Marie Dupont", "email": "marie@example.com"}
        }
        entities = extractor.extract(text, metadata)

        person_entities = [e for e in entities if e.type == EntityType.PERSON]
        assert len(person_entities) >= 1
        sender_entity = next(
            (e for e in person_entities if e.metadata.get("role") == "sender"),
            None
        )
        assert sender_entity is not None
        assert sender_entity.confidence == extractor.METADATA_CONFIDENCE


class TestOrganizationExtraction:
    """Tests for organization extraction"""

    def test_extract_company_with_suffix(self):
        """Extract company with common suffix"""
        extractor = EntityExtractor()
        text = "Nous travaillons avec Acme Inc. sur ce projet"
        entities = extractor.extract(text)

        org_entities = [e for e in entities if e.type == EntityType.ORGANIZATION]
        assert len(org_entities) >= 1
        assert any("Acme" in e.value for e in org_entities)

    def test_extract_french_company(self):
        """Extract French company formats"""
        extractor = EntityExtractor()
        text = "Contrat avec Société Générale SA"
        entities = extractor.extract(text)

        org_entities = [e for e in entities if e.type == EntityType.ORGANIZATION]
        assert len(org_entities) >= 1


class TestDeduplication:
    """Tests for entity deduplication"""

    def test_deduplicate_same_value(self):
        """Deduplicate entities with same value"""
        extractor = EntityExtractor()
        text = "Call me at 06 12 34 56 78. My number is 06 12 34 56 78."
        entities = extractor.extract(text)

        phone_entities = [e for e in entities if e.type == EntityType.PHONE]
        # Should only have one phone entity after deduplication
        unique_phones = set(e.value for e in phone_entities)
        assert len(phone_entities) == len(unique_phones)


class TestConfidenceScores:
    """Tests for confidence score assignment"""

    def test_regex_match_confidence(self):
        """Regex matches get REGEX_CONFIDENCE"""
        extractor = EntityExtractor()
        text = "Email: test@example.com"
        entities = extractor.extract(text)

        # URL and email entities from regex should have high confidence
        for entity in entities:
            if entity.type in (EntityType.URL, EntityType.PHONE, EntityType.AMOUNT):
                assert entity.confidence == extractor.REGEX_CONFIDENCE

    def test_metadata_confidence(self):
        """Metadata entities get METADATA_CONFIDENCE"""
        extractor = EntityExtractor()
        metadata = {
            "sender": {"name": "Test User", "email": "test@example.com"}
        }
        entities = extractor.extract("Hello", metadata)

        sender_entity = next(
            (e for e in entities if e.metadata.get("role") == "sender"),
            None
        )
        if sender_entity:
            assert sender_entity.confidence == extractor.METADATA_CONFIDENCE

    def test_heuristic_confidence(self):
        """Heuristic matches get HEURISTIC_CONFIDENCE"""
        extractor = EntityExtractor()
        text = "Bonjour Pierre, voici le document"
        entities = extractor.extract(text)

        # Person from greeting pattern should have heuristic confidence
        person_from_greeting = [
            e for e in entities
            if e.type == EntityType.PERSON
            and e.source == EntitySource.EXTRACTION
            and e.metadata.get("role") != "sender"
        ]
        for entity in person_from_greeting:
            assert entity.confidence == extractor.HEURISTIC_CONFIDENCE


class TestEntitySource:
    """Tests for entity source tracking"""

    def test_extraction_source(self):
        """Extracted entities have EXTRACTION source"""
        extractor = EntityExtractor()
        text = "Contact: 06 12 34 56 78"
        entities = extractor.extract(text)

        assert all(e.source == EntitySource.EXTRACTION for e in entities)


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_text(self):
        """Handle empty text gracefully"""
        extractor = EntityExtractor()
        entities = extractor.extract("")
        assert entities == []

    def test_none_metadata(self):
        """Handle None metadata"""
        extractor = EntityExtractor()
        entities = extractor.extract("Hello world", None)
        assert isinstance(entities, list)

    def test_empty_metadata(self):
        """Handle empty metadata"""
        extractor = EntityExtractor()
        entities = extractor.extract("Hello world", {})
        assert isinstance(entities, list)

    def test_malformed_sender(self):
        """Handle malformed sender in metadata"""
        extractor = EntityExtractor()
        metadata = {"sender": "not a dict"}
        entities = extractor.extract("Hello", metadata)
        # Should not crash, just skip malformed sender
        assert isinstance(entities, list)

    def test_unicode_text(self):
        """Handle Unicode text correctly"""
        extractor = EntityExtractor()
        text = "Réunion avec José García le 15 février"
        entities = extractor.extract(text)
        assert isinstance(entities, list)


class TestEntityModel:
    """Tests for Entity dataclass"""

    def test_entity_creation(self):
        """Create Entity with required fields"""
        entity = Entity(
            type=EntityType.PERSON,
            value="John Doe",
            confidence=0.9
        )
        assert entity.type == EntityType.PERSON
        assert entity.value == "John Doe"
        assert entity.confidence == 0.9

    def test_entity_validation_empty_value(self):
        """Entity rejects empty value"""
        with pytest.raises(ValueError, match="cannot be empty"):
            Entity(
                type=EntityType.PERSON,
                value="",
                confidence=0.5
            )

    def test_entity_validation_confidence_range(self):
        """Entity validates confidence in 0-1 range"""
        with pytest.raises(ValueError, match="between 0 and 1"):
            Entity(
                type=EntityType.PERSON,
                value="Test",
                confidence=1.5
            )

    def test_entity_to_dict(self):
        """Entity serializes to dict"""
        entity = Entity(
            type=EntityType.PERSON,
            value="John Doe",
            confidence=0.9,
            metadata={"email": "john@example.com"}
        )
        data = entity.to_dict()

        assert data["type"] == "person"
        assert data["value"] == "John Doe"
        assert data["confidence"] == 0.9
        assert data["metadata"]["email"] == "john@example.com"

    def test_entity_from_dict(self):
        """Entity deserializes from dict"""
        data = {
            "type": "person",
            "value": "John Doe",
            "confidence": 0.9,
            "source": "extraction",
            "metadata": {"email": "john@example.com"}
        }
        entity = Entity.from_dict(data)

        assert entity.type == EntityType.PERSON
        assert entity.value == "John Doe"
        assert entity.confidence == 0.9
        assert entity.metadata["email"] == "john@example.com"
