"""
Modèles de données pour Workflow v2.1

Ce module définit les structures de données pour le pipeline d'analyse
et d'enrichissement des connaissances.

Classes:
    - Extraction: Une information extraite d'un événement
    - AnalysisResult: Résultat complet de l'analyse d'un événement
    - EnrichmentResult: Résultat de l'application des extractions au PKM
    - ContextNote: Note de contexte pour enrichir le prompt
    - NoteResult: Résultat d'une opération sur une note
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ExtractionType(str, Enum):
    """Types d'informations extractibles"""

    DECISION = "decision"
    ENGAGEMENT = "engagement"
    FAIT = "fait"
    DEADLINE = "deadline"
    RELATION = "relation"


class ImportanceLevel(str, Enum):
    """Niveaux d'importance"""

    HAUTE = "haute"
    MOYENNE = "moyenne"


class NoteAction(str, Enum):
    """Actions possibles sur les notes"""

    ENRICHIR = "enrichir"
    CREER = "creer"


class EmailAction(str, Enum):
    """Actions possibles sur l'email après analyse"""

    ARCHIVE = "archive"
    FLAG = "flag"
    QUEUE = "queue"
    DELETE = "delete"
    RIEN = "rien"


@dataclass
class Extraction:
    """
    Une information extraite d'un événement.

    Représente une unité de connaissance permanente à intégrer
    dans le PKM (Personal Knowledge Management).

    Attributes:
        info: Description concise de l'information (ex: "Budget validé 50k€")
        type: Type d'information (decision, engagement, fait, deadline, relation)
        importance: Niveau d'importance (haute, moyenne)
        note_cible: Titre de la note où stocker l'information
        note_action: Action à effectuer (enrichir ou creer)
        omnifocus: Si True, créer aussi une tâche OmniFocus

    Example:
        >>> extraction = Extraction(
        ...     info="Marc livrera le rapport lundi",
        ...     type=ExtractionType.ENGAGEMENT,
        ...     importance=ImportanceLevel.HAUTE,
        ...     note_cible="Projet Alpha",
        ...     note_action=NoteAction.ENRICHIR,
        ...     omnifocus=True
        ... )
    """

    info: str
    type: ExtractionType
    importance: ImportanceLevel
    note_cible: str
    note_action: NoteAction
    omnifocus: bool = False

    def __post_init__(self) -> None:
        """Validation et normalisation après initialisation"""
        # Convertir les strings en enums si nécessaire
        if isinstance(self.type, str):
            self.type = ExtractionType(self.type)
        if isinstance(self.importance, str):
            self.importance = ImportanceLevel(self.importance)
        if isinstance(self.note_action, str):
            self.note_action = NoteAction(self.note_action)

        # Valider que info n'est pas vide
        if not self.info or not self.info.strip():
            raise ValueError("info ne peut pas être vide")

        # Valider que note_cible n'est pas vide
        if not self.note_cible or not self.note_cible.strip():
            raise ValueError("note_cible ne peut pas être vide")


