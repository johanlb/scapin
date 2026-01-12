"""
Entity Models

Core entity types for extraction and knowledge base enrichment.
Supports the Email → Notes bidirectional loop.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EntityType(str, Enum):
    """Types d'entités extractibles"""

    PERSON = "person"  # Nom, email, rôle
    DATE = "date"  # Échéance, événement
    PROJECT = "project"  # Référence projet
    ORGANIZATION = "organization"  # Entreprise, équipe
    AMOUNT = "amount"  # Montant, devise
    LOCATION = "location"  # Lieu physique
    URL = "url"  # Lien web
    TOPIC = "topic"  # Sujet, thème
    PHONE = "phone"  # Numéro de téléphone


class EntitySource(str, Enum):
    """Source de l'entité"""

    EXTRACTION = "extraction"  # Extraction regex/heuristique
    AI_VALIDATION = "ai_validation"  # Validation par IA
    USER = "user"  # Correction utilisateur
    CONTEXT = "context"  # Depuis le contexte des notes


@dataclass
class Entity:
    """
    Entité extraite avec métadonnées.

    Une entité représente une information structurée extraite d'un texte :
    personne, date, montant, organisation, etc.

    Attributes:
        type: Type d'entité (person, date, project, etc.)
        value: Valeur brute extraite
        normalized: Valeur normalisée (optionnelle)
        confidence: Score de confiance 0.0-1.0
        source: Source de l'extraction
        metadata: Métadonnées spécifiques au type

    Metadata examples by type:
        - person: {"email": "...", "role": "sender|recipient|mentioned"}
        - date: {"parsed": datetime, "type": "deadline|event|mention"}
        - amount: {"value": 1500.0, "currency": "EUR"}
        - project: {"note_id": "...", "match_score": 0.95}
        - organization: {"domain": "...", "type": "company|team|department"}
        - location: {"type": "address|city|country"}
        - phone: {"formatted": "+33 1 23 45 67 89", "type": "mobile|landline"}
    """

    type: EntityType
    value: str
    normalized: Optional[str] = None
    confidence: float = 0.0
    source: EntitySource = EntitySource.EXTRACTION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate entity after initialization."""
        if not self.value:
            raise ValueError("Entity value cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "value": self.value,
            "normalized": self.normalized,
            "confidence": self.confidence,
            "source": self.source.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        """Create from dictionary."""
        return cls(
            type=EntityType(data["type"]),
            value=data["value"],
            normalized=data.get("normalized"),
            confidence=data.get("confidence", 0.0),
            source=EntitySource(data.get("source", "extraction")),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProposedNote:
    """
    Proposition de création ou enrichissement de note.

    Générée par l'IA lors de l'analyse d'un email pour suggérer
    des mises à jour de la base de connaissances.

    Attributes:
        action: "create" pour nouvelle note, "enrich" pour mise à jour
        note_type: Type de note (personne, projet, etc.)
        title: Titre de la note
        content_summary: Résumé du contenu proposé
        entities: Entités associées à la note
        suggested_tags: Tags suggérés
        confidence: Score de confiance 0.0-1.0
        reasoning: Explication de la proposition
        target_note_id: ID de la note à enrichir (si action="enrich")
        source_email_id: ID de l'email source
    """

    action: str  # "create" | "enrich"
    note_type: str  # NoteType value
    title: str
    content_summary: str
    entities: list[Entity] = field(default_factory=list)
    suggested_tags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    target_note_id: Optional[str] = None
    source_email_id: str = ""

    def __post_init__(self) -> None:
        """Validate proposed note."""
        if self.action not in ("create", "enrich"):
            raise ValueError(f"Action must be 'create' or 'enrich', got '{self.action}'")
        if not self.title:
            raise ValueError("Title cannot be empty")
        if self.action == "enrich" and not self.target_note_id:
            raise ValueError("target_note_id required for 'enrich' action")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action,
            "note_type": self.note_type,
            "title": self.title,
            "content_summary": self.content_summary,
            "entities": [e.to_dict() for e in self.entities],
            "suggested_tags": self.suggested_tags,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "target_note_id": self.target_note_id,
            "source_email_id": self.source_email_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProposedNote":
        """Create from dictionary."""
        return cls(
            action=data["action"],
            note_type=data["note_type"],
            title=data["title"],
            content_summary=data.get("content_summary", ""),
            entities=[Entity.from_dict(e) for e in data.get("entities", [])],
            suggested_tags=data.get("suggested_tags", []),
            confidence=data.get("confidence", 0.0),
            reasoning=data.get("reasoning", ""),
            target_note_id=data.get("target_note_id"),
            source_email_id=data.get("source_email_id", ""),
        )


@dataclass
class ProposedTask:
    """
    Proposition de tâche OmniFocus.

    Générée par l'IA lors de l'analyse d'un email pour suggérer
    la création d'une tâche de suivi.

    Attributes:
        title: Titre de la tâche
        note: Note/description de la tâche
        project: Projet OmniFocus cible
        tags: Tags OmniFocus
        due_date: Date d'échéance
        defer_date: Date de report
        confidence: Score de confiance 0.0-1.0
        reasoning: Explication de la proposition
        source_email_id: ID de l'email source
    """

    title: str
    note: str = ""
    project: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    due_date: Optional[datetime] = None
    defer_date: Optional[datetime] = None
    confidence: float = 0.0
    reasoning: str = ""
    source_email_id: str = ""

    def __post_init__(self) -> None:
        """Validate proposed task."""
        if not self.title:
            raise ValueError("Task title cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "note": self.note,
            "project": self.project,
            "tags": self.tags,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "defer_date": self.defer_date.isoformat() if self.defer_date else None,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "source_email_id": self.source_email_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProposedTask":
        """Create from dictionary."""
        due_date = None
        if data.get("due_date"):
            due_date = datetime.fromisoformat(data["due_date"])

        defer_date = None
        if data.get("defer_date"):
            defer_date = datetime.fromisoformat(data["defer_date"])

        return cls(
            title=data["title"],
            note=data.get("note", ""),
            project=data.get("project"),
            tags=data.get("tags", []),
            due_date=due_date,
            defer_date=defer_date,
            confidence=data.get("confidence", 0.0),
            reasoning=data.get("reasoning", ""),
            source_email_id=data.get("source_email_id", ""),
        )


# Threshold for auto-applying proposed notes/tasks
AUTO_APPLY_THRESHOLD = 0.90  # For optional enrichments
AUTO_APPLY_THRESHOLD_REQUIRED = 0.85  # For required enrichments (aligned with action minimum)


def should_auto_apply(confidence: float, is_required: bool) -> bool:
    """
    Determine if an enrichment should be auto-applied.

    Required enrichments use a lower threshold (85%) to ensure critical
    information is saved before archiving the email.
    Optional enrichments use a higher threshold (90%) for extra caution.

    Args:
        confidence: The confidence score (0.0-1.0)
        is_required: Whether this enrichment is marked as required

    Returns:
        True if the enrichment should be auto-applied
    """
    threshold = AUTO_APPLY_THRESHOLD_REQUIRED if is_required else AUTO_APPLY_THRESHOLD
    return confidence >= threshold
