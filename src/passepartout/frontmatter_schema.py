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


@dataclass
class ConceptFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type CONCEPT.

    Contient les informations sur une idée, un sujet, une recette ou des instructions.
    """

    type: NoteType = NoteType.CONCEPT

    # === CLASSIFICATION ===
    concept_type: Optional[str] = None  # idée, sujet, recette, instruction, technique
    domain: Optional[str] = None  # cuisine, informatique, philosophie, etc.
    difficulty: Optional[str] = None  # facile, moyen, avancé

    # === ÉTAT ===
    maturity: Optional[str] = None  # brouillon, en_cours, mature, validé
    last_reviewed: Optional[datetime] = None

    # === RÉFÉRENCES ===
    sources: list[str] = field(default_factory=list)  # URLs, livres, articles
    inspired_by: Optional[str] = None  # Wikilink [[Note]]

    # === POUR RECETTES/INSTRUCTIONS ===
    duration: Optional[str] = None  # "30 min", "2h", etc.
    prerequisites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.concept_type:
            result["concept_type"] = self.concept_type
        if self.domain:
            result["domain"] = self.domain
        if self.difficulty:
            result["difficulty"] = self.difficulty
        if self.maturity:
            result["maturity"] = self.maturity
        if self.last_reviewed:
            result["last_reviewed"] = self.last_reviewed.isoformat()
        if self.sources:
            result["sources"] = self.sources
        if self.inspired_by:
            result["inspired_by"] = self.inspired_by
        if self.duration:
            result["duration"] = self.duration
        if self.prerequisites:
            result["prerequisites"] = self.prerequisites

        return result


@dataclass
class RessourceFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type RESSOURCE.

    Contient les informations sur un contenu consommé (livre, article, vidéo, podcast, cours).
    """

    type: NoteType = NoteType.RESSOURCE

    # === IDENTIFICATION ===
    resource_type: Optional[str] = None  # livre, article, video, podcast, cours
    author: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None

    # === ACCÈS ===
    url: Optional[str] = None
    isbn: Optional[str] = None

    # === CONSOMMATION ===
    status: Optional[str] = None  # à_lire, en_cours, terminé, abandonné
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    rating: Optional[int] = None  # 1-5

    # === CLASSIFICATION ===
    topics: list[str] = field(default_factory=list)
    recommended_by: Optional[str] = None  # Wikilink [[Personne]]

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.resource_type:
            result["resource_type"] = self.resource_type
        if self.author:
            result["author"] = self.author
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.url:
            result["url"] = self.url
        if self.isbn:
            result["isbn"] = self.isbn
        if self.status:
            result["status"] = self.status
        if self.started_at:
            result["started_at"] = self.started_at.isoformat()
        if self.finished_at:
            result["finished_at"] = self.finished_at.isoformat()
        if self.rating:
            result["rating"] = self.rating
        if self.topics:
            result["topics"] = self.topics
        if self.recommended_by:
            result["recommended_by"] = self.recommended_by

        return result


@dataclass
class LieuFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type LIEU.

    Contient les informations sur un endroit physique (restaurant, hôtel, ville, adresse).
    """

    type: NoteType = NoteType.LIEU

    # === IDENTIFICATION ===
    lieu_type: Optional[str] = None  # restaurant, hotel, ville, adresse, magasin

    # === LOCALISATION ===
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    gps: Optional[str] = None  # "latitude, longitude"
    maps_url: Optional[str] = None

    # === CONTACT ===
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None

    # === ÉVALUATION ===
    rating: Optional[int] = None  # 1-5
    price_range: Optional[str] = None  # €, €€, €€€, €€€€
    last_visit: Optional[datetime] = None

    # === CONTEXTE ===
    recommended_by: Optional[str] = None  # Wikilink [[Personne]]
    visited_with: list[str] = field(default_factory=list)  # Wikilinks

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.lieu_type:
            result["lieu_type"] = self.lieu_type
        if self.address:
            result["address"] = self.address
        if self.city:
            result["city"] = self.city
        if self.country:
            result["country"] = self.country
        if self.gps:
            result["gps"] = self.gps
        if self.maps_url:
            result["maps_url"] = self.maps_url
        if self.phone:
            result["phone"] = self.phone
        if self.website:
            result["website"] = self.website
        if self.email:
            result["email"] = self.email
        if self.rating:
            result["rating"] = self.rating
        if self.price_range:
            result["price_range"] = self.price_range
        if self.last_visit:
            result["last_visit"] = self.last_visit.isoformat()
        if self.recommended_by:
            result["recommended_by"] = self.recommended_by
        if self.visited_with:
            result["visited_with"] = self.visited_with

        return result


@dataclass
class ProduitFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type PRODUIT.

    Contient les informations sur un outil, équipement ou logiciel.
    """

    type: NoteType = NoteType.PRODUIT

    # === IDENTIFICATION ===
    product_type: Optional[str] = None  # logiciel, materiel, service, equipement
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None

    # === ACQUISITION ===
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[str] = None
    purchase_location: Optional[str] = None
    warranty_until: Optional[datetime] = None

    # === ÉTAT ===
    status: Optional[str] = None  # actif, stocké, vendu, jeté
    rating: Optional[int] = None  # 1-5

    # === LIENS ===
    website: Optional[str] = None
    documentation: Optional[str] = None
    related_products: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.product_type:
            result["product_type"] = self.product_type
        if self.brand:
            result["brand"] = self.brand
        if self.model:
            result["model"] = self.model
        if self.version:
            result["version"] = self.version
        if self.purchase_date:
            result["purchase_date"] = self.purchase_date.isoformat()
        if self.purchase_price:
            result["purchase_price"] = self.purchase_price
        if self.purchase_location:
            result["purchase_location"] = self.purchase_location
        if self.warranty_until:
            result["warranty_until"] = self.warranty_until.isoformat()
        if self.status:
            result["status"] = self.status
        if self.rating:
            result["rating"] = self.rating
        if self.website:
            result["website"] = self.website
        if self.documentation:
            result["documentation"] = self.documentation
        if self.related_products:
            result["related_products"] = self.related_products

        return result