@dataclass
class AnalysisResult:
    """
    Résultat de l'analyse d'un événement.

    Contient toutes les extractions identifiées ainsi que les métadonnées
    de l'analyse (modèle utilisé, confiance, etc.).

    Attributes:
        extractions: Liste des informations extraites
        action: Action recommandée sur l'email (archive, flag, queue, rien)
        confidence: Score de confiance [0.0, 1.0]
        raisonnement: Explication courte de l'analyse
        model_used: Modèle AI utilisé (haiku, sonnet)
        tokens_used: Nombre de tokens consommés
        duration_ms: Durée de l'analyse en millisecondes
        timestamp: Horodatage de l'analyse
        escalated: Si True, l'analyse a été escaladée vers un modèle plus puissant

    Example:
        >>> result = AnalysisResult(
        ...     extractions=[],
        ...     action=EmailAction.ARCHIVE,
        ...     confidence=0.92,
        ...     raisonnement="Newsletter sans information permanente",
        ...     model_used="haiku",
        ...     tokens_used=450,
        ...     duration_ms=1200.5
        ... )
    """

    extractions: list[Extraction]
    action: EmailAction
    confidence: float
    raisonnement: str
    model_used: str
    tokens_used: int
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    escalated: bool = False

    def __post_init__(self) -> None:
        """Validation après initialisation"""
        # Convertir action en enum si nécessaire
        if isinstance(self.action, str):
            self.action = EmailAction(self.action)

        # Valider confidence dans [0, 1]
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence doit être entre 0 et 1, reçu: {self.confidence}")

        # Valider tokens_used positif
        if self.tokens_used < 0:
            raise ValueError(f"tokens_used doit être >= 0, reçu: {self.tokens_used}")

        # Valider duration_ms positif
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms doit être >= 0, reçu: {self.duration_ms}")

    @property
    def has_extractions(self) -> bool:
        """Retourne True si au moins une extraction a été identifiée"""
        return len(self.extractions) > 0

    @property
    def high_confidence(self) -> bool:
        """Retourne True si la confiance est >= 0.85 (seuil auto-application)"""
        return self.confidence >= 0.85

    @property
    def extraction_count(self) -> int:
        """Nombre d'extractions"""
        return len(self.extractions)

    @property
    def omnifocus_tasks_count(self) -> int:
        """Nombre d'extractions avec tâche OmniFocus"""
        return sum(1 for e in self.extractions if e.omnifocus)


@dataclass
class NoteResult:
    """
    Résultat d'une opération sur une note.

    Attributes:
        note_id: Identifiant de la note
        created: True si la note a été créée (vs enrichie)
        title: Titre de la note
        error: Message d'erreur si l'opération a échoué
    """

    note_id: str
    created: bool = False
    title: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Retourne True si l'opération a réussi"""
        return self.error is None


@dataclass
class EnrichmentResult:
    """
    Résultat de l'application des extractions au PKM.

    Contient les listes des notes mises à jour/créées et des tâches créées.

    Attributes:
        notes_updated: IDs des notes enrichies
        notes_created: IDs des notes nouvellement créées
        tasks_created: IDs des tâches OmniFocus créées
        errors: Liste des erreurs rencontrées

    Example:
        >>> result = EnrichmentResult(
        ...     notes_updated=["note_123", "note_456"],
        ...     notes_created=["note_new"],
        ...     tasks_created=["task_789"],
        ...     errors=[]
        ... )
        >>> result.success
        True
        >>> result.total_notes_affected
        3
    """

    notes_updated: list[str] = field(default_factory=list)
    notes_created: list[str] = field(default_factory=list)
    tasks_created: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Retourne True si aucune erreur"""
        return len(self.errors) == 0

    @property
    def total_notes_affected(self) -> int:
        """Nombre total de notes affectées"""
        return len(self.notes_updated) + len(self.notes_created)

    @property
    def has_changes(self) -> bool:
        """Retourne True si des changements ont été effectués"""
        return self.total_notes_affected > 0 or len(self.tasks_created) > 0


@dataclass
class ContextNote:
    """
    Note de contexte pour enrichir le prompt d'analyse.

    Représente un résumé d'une note existante utilisée pour fournir
    du contexte à l'IA lors de l'analyse d'un événement.

    Attributes:
        title: Titre de la note
        type: Type de note (personne, projet, concept, etc.)
        content_summary: Résumé du contenu (max ~300 caractères)
        relevance: Score de pertinence [0.0, 1.0]
        note_id: Identifiant optionnel de la note source

    Example:
        >>> context = ContextNote(
        ...     title="Projet Alpha",
        ...     type="projet",
        ...     content_summary="Projet de refonte API, deadline mars 2026...",
        ...     relevance=0.87,
        ...     note_id="projets/alpha"
        ... )
    """

    title: str
    type: str
    content_summary: str
    relevance: float
    note_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validation après initialisation"""
        # Valider relevance dans [0, 1]
        if not 0.0 <= self.relevance <= 1.0:
            raise ValueError(f"relevance doit être entre 0 et 1, reçu: {self.relevance}")

        # Valider title non vide
        if not self.title or not self.title.strip():
            raise ValueError("title ne peut pas être vide")
