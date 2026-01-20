"""
Note Types and Categories

Defines note types, importance levels, and review configurations
for the spaced repetition system.
"""

from dataclasses import dataclass, field
from enum import Enum


class CycleType(str, Enum):
    """
    Types de cycles de révision (v2: Memory Cycles)

    - RETOUCHE: Cycle IA pour amélioration automatique des notes
    - LECTURE: Cycle humain pour révision espacée par Johan
    """

    RETOUCHE = "retouche"  # IA améliore automatiquement
    LECTURE = "lecture"  # Johan révise manuellement


class NoteType(str, Enum):
    """
    Types de notes supportés

    Chaque type correspond à un dossier dans la base de notes
    et possède des caractéristiques de révision spécifiques.
    """

    ENTITE = "entite"  # Organisations, entreprises, concepts
    EVENEMENT = "evenement"  # Événements ponctuels importants
    PERSONNE = "personne"  # Fiches contacts enrichies
    PROCESSUS = "processus"  # Procédures, workflows
    PROJET = "projet"  # Projets actifs ou archivés
    REUNION = "reunion"  # Comptes-rendus de réunions
    SOUVENIR = "souvenir"  # Mémoires personnelles
    AUTRE = "autre"  # Notes non catégorisées

    @classmethod
    def from_folder(cls, folder_name: str) -> "NoteType":
        """
        Détermine le type de note à partir du nom de dossier

        Args:
            folder_name: Nom du dossier (ex: "Personnes", "Projets")

        Returns:
            NoteType correspondant ou AUTRE si non reconnu
        """
        mapping = {
            "entites": cls.ENTITE,
            "entités": cls.ENTITE,
            "evenements": cls.EVENEMENT,
            "événements": cls.EVENEMENT,
            "personnes": cls.PERSONNE,
            "processus": cls.PROCESSUS,
            "projets": cls.PROJET,
            "reunions": cls.REUNION,
            "réunions": cls.REUNION,
            "souvenirs": cls.SOUVENIR,
        }
        return mapping.get(folder_name.lower(), cls.AUTRE)

    @property
    def folder_name(self) -> str:
        """Retourne le nom de dossier standard pour ce type"""
        names = {
            NoteType.ENTITE: "Entités",
            NoteType.EVENEMENT: "Événements",
            NoteType.PERSONNE: "Personnes",
            NoteType.PROCESSUS: "Processus",
            NoteType.PROJET: "Projets",
            NoteType.REUNION: "Réunions",
            NoteType.SOUVENIR: "Souvenirs",
            NoteType.AUTRE: "Notes",
        }
        return names[self]


class ImportanceLevel(str, Enum):
    """
    Niveaux d'importance pour la priorisation des révisions
    Supporte les valeurs anglaises (interne) et françaises (frontmatter).
    """

    CRITICAL = "critical"  # critique
    HIGH = "high"  # haute
    NORMAL = "normal"  # moyenne
    LOW = "low"  # basse
    ARCHIVE = "archive"  # archive

    @classmethod
    def from_french(cls, value: str) -> "ImportanceLevel":
        mapping = {
            "critique": cls.CRITICAL,
            "haute": cls.HIGH,
            "moyenne": cls.NORMAL,
            "basse": cls.LOW,
            "archive": cls.ARCHIVE,
        }
        return mapping.get(value.lower(), cls.NORMAL)


class NoteStatus(str, Enum):
    """
    Statut de la note (cycle de vie)
    """

    ACTIF = "actif"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    ARCHIVE = "archive"
    BROUILLON = "brouillon"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return any(value.lower() == item.value for item in cls)