@dataclass
class DecisionFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type DECISION.

    Contient les informations sur un choix important documenté.
    """

    type: NoteType = NoteType.DECISION

    # === DÉCISION ===
    decision_date: Optional[datetime] = None
    decision_maker: Optional[str] = None  # Wikilink ou "moi"
    domain: Optional[str] = None  # tech, finance, carrière, perso

    # === CARACTÉRISTIQUES ===
    reversible: Optional[bool] = None
    impact: Optional[str] = None  # faible, moyen, fort
    confidence: Optional[str] = None  # faible, moyenne, haute

    # === RÉSULTAT ===
    outcome: Optional[str] = None  # positif, négatif, neutre, en_cours
    reviewed_at: Optional[datetime] = None

    # === LIENS ===
    related_project: Optional[str] = None  # Wikilink [[Projet]]
    stakeholders: list[str] = field(default_factory=list)  # Wikilinks

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.decision_date:
            result["decision_date"] = self.decision_date.isoformat()
        if self.decision_maker:
            result["decision_maker"] = self.decision_maker
        if self.domain:
            result["domain"] = self.domain
        if self.reversible is not None:
            result["reversible"] = self.reversible
        if self.impact:
            result["impact"] = self.impact
        if self.confidence:
            result["confidence"] = self.confidence
        if self.outcome:
            result["outcome"] = self.outcome
        if self.reviewed_at:
            result["reviewed_at"] = self.reviewed_at.isoformat()
        if self.related_project:
            result["related_project"] = self.related_project
        if self.stakeholders:
            result["stakeholders"] = self.stakeholders

        return result


@dataclass
class ObjectifFrontmatter(BaseFrontmatter):
    """
    Frontmatter pour une note de type OBJECTIF.

    Contient les informations sur un goal 1-5 ans ou area of focus (GTD).
    """

    type: NoteType = NoteType.OBJECTIF

    # === CLASSIFICATION ===
    horizon: Optional[str] = None  # 1_an, 3_ans, 5_ans, area_of_focus
    domain: Optional[str] = None  # santé, finance, carrière, relations, perso

    # === TEMPORALITÉ ===
    target_date: Optional[datetime] = None
    started_at: Optional[datetime] = None

    # === ÉTAT ===
    status: Optional[str] = None  # actif, atteint, abandonné, en_pause
    progress: Optional[int] = None  # 0-100

    # === MESURE ===
    kpis: list[str] = field(default_factory=list)  # Indicateurs clés
    current_value: Optional[str] = None
    target_value: Optional[str] = None

    # === LIENS ===
    parent_objective: Optional[str] = None  # Wikilink [[Objectif parent]]
    contributing_projects: list[str] = field(default_factory=list)  # Wikilinks

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dict pour sérialisation YAML."""
        result = super().to_dict()

        if self.horizon:
            result["horizon"] = self.horizon
        if self.domain:
            result["domain"] = self.domain
        if self.target_date:
            result["target_date"] = self.target_date.isoformat()
        if self.started_at:
            result["started_at"] = self.started_at.isoformat()
        if self.status:
            result["status"] = self.status
        if self.progress is not None:
            result["progress"] = self.progress
        if self.kpis:
            result["kpis"] = self.kpis
        if self.current_value:
            result["current_value"] = self.current_value
        if self.target_value:
            result["target_value"] = self.target_value
        if self.parent_objective:
            result["parent_objective"] = self.parent_objective
        if self.contributing_projects:
            result["contributing_projects"] = self.contributing_projects

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
    ConceptFrontmatter,
    RessourceFrontmatter,
    LieuFrontmatter,
    ProduitFrontmatter,
    DecisionFrontmatter,
    ObjectifFrontmatter,
]
