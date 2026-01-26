"""
Frontmatter Parser — YAML to Typed Dataclasses

Parses raw YAML frontmatter into typed dataclasses for better
AI context understanding and type-safe manipulation.

See: docs/specs/FRONTMATTER_ENRICHED_SPEC.md
"""

from datetime import datetime, timezone
from typing import Any, Optional

from src.monitoring.logger import get_logger
from src.passepartout.frontmatter_schema import (
    ActifFrontmatter,
    AnyFrontmatter,
    BaseFrontmatter,
    ConceptFrontmatter,
    Contact,
    DecisionFrontmatter,
    EntiteFrontmatter,
    LieuFrontmatter,
    LinkedSource,
    ObjectifFrontmatter,
    PendingUpdate,
    PersonneFrontmatter,
    ProduitFrontmatter,
    ProjetFrontmatter,
    RessourceFrontmatter,
    ReunionFrontmatter,
    Stakeholder,
)
from src.passepartout.note_types import (
    Category,
    EntityType,
    ImportanceLevel,
    NoteType,
    ProjectStatus,
    Relation,
    RelationshipStrength,
)

logger = get_logger("passepartout.frontmatter_parser")


class FrontmatterParser:
    """
    Parser pour convertir le YAML brut en dataclasses typées.

    Usage:
        parser = FrontmatterParser()
        frontmatter = parser.parse(yaml_dict)
        yaml_dict = parser.to_dict(frontmatter)
    """

    def parse(self, yaml_dict: dict[str, Any]) -> AnyFrontmatter:
        """
        Parse un dict YAML en frontmatter typé.

        Args:
            yaml_dict: Dict provenant de yaml.safe_load()

        Returns:
            Frontmatter typé selon le type de note détecté
        """
        if not yaml_dict:
            return BaseFrontmatter()

        note_type = self._detect_type(yaml_dict)

        try:
            if note_type == NoteType.PERSONNE:
                return self._parse_personne(yaml_dict)
            elif note_type == NoteType.PROJET:
                return self._parse_projet(yaml_dict)
            elif note_type == NoteType.ENTITE:
                # Vérifier si c'est un actif
                if "asset_type" in yaml_dict:
                    return self._parse_actif(yaml_dict)
                return self._parse_entite(yaml_dict)
            elif note_type == NoteType.REUNION:
                return self._parse_reunion(yaml_dict)
            elif note_type == NoteType.CONCEPT:
                return self._parse_concept(yaml_dict)
            elif note_type == NoteType.RESSOURCE:
                return self._parse_ressource(yaml_dict)
            elif note_type == NoteType.LIEU:
                return self._parse_lieu(yaml_dict)
            elif note_type == NoteType.PRODUIT:
                return self._parse_produit(yaml_dict)
            elif note_type == NoteType.DECISION:
                return self._parse_decision(yaml_dict)
            elif note_type == NoteType.OBJECTIF:
                return self._parse_objectif(yaml_dict)
            else:
                return self._parse_base(yaml_dict)
        except Exception as e:
            logger.warning(
                "Failed to parse typed frontmatter, falling back to base",
                extra={"error": str(e), "type": note_type.value},
            )
            return self._parse_base(yaml_dict)

    def _detect_type(self, yaml_dict: dict[str, Any]) -> NoteType:
        """Détecte le type de note depuis le frontmatter ou le chemin."""
        # 1. Champ 'type' explicite
        if "type" in yaml_dict:
            try:
                return NoteType(yaml_dict["type"])
            except ValueError:
                pass

        # 2. Déduire du chemin metadata.path
        path = yaml_dict.get("metadata", {}).get("path", "")
        if not path:
            path = str(yaml_dict.get("path", ""))

        path_lower = path.lower()
        if "personnes" in path_lower:
            return NoteType.PERSONNE
        elif "projets" in path_lower:
            return NoteType.PROJET
        elif "entités" in path_lower or "entites" in path_lower:
            return NoteType.ENTITE
        elif "réunions" in path_lower or "reunions" in path_lower:
            return NoteType.REUNION
        elif "concepts" in path_lower:
            return NoteType.CONCEPT
        elif "ressources" in path_lower:
            return NoteType.RESSOURCE
        elif "lieux" in path_lower:
            return NoteType.LIEU
        elif "produits" in path_lower:
            return NoteType.PRODUIT
        elif "décisions" in path_lower or "decisions" in path_lower:
            return NoteType.DECISION
        elif "objectifs" in path_lower:
            return NoteType.OBJECTIF

        return NoteType.AUTRE

    def _parse_base(self, d: dict[str, Any]) -> BaseFrontmatter:
        """Parse les champs de base communs à tous les types."""
        return BaseFrontmatter(
            title=str(d.get("title", "")),
            type=self._parse_note_type(d.get("type")),
            aliases=self._parse_list(d.get("aliases")),
            created_at=self._parse_datetime(d.get("created_at") or d.get("created")),
            updated_at=self._parse_datetime(d.get("updated_at") or d.get("modified")),
            source=d.get("source"),
            source_id=d.get("source_id") or d.get("apple_id"),
            importance=self._parse_importance(d.get("importance")),
            tags=self._parse_list(d.get("tags")),
            category=Category.from_string(d.get("category")) if d.get("category") else None,
            related=self._parse_list(d.get("related")),
            linked_sources=self._parse_linked_sources(d.get("linked_sources")),
            pending_updates=self._parse_pending_updates(d.get("pending_updates")),
            _raw_metadata=d,
        )

    def _parse_personne(self, d: dict[str, Any]) -> PersonneFrontmatter:
        """Parse un frontmatter PERSONNE."""
        base = self._parse_base(d)
        return PersonneFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.PERSONNE,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Personne-specific fields
            first_name=d.get("first_name"),
            last_name=d.get("last_name"),
            relation=Relation.from_string(d.get("relation")),
            relationship_strength=RelationshipStrength.from_string(d.get("relationship_strength")),
            introduced_by=d.get("introduced_by"),
            organization=d.get("organization"),
            role=d.get("role"),
            sector=d.get("sector"),
            email=d.get("email"),
            phone=d.get("phone"),
            preferred_language=d.get("preferred_language", "français"),
            communication_style=d.get("communication_style"),
            timezone=d.get("timezone"),
            projects=self._parse_list(d.get("projects")),
            last_contact=self._parse_datetime(d.get("last_contact")),
            mention_count=int(d.get("mention_count", 0)),
            first_contact=self._parse_datetime(d.get("first_contact")),
            notes_personnelles=d.get("notes_personnelles"),
        )

    def _parse_projet(self, d: dict[str, Any]) -> ProjetFrontmatter:
        """Parse un frontmatter PROJET."""
        base = self._parse_base(d)
        return ProjetFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.PROJET,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Projet-specific fields
            status=ProjectStatus.from_string(d.get("status")) or ProjectStatus.ACTIF,
            priority=self._parse_importance(d.get("priority")),
            domain=d.get("domain"),
            start_date=self._parse_datetime(d.get("start_date")),
            target_date=self._parse_datetime(d.get("target_date")),
            deadline=self._parse_datetime(d.get("deadline")),
            stakeholders=self._parse_stakeholders(d.get("stakeholders")),
            budget_range=d.get("budget_range"),
            currency=d.get("currency", "EUR"),
            related_entities=self._parse_list(d.get("related_entities")),
            last_activity=self._parse_datetime(d.get("last_activity")),
            activity_count=int(d.get("activity_count", 0)),
        )

    def _parse_entite(self, d: dict[str, Any]) -> EntiteFrontmatter:
        """Parse un frontmatter ENTITE."""
        base = self._parse_base(d)
        return EntiteFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.ENTITE,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Entite-specific fields
            entity_type=EntityType.from_string(d.get("entity_type")),
            sector=d.get("sector"),
            industry=d.get("industry"),
            relationship=d.get("relationship"),
            contacts=self._parse_contacts(d.get("contacts")),
            website=d.get("website"),
            email_domain=d.get("email_domain"),
            address=d.get("address"),
            country=d.get("country"),
            projects=self._parse_list(d.get("projects")),
            last_interaction=self._parse_datetime(d.get("last_interaction")),
        )

    def _parse_reunion(self, d: dict[str, Any]) -> ReunionFrontmatter:
        """Parse un frontmatter REUNION."""
        base = self._parse_base(d)
        return ReunionFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.REUNION,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Reunion-specific fields
            date=self._parse_datetime(d.get("date")),
            duration_minutes=d.get("duration_minutes"),
            timezone=d.get("timezone"),
            location=d.get("location"),
            location_type=d.get("location_type"),
            meeting_url=d.get("meeting_url"),
            participants=self._parse_stakeholders(d.get("participants")),
            project=d.get("project"),
            agenda=self._parse_list(d.get("agenda")),
            decisions=self._parse_list(d.get("decisions")),
            action_items=self._parse_list(d.get("action_items")),
            next_meeting=self._parse_datetime(d.get("next_meeting")),
        )

    def _parse_actif(self, d: dict[str, Any]) -> ActifFrontmatter:
        """Parse un frontmatter ACTIF."""
        base = self._parse_base(d)
        return ActifFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.ENTITE,  # Pas de type ACTIF dédié
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Actif-specific fields
            asset_type=d.get("asset_type"),
            asset_category=d.get("asset_category"),
            location=d.get("location"),
            address=d.get("address"),
            country=d.get("country"),
            acquisition_date=self._parse_datetime(d.get("acquisition_date")),
            acquisition_value=d.get("acquisition_value"),
            current_status=d.get("current_status"),
            contacts=self._parse_contacts(d.get("contacts")),
            projects=self._parse_list(d.get("projects")),
        )

    def _parse_concept(self, d: dict[str, Any]) -> ConceptFrontmatter:
        """Parse un frontmatter CONCEPT."""
        base = self._parse_base(d)
        return ConceptFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.CONCEPT,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Concept-specific fields
            concept_type=d.get("concept_type"),
            domain=d.get("domain"),
            difficulty=d.get("difficulty"),
            maturity=d.get("maturity"),
            last_reviewed=self._parse_datetime(d.get("last_reviewed")),
            sources=self._parse_list(d.get("sources")),
            inspired_by=d.get("inspired_by"),
            duration=d.get("duration"),
            prerequisites=self._parse_list(d.get("prerequisites")),
        )

    def _parse_ressource(self, d: dict[str, Any]) -> RessourceFrontmatter:
        """Parse un frontmatter RESSOURCE."""
        base = self._parse_base(d)
        return RessourceFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.RESSOURCE,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Ressource-specific fields
            resource_type=d.get("resource_type"),
            author=d.get("author"),
            publisher=d.get("publisher"),
            year=int(d["year"]) if d.get("year") else None,
            url=d.get("url"),
            isbn=d.get("isbn"),
            status=d.get("status"),
            started_at=self._parse_datetime(d.get("started_at")),
            finished_at=self._parse_datetime(d.get("finished_at")),
            rating=int(d["rating"]) if d.get("rating") else None,
            topics=self._parse_list(d.get("topics")),
            recommended_by=d.get("recommended_by"),
        )

    def _parse_lieu(self, d: dict[str, Any]) -> LieuFrontmatter:
        """Parse un frontmatter LIEU."""
        base = self._parse_base(d)
        return LieuFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.LIEU,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Lieu-specific fields
            lieu_type=d.get("lieu_type"),
            address=d.get("address"),
            city=d.get("city"),
            country=d.get("country"),
            gps=d.get("gps"),
            maps_url=d.get("maps_url"),
            phone=d.get("phone"),
            website=d.get("website"),
            email=d.get("email"),
            rating=int(d["rating"]) if d.get("rating") else None,
            price_range=d.get("price_range"),
            last_visit=self._parse_datetime(d.get("last_visit")),
            recommended_by=d.get("recommended_by"),
            visited_with=self._parse_list(d.get("visited_with")),
        )

    def _parse_produit(self, d: dict[str, Any]) -> ProduitFrontmatter:
        """Parse un frontmatter PRODUIT."""
        base = self._parse_base(d)
        return ProduitFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.PRODUIT,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Produit-specific fields
            product_type=d.get("product_type"),
            brand=d.get("brand"),
            model=d.get("model"),
            version=d.get("version"),
            purchase_date=self._parse_datetime(d.get("purchase_date")),
            purchase_price=d.get("purchase_price"),
            purchase_location=d.get("purchase_location"),
            warranty_until=self._parse_datetime(d.get("warranty_until")),
            status=d.get("status"),
            rating=int(d["rating"]) if d.get("rating") else None,
            website=d.get("website"),
            documentation=d.get("documentation"),
            related_products=self._parse_list(d.get("related_products")),
        )

    def _parse_decision(self, d: dict[str, Any]) -> DecisionFrontmatter:
        """Parse un frontmatter DECISION."""
        base = self._parse_base(d)
        return DecisionFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.DECISION,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Decision-specific fields
            decision_date=self._parse_datetime(d.get("decision_date")),
            decision_maker=d.get("decision_maker"),
            domain=d.get("domain"),
            reversible=d.get("reversible"),
            impact=d.get("impact"),
            confidence=d.get("confidence"),
            outcome=d.get("outcome"),
            reviewed_at=self._parse_datetime(d.get("reviewed_at")),
            related_project=d.get("related_project"),
            stakeholders=self._parse_list(d.get("stakeholders")),
        )

    def _parse_objectif(self, d: dict[str, Any]) -> ObjectifFrontmatter:
        """Parse un frontmatter OBJECTIF."""
        base = self._parse_base(d)
        return ObjectifFrontmatter(
            # Base fields
            title=base.title,
            type=NoteType.OBJECTIF,
            aliases=base.aliases,
            created_at=base.created_at,
            updated_at=base.updated_at,
            source=base.source,
            source_id=base.source_id,
            importance=base.importance,
            tags=base.tags,
            category=base.category,
            related=base.related,
            linked_sources=base.linked_sources,
            pending_updates=base.pending_updates,
            _raw_metadata=base._raw_metadata,
            # Objectif-specific fields
            horizon=d.get("horizon"),
            domain=d.get("domain"),
            target_date=self._parse_datetime(d.get("target_date")),
            started_at=self._parse_datetime(d.get("started_at")),
            status=d.get("status"),
            progress=int(d["progress"]) if d.get("progress") is not None else None,
            kpis=self._parse_list(d.get("kpis")),
            current_value=d.get("current_value"),
            target_value=d.get("target_value"),
            parent_objective=d.get("parent_objective"),
            contributing_projects=self._parse_list(d.get("contributing_projects")),
        )

    # === HELPER METHODS ===

    def _parse_note_type(self, value: Any) -> NoteType:
        """Parse un NoteType depuis une valeur."""
        if not value:
            return NoteType.AUTRE
        try:
            return NoteType(str(value).lower())
        except ValueError:
            return NoteType.AUTRE

    def _parse_importance(self, value: Any) -> Optional[ImportanceLevel]:
        """Parse un ImportanceLevel depuis une valeur."""
        if not value:
            return None
        try:
            return ImportanceLevel(str(value).lower())
        except ValueError:
            # Try French mapping
            return ImportanceLevel.from_french(str(value))

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse une datetime depuis diverses représentations."""
        if not value:
            return None

        # Already a datetime
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        # String ISO format
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                pass

            # Try date-only format
            try:
                dt = datetime.strptime(value, "%Y-%m-%d")
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        return None

    def _parse_list(self, value: Any) -> list[str]:
        """Parse une liste de strings."""
        if not value:
            return []
        if isinstance(value, list):
            return [str(v) for v in value if v]
        if isinstance(value, str):
            return [value]
        return []

    def _parse_stakeholders(self, value: Any) -> list[Stakeholder]:
        """Parse une liste de Stakeholder."""
        if not value or not isinstance(value, list):
            return []

        result = []
        for item in value:
            if isinstance(item, dict):
                person = item.get("person", "")
                role = item.get("role", "")
                if person:
                    result.append(Stakeholder(person=person, role=role))
        return result

    def _parse_contacts(self, value: Any) -> list[Contact]:
        """Parse une liste de Contact."""
        if not value or not isinstance(value, list):
            return []

        result = []
        for item in value:
            if isinstance(item, dict):
                person = item.get("person", "")
                role = item.get("role", "")
                if person:
                    result.append(Contact(person=person, role=role))
        return result

    def _parse_linked_sources(self, value: Any) -> list[LinkedSource]:
        """Parse une liste de LinkedSource."""
        if not value or not isinstance(value, list):
            return []

        result = []
        for item in value:
            if isinstance(item, dict):
                source_type = item.get("type", "")
                # Get identifier from type-specific key
                identifier = (
                    item.get("path")
                    or item.get("contact")
                    or item.get("filter")
                    or item.get("chat")
                    or item.get("identifier")
                    or ""
                )
                priority = int(item.get("priority", 2))
                if source_type and identifier:
                    result.append(
                        LinkedSource(type=source_type, identifier=identifier, priority=priority)
                    )
        return result

    def _parse_pending_updates(self, value: Any) -> list[PendingUpdate]:
        """Parse une liste de PendingUpdate."""
        if not value or not isinstance(value, list):
            return []

        result = []
        for item in value:
            if isinstance(item, dict):
                field_name = item.get("field", "")
                if field_name:
                    result.append(
                        PendingUpdate(
                            field=field_name,
                            value=item.get("value"),
                            source=item.get("source", ""),
                            source_ref=item.get("source_ref"),
                            detected_at=self._parse_datetime(item.get("detected_at"))
                            or datetime.now(timezone.utc),
                            confidence=float(item.get("confidence", 0.0)),
                        )
                    )
        return result

    def to_dict(self, frontmatter: AnyFrontmatter) -> dict[str, Any]:
        """
        Convertit un frontmatter typé en dict YAML.

        Args:
            frontmatter: Frontmatter typé

        Returns:
            Dict prêt pour yaml.dump()
        """
        return frontmatter.to_dict()
