"""
Frontmatter Schema — Enriched Frontmatter Dataclasses

Defines typed dataclasses for note frontmatter to enable:
- Better AI context understanding
- Type-safe frontmatter manipulation
- Validation and defaults

See: docs/specs/FRONTMATTER_ENRICHED_SPEC.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Union

from src.passepartout.note_types import (
    Category,
    EntityType,
    ImportanceLevel,
    NoteType,
    ProjectStatus,
    Relation,
    RelationshipStrength,
)

# === HELPER DATACLASSES ===


@dataclass
class PendingUpdate:
    """
    Proposition de mise à jour en attente de validation.

    Les workflows background proposent des mises à jour qui sont stockées
    ici jusqu'à validation par l'utilisateur.
    """

    field: str  # Nom du champ à mettre à jour
    value: Any  # Nouvelle valeur proposée
    source: str  # Source de la détection (email_signature, email_content, calendar, etc.)
    source_ref: Optional[str]  # ID de l'événement source (ex: message_id)
    detected_at: datetime  # Date de détection
    confidence: float  # Confiance de la détection (0.0-1.0)

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        return {
            "field": self.field,
            "value": self.value,
            "source": self.source,
            "source_ref": self.source_ref,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "confidence": self.confidence,
        }


@dataclass
class Stakeholder:
    """
    Partie prenante d'un projet.

    Représente une personne impliquée dans un projet avec son rôle.
    """

    person: str  # Wikilink [[Nom]] ou titre de note
    role: str  # Rôle dans le projet (investisseur, partenaire, etc.)

    def to_dict(self) -> dict[str, str]:
        """Convertit en dict pour sérialisation YAML."""
        return {"person": self.person, "role": self.role}


@dataclass
class LinkedSource:
    """
    Source liée pour enrichissement background.

    Définit une source externe à surveiller pour enrichir automatiquement la note.
    """

    type: str  # folder, whatsapp, email, teams
    identifier: str  # path, contact name, filter, chat name
    priority: int = 2  # 1 = haute, 2 = moyenne, 3 = basse

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result: dict[str, Any] = {"type": self.type, "priority": self.priority}
        # Use appropriate key based on type
        key_mapping = {
            "folder": "path",
            "whatsapp": "contact",
            "email": "filter",
            "teams": "chat",
        }
        key = key_mapping.get(self.type, "identifier")
        result[key] = self.identifier
        return result


@dataclass
class Contact:
    """
    Contact lié à une entité ou un actif.
    """

    person: str  # Wikilink [[Nom]]
    role: str  # Rôle (syndic, locataire, gestionnaire, etc.)

    def to_dict(self) -> dict[str, str]:
        """Convertit en dict pour sérialisation YAML."""
        return {"person": self.person, "role": self.role}


# === BASE FRONTMATTER ===


@dataclass
class BaseFrontmatter:
    """
    Champs communs à toutes les notes.

    Tous les types de notes héritent de ces champs de base.
    """

    # === IDENTIFICATION ===
    title: str = ""
    type: NoteType = NoteType.AUTRE
    aliases: list[str] = field(default_factory=list)

    # === MÉTADONNÉES SYSTÈME ===
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    source: Optional[str] = None  # apple_notes, scapin, manual
    source_id: Optional[str] = None  # ID source externe si applicable

    # === CLASSIFICATION ===
    importance: Optional[ImportanceLevel] = None
    tags: list[str] = field(default_factory=list)
    category: Optional[Category] = None

    # === RELATIONS ===
    related: list[str] = field(default_factory=list)  # Wikilinks

    # === SOURCES LIÉES ===
    linked_sources: list[LinkedSource] = field(default_factory=list)

    # === PROPOSITIONS EN ATTENTE ===
    pending_updates: list[PendingUpdate] = field(default_factory=list)

    # === MÉTADONNÉES BRUTES (préservées du YAML original) ===
    _raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result: dict[str, Any] = {}

        if self.title:
            result["title"] = self.title
        if self.type != NoteType.AUTRE:
            result["type"] = self.type.value
        if self.aliases:
            result["aliases"] = self.aliases

        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
        if self.source:
            result["source"] = self.source
        if self.source_id:
            result["source_id"] = self.source_id

        if self.importance:
            result["importance"] = self.importance.value
        if self.tags:
            result["tags"] = self.tags
        if self.category:
            result["category"] = self.category.value

        if self.related:
            result["related"] = self.related
        if self.linked_sources:
            result["linked_sources"] = [ls.to_dict() for ls in self.linked_sources]
        if self.pending_updates:
            result["pending_updates"] = [pu.to_dict() for pu in self.pending_updates]

        return result


# === TYPE-SPECIFIC FRONTMATTER ===


@dataclass
class PersonneFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type PERSONNE.

    Contient les informations de contact et la relation avec Johan.
    """

    type: NoteType = NoteType.PERSONNE

    # === IDENTITÉ ===
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    # === RELATION AVEC JOHAN ===
    relation: Optional[Relation] = None
    relationship_strength: Optional[RelationshipStrength] = None
    introduced_by: Optional[str] = None  # Wikilink [[Nom]]

    # === PROFESSIONNEL ===
    organization: Optional[str] = None  # Wikilink [[Entreprise]]
    role: Optional[str] = None
    sector: Optional[str] = None

    # === COMMUNICATION ===
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: str = "français"
    communication_style: Optional[str] = None  # formel, casual, technique
    timezone: Optional[str] = None

    # === CONTEXTE ===
    projects: list[str] = field(default_factory=list)  # Wikilinks [[Projet]]
    last_contact: Optional[datetime] = None  # Auto-updated
    mention_count: int = 0  # Auto-updated
    first_contact: Optional[datetime] = None

    # === NOTES PERSONNELLES ===
    notes_personnelles: Optional[str] = None  # Manual only

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.first_name:
            result["first_name"] = self.first_name
        if self.last_name:
            result["last_name"] = self.last_name

        if self.relation:
            result["relation"] = self.relation.value
        if self.relationship_strength:
            result["relationship_strength"] = self.relationship_strength.value
        if self.introduced_by:
            result["introduced_by"] = self.introduced_by

        if self.organization:
            result["organization"] = self.organization
        if self.role:
            result["role"] = self.role
        if self.sector:
            result["sector"] = self.sector

        if self.email:
            result["email"] = self.email
        if self.phone:
            result["phone"] = self.phone
        if self.preferred_language != "français":
            result["preferred_language"] = self.preferred_language
        if self.communication_style:
            result["communication_style"] = self.communication_style
        if self.timezone:
            result["timezone"] = self.timezone

        if self.projects:
            result["projects"] = self.projects
        if self.last_contact:
            result["last_contact"] = self.last_contact.isoformat()
        if self.mention_count > 0:
            result["mention_count"] = self.mention_count
        if self.first_contact:
            result["first_contact"] = self.first_contact.isoformat()

        if self.notes_personnelles:
            result["notes_personnelles"] = self.notes_personnelles

        return result