class Relation(str, Enum):
    """
    Type de relation avec Johan.
    Utilisé pour qualifier les contacts dans les notes PERSONNE.
    """

    AMI = "ami"
    FAMILLE = "famille"
    COLLEGUE = "collègue"
    CLIENT = "client"
    PARTENAIRE = "partenaire"
    FOURNISSEUR = "fournisseur"
    CONNAISSANCE = "connaissance"
    ADMINISTRATION = "administration"

    @classmethod
    def from_string(cls, value: str) -> "Relation | None":
        """Parse une relation depuis une string (insensible à la casse)."""
        if not value:
            return None
        normalized = value.lower().strip()
        for item in cls:
            if item.value == normalized:
                return item
        return None


class RelationshipStrength(str, Enum):
    """
    Force de la relation avec un contact.
    Aide à prioriser les notes importantes.
    """

    FORTE = "forte"
    MOYENNE = "moyenne"
    FAIBLE = "faible"
    NOUVELLE = "nouvelle"

    @classmethod
    def from_string(cls, value: str) -> "RelationshipStrength | None":
        """Parse depuis une string."""
        if not value:
            return None
        normalized = value.lower().strip()
        for item in cls:
            if item.value == normalized:
                return item
        return None


class ProjectStatus(str, Enum):
    """
    Statut d'un projet (différent de NoteStatus).
    Utilisé pour les notes de type PROJET.
    """

    ACTIF = "actif"
    EN_PAUSE = "en_pause"
    TERMINE = "terminé"
    ANNULE = "annulé"

    @classmethod
    def from_string(cls, value: str) -> "ProjectStatus | None":
        """Parse depuis une string."""
        if not value:
            return None
        normalized = value.lower().strip()
        for item in cls:
            if item.value == normalized:
                return item
        # Gérer les variantes sans accent
        if normalized == "termine":
            return cls.TERMINE
        if normalized == "annule":
            return cls.ANNULE
        return None


class EntityType(str, Enum):
    """
    Type d'entité/organisation.
    Utilisé pour les notes de type ENTITE.
    """

    ENTREPRISE = "entreprise"
    ADMINISTRATION = "administration"
    ASSOCIATION = "association"
    INSTITUTION = "institution"
    AUTRE = "autre"

    @classmethod
    def from_string(cls, value: str) -> "EntityType | None":
        """Parse depuis une string."""
        if not value:
            return None
        normalized = value.lower().strip()
        for item in cls:
            if item.value == normalized:
                return item
        return None


class Category(str, Enum):
    """
    Catégorie de note (domaine de vie).
    """

    WORK = "work"
    PERSONAL = "personal"
    FINANCE = "finance"
    HEALTH = "health"
    FAMILY = "family"
    OTHER = "other"

    @classmethod
    def from_string(cls, value: str) -> "Category | None":
        """Parse depuis une string."""
        if not value:
            return None
        normalized = value.lower().strip()
        for item in cls:
            if item.value == normalized:
                return item
        return None


@dataclass(frozen=True)
class ReviewConfig:
    """
    Configuration de révision pour un type de note

    Attributes:
        base_interval_hours: Intervalle initial en heures
        max_interval_days: Intervalle maximum en jours
        easiness_factor: Facteur de facilité initial (1.3-2.5)
        auto_enrich: Activer l'enrichissement automatique
        web_search_default: Activer la recherche web par défaut
        skip_revision: Ne jamais réviser ce type (ex: souvenirs)
    """

    base_interval_hours: float = 2.0
    max_interval_days: int = 90
    easiness_factor: float = 2.5
    auto_enrich: bool = True
    web_search_default: bool = False
    skip_revision: bool = False


