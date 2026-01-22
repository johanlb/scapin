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

# Import unified EmailAction from schemas (single source of truth)
from src.core.schemas import EmailAction


class ExtractionType(str, Enum):
    """Types d'informations extractibles"""

    # Types originaux
    DECISION = "decision"
    ENGAGEMENT = "engagement"
    FAIT = "fait"
    DEADLINE = "deadline"
    RELATION = "relation"

    # Types ajoutés v2.1.1
    COORDONNEES = "coordonnees"  # Téléphone, adresse, email de contacts
    MONTANT = "montant"  # Valeurs financières, factures, contrats
    REFERENCE = "reference"  # Numéros de dossier, facture, ticket
    DEMANDE = "demande"  # Requêtes faites à Johan
    EVENEMENT = "evenement"  # Dates importantes sans obligation (réunion, anniversaire)
    CITATION = "citation"  # Propos importants à retenir verbatim
    OBJECTIF = "objectif"  # Buts, cibles, KPIs mentionnés
    COMPETENCE = "competence"  # Expertise/compétences d'une personne
    PREFERENCE = "preference"  # Préférences de travail d'une personne


class ImportanceLevel(str, Enum):
    """Niveaux d'importance"""

    HAUTE = "haute"  # Critique, à ne pas rater
    MOYENNE = "moyenne"  # Utile, bon à savoir
    BASSE = "basse"  # Contexte, référence future


class NoteAction(str, Enum):
    """Actions possibles sur les notes"""

    ENRICHIR = "enrichir"
    CREER = "creer"


# EmailAction is imported from src.core.schemas (unified enum)
# Available actions: DELETE, ARCHIVE, KEEP, QUEUE, FLAG, DEFER, REPLY