@dataclass
class ProjetFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type PROJET.

    Contient les informations de suivi et les parties prenantes.
    """

    type: NoteType = NoteType.PROJET

    # === ÉTAT ===
    status: ProjectStatus = ProjectStatus.ACTIF
    priority: Optional[ImportanceLevel] = None
    domain: Optional[str] = None

    # === TEMPORALITÉ ===
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    deadline: Optional[datetime] = None  # Date butoir ferme

    # === PARTIES PRENANTES ===
    stakeholders: list[Stakeholder] = field(default_factory=list)

    # === FINANCIER ===
    budget_range: Optional[str] = None
    currency: str = "EUR"

    # === CONTEXTE ===
    related_entities: list[str] = field(default_factory=list)  # Wikilinks
    last_activity: Optional[datetime] = None  # Auto-updated
    activity_count: int = 0  # Auto-updated

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        result["status"] = self.status.value
        if self.priority:
            result["priority"] = self.priority.value
        if self.domain:
            result["domain"] = self.domain

        if self.start_date:
            result["start_date"] = self.start_date.isoformat()
        if self.target_date:
            result["target_date"] = self.target_date.isoformat()
        if self.deadline:
            result["deadline"] = self.deadline.isoformat()

        if self.stakeholders:
            result["stakeholders"] = [s.to_dict() for s in self.stakeholders]

        if self.budget_range:
            result["budget_range"] = self.budget_range
        if self.currency != "EUR":
            result["currency"] = self.currency

        if self.related_entities:
            result["related_entities"] = self.related_entities
        if self.last_activity:
            result["last_activity"] = self.last_activity.isoformat()
        if self.activity_count > 0:
            result["activity_count"] = self.activity_count

        return result


@dataclass
class EntiteFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type ENTITE (organisation).

    Contient les informations sur l'organisation et ses contacts.
    """

    type: NoteType = NoteType.ENTITE

    # === TYPE D'ORGANISATION ===
    entity_type: Optional[EntityType] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    # === RELATION ===
    relationship: Optional[str] = None  # employeur, client, fournisseur, partenaire

    # === CONTACTS CLÉS ===
    contacts: list[Contact] = field(default_factory=list)

    # === COORDONNÉES ===
    website: Optional[str] = None
    email_domain: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None

    # === CONTEXTE ===
    projects: list[str] = field(default_factory=list)  # Wikilinks
    last_interaction: Optional[datetime] = None  # Auto-updated

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.entity_type:
            result["entity_type"] = self.entity_type.value
        if self.sector:
            result["sector"] = self.sector
        if self.industry:
            result["industry"] = self.industry

        if self.relationship:
            result["relationship"] = self.relationship

        if self.contacts:
            result["contacts"] = [c.to_dict() for c in self.contacts]

        if self.website:
            result["website"] = self.website
        if self.email_domain:
            result["email_domain"] = self.email_domain
        if self.address:
            result["address"] = self.address
        if self.country:
            result["country"] = self.country

        if self.projects:
            result["projects"] = self.projects
        if self.last_interaction:
            result["last_interaction"] = self.last_interaction.isoformat()

        return result