# Configuration par défaut pour chaque type de note
NOTE_TYPE_CONFIGS: dict[NoteType, ReviewConfig] = {
    NoteType.ENTITE: ReviewConfig(
        base_interval_hours=12.0,  # Entités changent peu
        max_interval_days=90,
        easiness_factor=2.5,
        auto_enrich=True,
        web_search_default=False,
    ),
    NoteType.EVENEMENT: ReviewConfig(
        base_interval_hours=24.0,  # Événements passés changent rarement
        max_interval_days=180,
        easiness_factor=2.5,
        auto_enrich=False,  # Préserver les événements tels quels
        web_search_default=False,
    ),
    NoteType.PERSONNE: ReviewConfig(
        base_interval_hours=2.0,  # Personnes : révision fréquente
        max_interval_days=30,  # Max 1 mois entre révisions
        easiness_factor=2.3,  # Légèrement plus exigeant
        auto_enrich=True,
        web_search_default=False,  # Désactivé par défaut (vie privée)
    ),
    NoteType.PROCESSUS: ReviewConfig(
        base_interval_hours=48.0,  # Processus changent sur demande
        max_interval_days=120,
        easiness_factor=2.5,
        auto_enrich=True,
        web_search_default=False,
    ),
    NoteType.PROJET: ReviewConfig(
        base_interval_hours=2.0,  # Projets actifs : très fréquent
        max_interval_days=14,  # Max 2 semaines
        easiness_factor=2.0,  # Plus exigeant
        auto_enrich=True,
        web_search_default=False,
    ),
    NoteType.REUNION: ReviewConfig(
        base_interval_hours=12.0,  # Réunions : révision modérée
        max_interval_days=60,
        easiness_factor=2.4,
        auto_enrich=True,  # Extraire les actions
        web_search_default=False,
    ),
    NoteType.SOUVENIR: ReviewConfig(
        base_interval_hours=0.0,  # Jamais réviser automatiquement
        max_interval_days=0,
        easiness_factor=2.5,
        auto_enrich=False,  # Ne jamais modifier
        web_search_default=False,
        skip_revision=True,  # Flag explicite
    ),
    NoteType.AUTRE: ReviewConfig(
        base_interval_hours=24.0,  # Par défaut : quotidien
        max_interval_days=60,
        easiness_factor=2.5,
        auto_enrich=False,  # Demander confirmation
        web_search_default=False,
    ),
}


@dataclass
class ConservationCriteria:
    """
    Critères de conservation vs suppression du contenu

    Utilisé pour déterminer quelles informations conserver
    lors de l'enrichissement et de la révision.
    """

    # Patterns à conserver (conservateur)
    keep_patterns: list[str] = field(
        default_factory=lambda: [
            r"dernier contact.*\d{4}",  # Dates de contact
            r"\[\s*\]",  # Actions non terminées
            r"projet.*\d{4}",  # Références projets avec dates
            r"\[\[.*\]\]",  # Wikilinks
            r"directeur|manager|responsable",  # Rôles professionnels
            r"travaille.*avec",  # Relations
        ]
    )

    # Durées avant suppression potentielle (en jours)
    obsolete_meeting_days: int = 30  # "Réunion mardi prochain"
    completed_minor_action_days: int = 14  # "[x] Appeler Jean"
    temporal_remark_days: int = 7  # "Cette semaine, faire X"

    # Seuils de confiance
    min_confidence_auto_archive: float = 0.95  # Archiver automatiquement
    min_confidence_suggest_removal: float = 0.80  # Proposer suppression


# Instance par défaut
DEFAULT_CONSERVATION_CRITERIA = ConservationCriteria()


def get_review_config(note_type: NoteType) -> ReviewConfig:
    """
    Récupère la configuration de révision pour un type de note

    Args:
        note_type: Type de note

    Returns:
        ReviewConfig pour ce type
    """
    return NOTE_TYPE_CONFIGS.get(note_type, NOTE_TYPE_CONFIGS[NoteType.AUTRE])


def detect_note_type_from_path(file_path: str) -> NoteType:
    """
    Détecte le type de note à partir du chemin du fichier

    Args:
        file_path: Chemin complet ou relatif du fichier

    Returns:
        NoteType détecté ou AUTRE
    """
    # Normaliser le chemin
    path_parts = file_path.replace("\\", "/").lower().split("/")

    # Chercher un dossier correspondant à un type
    for part in path_parts:
        note_type = NoteType.from_folder(part)
        if note_type != NoteType.AUTRE:
            return note_type

    return NoteType.AUTRE