@dataclass
class Extraction:
    """
    Une information extraite d'un événement.

    Représente une unité de connaissance permanente à intégrer
    dans le PKM (Personal Knowledge Management).

    Attributes:
        info: Description concise de l'information (ex: "Budget validé 50k€")
        type: Type d'information (14 types: decision, engagement, fait, etc.)
        importance: Niveau d'importance (haute, moyenne, basse)
        note_cible: Titre de la note où stocker l'information
        note_action: Action à effectuer (enrichir ou creer)
        omnifocus: Si True, créer aussi une tâche OmniFocus
        calendar: Si True, créer aussi un événement calendrier (pour type evenement)
        date: Date associée au format YYYY-MM-DD (optionnel, pour deadlines/events)
        time: Heure associée au format HH:MM (optionnel, pour events)
        timezone: Fuseau horaire explicite (HF, HM, Maurice, UTC, Paris)
        duration: Durée en minutes (défaut 60 pour events)
        has_attachments: Signale des pièces jointes importantes
        priority: Priorité OmniFocus (haute, normale, basse)
        project: Projet OmniFocus cible

    Example:
        >>> extraction = Extraction(
        ...     info="Réunion le 25 janvier à 14h",
        ...     type=ExtractionType.EVENEMENT,
        ...     importance=ImportanceLevel.MOYENNE,
        ...     note_cible="Réunions",
        ...     note_action=NoteAction.ENRICHIR,
        ...     omnifocus=False,
        ...     calendar=True,
        ...     date="2026-01-25",
        ...     time="14:00",
        ...     timezone="HF",
        ...     duration=90
        ... )
    """

    info: str
    type: ExtractionType
    importance: ImportanceLevel
    note_cible: str
    note_action: NoteAction
    omnifocus: bool = False
    calendar: bool = False
    date: Optional[str] = None  # Format YYYY-MM-DD
    time: Optional[str] = None  # Format HH:MM
    # V2.1.2: New fields
    timezone: Optional[str] = None  # HF, HM, Maurice, UTC, Paris
    duration: Optional[int] = None  # Duration in minutes (default 60)
    has_attachments: bool = False  # Important attachments present
    priority: Optional[str] = None  # OmniFocus priority: haute, normale, basse
    project: Optional[str] = None  # OmniFocus project name

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
        pattern_matches: Patterns Sganarelle correspondants (validation)
        clarification_questions: Questions pour l'utilisateur si confiance basse
        needs_clarification: True si l'analyse nécessite une clarification humaine

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
    # V2.1.1: Draft reply suggestion
    draft_reply: Optional[str] = None
    # V2.2: Pattern validation (Sganarelle)
    pattern_matches: list["PatternMatch"] = field(default_factory=list)
    pattern_validated: bool = False
    pattern_confidence_boost: float = 0.0
    # V2.2: User clarification
    clarification_questions: list["ClarificationQuestion"] = field(default_factory=list)
    needs_clarification: bool = False

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

    @property
    def effective_confidence(self) -> float:
        """Confiance effective incluant le boost des patterns"""
        return min(1.0, self.confidence + self.pattern_confidence_boost)


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

    Contient les listes des notes mises à jour/créées, tâches et événements créés.

    Attributes:
        notes_updated: IDs des notes enrichies
        notes_created: IDs des notes nouvellement créées
        tasks_created: IDs des tâches OmniFocus créées
        events_created: IDs des événements calendrier créés
        errors: Liste des erreurs rencontrées

    Example:
        >>> result = EnrichmentResult(
        ...     notes_updated=["note_123", "note_456"],
        ...     notes_created=["note_new"],
        ...     tasks_created=["task_789"],
        ...     events_created=["event_456"],
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
    events_created: list[str] = field(default_factory=list)
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
        return (
            self.total_notes_affected > 0
            or len(self.tasks_created) > 0
            or len(self.events_created) > 0
        )


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


@dataclass
class CrossSourceContext:
    """
    Contexte récupéré depuis les sources croisées (emails, calendar, teams, etc.).

    Attributes:
        source: Source de l'information (email, calendar, teams, whatsapp, files, web)
        title: Titre ou sujet de l'item
        content_summary: Résumé du contenu
        relevance: Score de pertinence [0.0, 1.0]
        timestamp: Date de l'item source
        metadata: Métadonnées additionnelles
    """

    source: str
    title: str
    content_summary: str
    relevance: float
    timestamp: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class PatternMatch:
    """
    Un pattern Sganarelle qui correspond à l'événement.

    Attributes:
        pattern_id: Identifiant du pattern
        description: Description du pattern
        confidence: Confiance du pattern [0.0, 1.0]
        suggested_action: Action suggérée par le pattern
        occurrences: Nombre de fois que ce pattern a été observé
    """

    pattern_id: str
    description: str
    confidence: float
    suggested_action: str
    occurrences: int


@dataclass
class ClarificationQuestion:
    """
    Question à poser à l'utilisateur pour clarifier l'analyse.

    Attributes:
        question: La question à poser
        reason: Pourquoi cette clarification est nécessaire
        options: Options de réponse possibles (si applicable)
        priority: Priorité de la question (haute, moyenne, basse)
    """

    question: str
    reason: str
    options: list[str] = field(default_factory=list)
    priority: str = "moyenne"


class V2MemoryState(str, Enum):
    """États du cycle de vie de la mémoire de travail V2"""

    INITIALIZED = "initialized"
    CONTEXT_RETRIEVED = "context_retrieved"
    ANALYZING = "analyzing"
    PATTERN_VALIDATING = "pattern_validating"
    NEEDS_CLARIFICATION = "needs_clarification"
    APPLYING = "applying"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class V2WorkingMemory:
    """
    Mémoire de travail légère pour le Workflow V2.

    Version simplifiée de WorkingMemory qui trace l'état cognitif
    pendant le traitement d'un événement sans la complexité du multi-pass.

    Attributes:
        event_id: ID de l'événement en cours de traitement
        state: État actuel du traitement
        started_at: Horodatage du début
        context_notes: Notes de contexte récupérées
        cross_source_context: Contexte des sources croisées
        pattern_matches: Patterns Sganarelle correspondants
        analysis: Résultat de l'analyse (si disponible)
        clarification_questions: Questions en attente
        errors: Erreurs rencontrées
        trace: Journal des étapes de traitement

    Example:
        >>> memory = V2WorkingMemory(event_id="email_123")
        >>> memory.add_trace("Context retrieved", {"notes_count": 3})
        >>> memory.transition_to(V2MemoryState.ANALYZING)
    """

    event_id: str
    state: V2MemoryState = V2MemoryState.INITIALIZED
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Contexte
    context_notes: list["ContextNote"] = field(default_factory=list)
    cross_source_context: list["CrossSourceContext"] = field(default_factory=list)

    # Validation
    pattern_matches: list["PatternMatch"] = field(default_factory=list)

    # Résultat
    analysis: Optional["AnalysisResult"] = None

    # Clarification
    clarification_questions: list["ClarificationQuestion"] = field(default_factory=list)

    # Suivi
    errors: list[str] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)

    def transition_to(self, new_state: V2MemoryState) -> None:
        """Change l'état de la mémoire de travail"""
        old_state = self.state
        self.state = new_state
        self.add_trace(f"State transition: {old_state.value} → {new_state.value}")

        if new_state in (V2MemoryState.COMPLETE, V2MemoryState.FAILED):
            self.completed_at = datetime.now()

    def add_trace(self, message: str, metadata: Optional[dict] = None) -> None:
        """Ajoute une entrée au journal de trace"""
        self.trace.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "metadata": metadata or {},
        })

    def add_error(self, error: str) -> None:
        """Ajoute une erreur"""
        self.errors.append(error)
        self.add_trace(f"Error: {error}")

    @property
    def duration_ms(self) -> float:
        """Durée du traitement en millisecondes"""
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds() * 1000

    @property
    def total_context_items(self) -> int:
        """Nombre total d'items de contexte"""
        return len(self.context_notes) + len(self.cross_source_context)

    @property
    def has_errors(self) -> bool:
        """True si des erreurs ont été rencontrées"""
        return len(self.errors) > 0

    @property
    def is_complete(self) -> bool:
        """True si le traitement est terminé"""
        return self.state in (V2MemoryState.COMPLETE, V2MemoryState.FAILED)

    def to_dict(self) -> dict:
        """Exporte la mémoire de travail en dictionnaire (pour logs/debug)"""
        return {
            "event_id": self.event_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "context_notes_count": len(self.context_notes),
            "cross_source_count": len(self.cross_source_context),
            "pattern_matches_count": len(self.pattern_matches),
            "has_analysis": self.analysis is not None,
            "clarification_questions_count": len(self.clarification_questions),
            "errors": self.errors,
            "trace": self.trace,
        }