@dataclass
class ReunionFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type REUNION.

    Contient les informations de la réunion et ses résultats.
    """

    type: NoteType = NoteType.REUNION

    # === TEMPORALITÉ ===
    date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    timezone: Optional[str] = None

    # === LIEU ===
    location: Optional[str] = None
    location_type: Optional[str] = None  # online, physical, hybrid
    meeting_url: Optional[str] = None

    # === PARTICIPANTS ===
    participants: list[Stakeholder] = field(default_factory=list)

    # === CONTEXTE ===
    project: Optional[str] = None  # Wikilink [[Projet]]
    agenda: list[str] = field(default_factory=list)

    # === RÉSULTATS ===
    decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    next_meeting: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.date:
            result["date"] = self.date.isoformat()
        if self.duration_minutes:
            result["duration_minutes"] = self.duration_minutes
        if self.timezone:
            result["timezone"] = self.timezone

        if self.location:
            result["location"] = self.location
        if self.location_type:
            result["location_type"] = self.location_type
        if self.meeting_url:
            result["meeting_url"] = self.meeting_url

        if self.participants:
            result["participants"] = [p.to_dict() for p in self.participants]

        if self.project:
            result["project"] = self.project
        if self.agenda:
            result["agenda"] = self.agenda

        if self.decisions:
            result["decisions"] = self.decisions
        if self.action_items:
            result["action_items"] = self.action_items
        if self.next_meeting:
            result["next_meeting"] = self.next_meeting.isoformat()

        return result


@dataclass
class ActifFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type ACTIF (bien, domaine).

    Note: Utilise NoteType.ENTITE car ACTIF n'existe pas comme type séparé.
    Le type réel est déterminé par le contenu (asset_type).
    """

    type: NoteType = NoteType.ENTITE  # Pas de type ACTIF dédié

    # === TYPE D'ACTIF ===
    asset_type: Optional[str] = None  # bien_immobilier, véhicule, investissement, domaine
    asset_category: Optional[str] = None

    # === LOCALISATION ===
    location: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None

    # === VALEUR ===
    acquisition_date: Optional[datetime] = None
    acquisition_value: Optional[str] = None
    current_status: Optional[str] = None  # possédé, loué, en_vente, vendu

    # === CONTACTS LIÉS ===
    contacts: list[Contact] = field(default_factory=list)

    # === PROJETS LIÉS ===
    projects: list[str] = field(default_factory=list)  # Wikilinks

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.asset_type:
            result["asset_type"] = self.asset_type
        if self.asset_category:
            result["asset_category"] = self.asset_category

        if self.location:
            result["location"] = self.location
        if self.address:
            result["address"] = self.address
        if self.country:
            result["country"] = self.country

        if self.acquisition_date:
            result["acquisition_date"] = self.acquisition_date.isoformat()
        if self.acquisition_value:
            result["acquisition_value"] = self.acquisition_value
        if self.current_status:
            result["current_status"] = self.current_status

        if self.contacts:
            result["contacts"] = [c.to_dict() for c in self.contacts]
        if self.projects:
            result["projects"] = self.projects

        return result


# === TYPE ALIAS ===

# Union de tous les types de frontmatter
AnyFrontmatter = Union[
    BaseFrontmatter,
    PersonneFrontmatter,
    ProjetFrontmatter,
    EntiteFrontmatter,
    ReunionFrontmatter,
    ActifFrontmatter,
]
