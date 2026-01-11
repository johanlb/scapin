# Modèles de Données

**Version** : 1.0.0-RC
**Dernière mise à jour** : 11 janvier 2026
**Nombre de modèles** : 120+

---

## Table des Matières

1. [Core Layer - Fondamentaux](#1-core-layer---fondamentaux)
2. [Jeeves - Modèles API](#2-jeeves---modèles-api)
3. [Passepartout - Base de Connaissances](#3-passepartout---base-de-connaissances)
4. [Intégrations Externes](#4-intégrations-externes)
5. [Patterns de Conception](#5-patterns-de-conception)

---

## 1. Core Layer - Fondamentaux

### 1.1 Événements Universels (`src/core/events/universal_event.py`)

#### Enums

| Enum | Valeurs | Usage |
|------|---------|-------|
| **EventSource** | EMAIL, TEAMS, FILE, QUESTION, DOCUMENT, CALENDAR, WEB, TASK, NOTE, UNKNOWN | Source événement |
| **EventType** | REQUEST, INFORMATION, DECISION_NEEDED, ACTION_REQUIRED, REMINDER, DEADLINE, REFERENCE, LEARNING, INSIGHT, STATUS_UPDATE, ERROR, CONFIRMATION, INVITATION, REPLY, UNKNOWN | Classification sémantique |
| **UrgencyLevel** | CRITICAL, HIGH, MEDIUM, LOW, NONE | Niveau d'urgence |

#### Entity (Dataclass)

```python
@dataclass
class Entity:
    type: str              # person, organization, date, location, topic, project, amount, url, phone
    value: str             # Valeur extraite
    confidence: float      # Score 0.0-1.0
    metadata: dict[str, Any]

    def __post_init__(self):
        # Validation: confidence in [0,1], value non-vide

    def __eq__(self, other):
        # Égalité basée sur type et value (insensible casse)

    def __hash__(self):
        # Hash pour sets/dicts
```

#### PerceivedEvent (Frozen Dataclass)

```python
@dataclass(frozen=True)
class PerceivedEvent:
    # Identité
    event_id: str                    # UUID unique
    source: EventSource              # Source (email, teams, calendar)
    source_id: str                   # ID dans système source

    # Timing
    occurred_at: datetime            # Quand événement s'est produit
    received_at: datetime            # Quand reçu
    perceived_at: datetime           # Quand analysé (default: now)

    # Contenu
    title: str                       # Titre/sujet
    content: str                     # Contenu complet

    # Classification
    event_type: EventType            # Type sémantique
    urgency: UrgencyLevel            # Niveau urgence

    # Extraction
    entities: list[Entity]           # Entités extraites
    topics: list[str]                # Thèmes principaux
    keywords: list[str]              # Mots-clés

    # Participants
    from_person: str                 # Expéditeur
    to_people: list[str]             # Destinataires
    cc_people: list[str]             # CC

    # Threading
    thread_id: Optional[str]         # ID conversation
    references: list[str]            # IDs liés
    in_reply_to: Optional[str]       # Réponse à

    # Attachements
    has_attachments: bool
    attachment_count: int
    attachment_types: list[str]
    urls: list[str]

    # Qualité
    perception_confidence: float     # Confiance 0-1
    needs_clarification: bool
    clarification_questions: list[str]

    # Métadonnées
    metadata: dict[str, Any]         # Données source-spécifiques
```

**Méthodes** :
- `get_entities_by_type(type: str) -> list[Entity]`
- `has_entity(type: str, value: str) -> bool`
- `is_part_of_thread() -> bool`
- `is_urgent() -> bool`
- `to_dict() -> dict[str, Any]`

---

### 1.2 Mémoire de Travail (`src/core/memory/working_memory.py`)

#### Enums

| Enum | Valeurs | Usage |
|------|---------|-------|
| **MemoryState** | INITIALIZED, PERCEIVING, REASONING, PLANNING, EXECUTING, COMPLETE, ARCHIVED | Cycle de vie |

#### Hypothesis (Dataclass)

```python
@dataclass
class Hypothesis:
    id: str
    description: str
    confidence: float               # Score 0-1
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    def add_evidence(self, evidence: str, supporting: bool)
    def update_confidence(self, new_confidence: float)
```

#### ReasoningPass (Dataclass)

```python
@dataclass
class ReasoningPass:
    pass_number: int                # 1-5
    pass_type: str                  # initial_analysis, context_enrichment, etc.
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]

    # État entrée
    input_confidence: float
    input_hypotheses_count: int

    # Actions
    context_queries: list[str]
    context_retrieved: list[str]
    ai_prompts: list[str]
    ai_responses: list[str]

    # État sortie
    output_confidence: float
    output_hypotheses_count: int
    confidence_delta: float

    # Insights
    insights: list[str]
    questions_raised: list[str]
    entities_extracted: list[str]

    metadata: dict[str, Any]

    def complete(self)              # Marque complétée + calcule durée
```

#### ContextItem (Dataclass)

```python
@dataclass
class ContextItem:
    source: str                     # pkm, memory, web
    type: str                       # note, entity, relationship
    content: str
    relevance_score: float          # 0-1
    retrieved_at: datetime
    metadata: dict[str, Any]
```

#### WorkingMemory (Class)

```python
class WorkingMemory:
    # État core
    event: PerceivedEvent
    state: MemoryState
    created_at: datetime
    updated_at: datetime

    # Raisonnement
    hypotheses: dict[str, Hypothesis]
    current_best_hypothesis: Optional[Hypothesis]
    overall_confidence: float
    reasoning_passes: list[ReasoningPass]
    current_pass: Optional[ReasoningPass]

    # Contexte
    context_items: list[ContextItem]
    related_events: list[str]

    # Incertitudes
    open_questions: list[str]
    uncertainties: list[str]

    # Continuité
    is_continuous: bool
    conversation_id: Optional[str]
    previous_events: list[PerceivedEvent]

    metadata: dict[str, Any]
```

**Méthodes principales** :
- `add_hypothesis(hypothesis, replace=False)`
- `get_top_hypotheses(n: int)`
- `start_reasoning_pass(pass_number, pass_type)`
- `complete_reasoning_pass()`
- `add_context(source, type, content, relevance)`
- `update_confidence(new_confidence)`
- `is_confident(threshold: float) -> bool`
- `needs_more_reasoning(threshold, max_passes) -> bool`
- `get_reasoning_summary() -> dict`

---

### 1.3 Configuration (`src/core/config_manager.py`)

#### EmailAccountConfig (Pydantic BaseModel)

```python
class EmailAccountConfig(BaseModel):
    # Identité
    account_id: str                  # Alphanumeric + _ -
    account_name: str                # Nom lisible
    enabled: bool = True

    # Connexion IMAP
    imap_host: str
    imap_port: int = 993             # 1-65535
    imap_username: EmailStr
    imap_password: str               # Min 8 chars
    imap_timeout: int = 30           # 5-300s
    imap_read_timeout: int = 60      # 10-600s

    # Dossiers
    inbox_folder: str = "INBOX"
    archive_folder: str = "Archive"
    reference_folder: str = "Référence"
    delete_folder: str = "_Scapin/À supprimer"

    # Traitement
    max_workers: int = 10            # 1-50
    batch_size: int = 100            # 1-1000
```

#### ProcessingConfig (Pydantic BaseModel)

```python
class ProcessingConfig(BaseModel):
    # Activation Pipeline Cognitif
    enable_cognitive_reasoning: bool = False
    cognitive_confidence_threshold: float = 0.85   # 0-1
    cognitive_timeout_seconds: int = 20            # 5-120s
    cognitive_max_passes: int = 5                  # 1-10
    fallback_on_failure: bool = True

    # Context Enrichment (Pass 2)
    enable_context_enrichment: bool = True
    context_top_k: int = 5                         # 1-20
    context_min_relevance: float = 0.3             # 0-1

    # Auto-Execution
    auto_execute_threshold: float = 0.85           # 0-1
    batch_size: int = 20                           # 1-100
    max_queue_size: int = 30                       # 1-200
    polling_interval_seconds: int = 300            # 60-3600s
```

#### ScapinConfig (Pydantic BaseSettings)

```python
class ScapinConfig(BaseSettings):
    environment: str                 # dev/prod
    email: EmailConfig               # Requis
    ai: AIConfig                     # Requis
    storage: StorageConfig
    integrations: IntegrationsConfig
    monitoring: MonitoringConfig
    processing: ProcessingConfig
    teams: TeamsConfig
    calendar: CalendarConfig
    briefing: BriefingConfig
    auth: AuthConfig
    api: APIConfig
```

---

### 1.4 Schémas Email (`src/core/schemas.py`)

#### Enums

| Enum | Valeurs |
|------|---------|
| **EmailAction** | DELETE, ARCHIVE, REFERENCE, KEEP, TASK, REPLY, DEFER, QUEUE |
| **EmailCategory** | PERSONAL, WORK, FINANCE, TRAVEL, SHOPPING, NEWSLETTER, SOCIAL, NOTIFICATION, SPAM, OTHER |
| **ProcessingMode** | AUTO, LEARNING, REVIEW |

#### EmailMetadata (Pydantic BaseModel)

```python
class EmailMetadata(BaseModel):
    id: int                          # UID IMAP
    folder: str = "INBOX"
    message_id: Optional[str]        # Header Message-ID

    from_address: EmailStr
    from_name: Optional[str]
    to_addresses: list[EmailStr]
    cc_addresses: list[EmailStr]
    bcc_addresses: list[EmailStr]

    subject: str                     # Min 1 char
    date: datetime

    has_attachments: bool = False
    attachments: list[EmailAttachment]
    size_bytes: Optional[int]
    flags: list[str]
    references: list[str]
    in_reply_to: Optional[str]
```

#### EmailAnalysis (Pydantic BaseModel)

```python
class EmailAnalysis(BaseModel):
    # Action principale
    action: EmailAction
    category: EmailCategory
    destination: Optional[str]       # Dossier archive
    confidence: int                  # 0-100
    reasoning: str                   # Min 10 chars

    # Multi-options
    options: list[ActionOption]
    summary: Optional[str]           # Résumé français

    # Entity Extraction
    entities: dict[str, Any]         # {person: [...], date: [...]}
    tags: list[str]
    related_emails: list[str]

    # Proposals
    proposed_notes: list[dict]       # ProposedNote serialized
    proposed_tasks: list[dict]       # ProposedTask serialized
    context_used: list[str]          # Note IDs utilisés

    # Draft Reply
    draft_reply: Optional[str]
```

---

### 1.5 Entités (`src/core/entities.py`)

#### Enums

| Enum | Valeurs |
|------|---------|
| **EntityType** | PERSON, DATE, PROJECT, ORGANIZATION, AMOUNT, LOCATION, URL, TOPIC, PHONE |
| **EntitySource** | EXTRACTION, AI_VALIDATION, USER, CONTEXT |

#### ProposedNote (Dataclass)

```python
@dataclass
class ProposedNote:
    action: str                      # "create" ou "enrich"
    note_type: str                   # personne, projet, etc.
    title: str
    content_summary: str
    entities: list[Entity]
    suggested_tags: list[str]
    confidence: float = 0.0          # 0-1
    reasoning: str
    target_note_id: Optional[str]    # Si enrich
    source_email_id: str

    # AUTO_APPLY_THRESHOLD = 0.90
```

#### ProposedTask (Dataclass)

```python
@dataclass
class ProposedTask:
    title: str
    note: str = ""
    project: Optional[str]           # Projet OmniFocus
    tags: list[str]
    due_date: Optional[datetime]
    defer_date: Optional[datetime]
    confidence: float
    reasoning: str
    source_email_id: str
```

---

### 1.6 Événements de Traitement (`src/core/processing_events.py`)

#### ProcessingEventType (Enum)

```python
class ProcessingEventType(str, Enum):
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    ACCOUNT_STARTED = "account_started"
    ACCOUNT_COMPLETED = "account_completed"
    ACCOUNT_ERROR = "account_error"
    EMAIL_STARTED = "email_started"
    EMAIL_ANALYZING = "email_analyzing"
    EMAIL_COMPLETED = "email_completed"
    EMAIL_QUEUED = "email_queued"
    EMAIL_EXECUTED = "email_executed"
    EMAIL_ERROR = "email_error"
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"
    BATCH_PROGRESS = "batch_progress"
    SYSTEM_READY = "system_ready"
    SYSTEM_ERROR = "system_error"
```

#### ProcessingEvent (Dataclass)

```python
@dataclass
class ProcessingEvent:
    event_type: ProcessingEventType
    timestamp: datetime

    # Context compte
    account_id: Optional[str]
    account_name: Optional[str]

    # Context email
    email_id: Optional[int]
    subject: Optional[str]
    from_address: Optional[str]
    email_date: Optional[datetime]
    preview: Optional[str]           # Max 80 chars

    # Analyse
    action: Optional[str]
    confidence: Optional[int]        # 0-100
    category: Optional[str]
    reasoning: Optional[str]

    # Progression
    current: Optional[int]
    total: Optional[int]

    # Erreurs
    error: Optional[str]
    error_type: Optional[str]

    metadata: dict[str, Any]
```

#### EventBus (Class - Thread-safe)

```python
class EventBus:
    _subscribers: dict[ProcessingEventType, list[Callable]]
    _lock: threading.Lock
    _event_count: int                # Limit 10000

    def subscribe(event_type, callback)
    def unsubscribe(event_type, callback)
    def emit(event: ProcessingEvent)
    def clear()
    def get_subscriber_count()
    def get_event_count()
```

---

## 2. Jeeves - Modèles API

### 2.1 Réponses (`src/jeeves/api/models/responses.py`)

#### APIResponse (Generic)

```python
class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    timestamp: datetime
```

#### PaginatedResponse (Generic)

```python
class PaginatedResponse(APIResponse[T]):
    total: int
    page: int
    page_size: int
    has_more: bool
```

### 2.2 Queue (`src/jeeves/api/models/queue.py`)

#### QueueItemResponse

```python
class QueueItemResponse(BaseModel):
    id: str
    account_id: str
    queued_at: datetime
    metadata: QueueItemMetadata
    analysis: QueueItemAnalysis
    content: QueueItemContent
    status: str                      # pending, approved, rejected, skipped
    reviewed_at: Optional[datetime]
    review_decision: Optional[str]
```

#### QueueStatsResponse

```python
class QueueStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_account: dict[str, int]
    oldest_item: Optional[str]
    newest_item: Optional[str]
```

### 2.3 Notes (`src/jeeves/api/models/notes.py`)

#### NoteResponse

```python
class NoteResponse(BaseModel):
    id: str                          # note_id
    title: str
    content: str                     # Markdown
    excerpt: str
    path: str
    tags: list[str]
    entities: list[dict]
    created_at: datetime
    updated_at: datetime
    pinned: bool
    metadata: dict
```

#### NotesTreeResponse

```python
class NotesTreeResponse(BaseModel):
    folders: list[FolderNode]
    pinned: list[NoteResponse]
    recent: list[NoteResponse]
    total_notes: int
```

### 2.4 Calendar (`src/jeeves/api/models/calendar.py`)

#### Enums

| Enum | Valeurs |
|------|---------|
| **ConflictType** | OVERLAP_FULL, OVERLAP_PARTIAL, TRAVEL_TIME |
| **ConflictSeverity** | HIGH, MEDIUM, LOW |

#### CalendarEventResponse

```python
class CalendarEventResponse(BaseModel):
    id: str
    title: str
    start: datetime
    end: datetime
    location: Optional[str]
    is_online: bool
    meeting_url: Optional[str]
    organizer: str
    attendees: list[CalendarAttendeeResponse]
    is_all_day: bool
    is_recurring: bool
    description: Optional[str]
    status: str
```

---

## 3. Passepartout - Base de Connaissances

### 3.1 Types Notes (`src/passepartout/note_types.py`)

#### Enums

| Enum | Valeurs |
|------|---------|
| **NoteType** | ENTITE, EVENEMENT, PERSONNE, PROCESSUS, PROJET, REUNION, SOUVENIR, AUTRE |
| **ImportanceLevel** | CRITICAL, HIGH, NORMAL, LOW, ARCHIVE |

#### ReviewConfig (Frozen Dataclass)

```python
@dataclass(frozen=True)
class ReviewConfig:
    base_interval_hours: float = 2.0
    max_interval_days: int = 90
    easiness_factor: float = 2.5     # 1.3-2.5
    auto_enrich: bool = True
    web_search_default: bool = False
    skip_revision: bool = False
```

**Configs prédéfinies** dans `NOTE_TYPE_CONFIGS` par NoteType.

### 3.2 Cross-Source (`src/passepartout/cross_source/models.py`)

#### Enums

| Enum | Valeurs |
|------|---------|
| **SourceType** | EMAIL, CALENDAR, TEAMS, WHATSAPP, FILES, WEB, NOTES |
| **ItemType** | MESSAGE, EVENT, FILE, WEB_RESULT, NOTE |

#### SourceItem (Dataclass)

```python
@dataclass
class SourceItem:
    source: str
    type: str
    title: str
    content: str                     # Max 500 chars
    timestamp: datetime
    relevance_score: float           # 0-1
    url: str | None
    metadata: dict[str, Any]
    final_score: float = 0.0         # Après pondération
```

#### CrossSourceResult (Dataclass)

```python
@dataclass
class CrossSourceResult:
    query: str
    items: list[SourceItem]
    sources_searched: list[str]
    sources_failed: list[str]
    total_results: int
    search_duration_ms: int
    from_cache: bool = False
```

### 3.3 Workflow v2.1.1 (`src/core/models/v2_models.py`)

> **Version** : 2.1.1 (11 janvier 2026)
> Modèles pour l'analyse et l'extraction de connaissances des événements.

#### Enums

| Enum | Valeurs | Description |
|------|---------|-------------|
| **ExtractionType** | DECISION, ENGAGEMENT, FAIT, DEADLINE, EVENEMENT, RELATION, COORDONNEES, MONTANT, REFERENCE, DEMANDE, CITATION, OBJECTIF, COMPETENCE, PREFERENCE | 14 types d'information extractibles |
| **ImportanceLevel** | HAUTE, MOYENNE, BASSE | 3 niveaux d'importance pour les extractions |
| **NoteAction** | ENRICHIR, CREER | Action sur la note cible |
| **EmailAction** | ARCHIVE, FLAG, QUEUE, DELETE, RIEN | Action sur l'événement après analyse |

#### ExtractionType (Détail)

| Type | Usage | OmniFocus |
|------|-------|-----------|
| **decision** | Choix actés, arbitrages | Non |
| **engagement** | Promesses, obligations | Oui si deadline |
| **fait** | Faits importants, événements passés | Non |
| **deadline** | Dates limites avec conséquences | **Toujours** |
| **evenement** | Dates sans obligation (réunion, anniversaire) | Optionnel |
| **relation** | Liens entre personnes/projets | Non |
| **coordonnees** | Téléphone, adresse, email de contacts | Non |
| **montant** | Valeurs financières, factures, contrats | Non |
| **reference** | Numéros de dossier, facture, ticket | Non |
| **demande** | Requêtes faites à Johan | Oui si deadline |
| **citation** | Propos exacts à retenir (verbatim) | Non |
| **objectif** | Buts, cibles, KPIs mentionnés | Non |
| **competence** | Expertise/compétences d'une personne | Non |
| **preference** | Préférences de travail d'une personne | Non |

#### ImportanceLevel (Détail)

| Niveau | Description | Icône |
|--------|-------------|-------|
| **HAUTE** | Critique, impact fort, à ne pas rater | 🔴 |
| **MOYENNE** | Utile, bon à savoir | 🟡 |
| **BASSE** | Contexte, référence future (ex: numéros, coordonnées) | ⚪ |

#### Extraction (Dataclass)

```python
@dataclass
class Extraction:
    info: str                    # Description concise (1-2 phrases)
    type: ExtractionType         # Type d'information
    importance: ImportanceLevel  # Niveau d'importance
    note_cible: str              # Titre de la note où stocker
    note_action: NoteAction      # enrichir ou creer
    omnifocus: bool = False      # Créer tâche OmniFocus ?
```

#### AnalysisResult (Dataclass)

```python
@dataclass
class AnalysisResult:
    extractions: list[Extraction]
    action: EmailAction
    confidence: float            # 0.0-1.0
    raisonnement: str
    model_used: str              # haiku, sonnet
    tokens_used: int
    duration_ms: float
    escalated: bool = False      # True si escaladé vers modèle puissant

    # Properties
    @property
    def has_extractions(self) -> bool
    @property
    def high_confidence(self) -> bool  # >= 0.85
    @property
    def extraction_count(self) -> int
    @property
    def omnifocus_tasks_count(self) -> int
```

---

## 4. Intégrations Externes

### 4.1 Microsoft Teams (`src/integrations/microsoft/models.py`)

#### Enums

| Enum | Valeurs |
|------|---------|
| **TeamsChatType** | ONE_ON_ONE, GROUP, MEETING |
| **TeamsMessageImportance** | NORMAL, HIGH, URGENT |

#### TeamsMessage (Frozen Dataclass)

```python
@dataclass(frozen=True)
class TeamsMessage:
    message_id: str
    chat_id: str
    sender: TeamsSender
    content: str                     # HTML
    content_plain: str
    created_at: datetime
    importance: TeamsMessageImportance
    mentions: tuple[TeamsSender, ...]
    attachments: tuple[str, ...]
    is_reply: bool
    reply_to_id: Optional[str]
    chat: Optional[TeamsChat]
```

### 4.2 Microsoft Calendar (`src/integrations/microsoft/calendar_models.py`)

#### Enums

| Enum | Valeurs |
|------|---------|
| **CalendarResponseStatus** | NONE, ORGANIZER, TENTATIVELY_ACCEPTED, ACCEPTED, DECLINED, NOT_RESPONDED |
| **CalendarEventImportance** | LOW, NORMAL, HIGH |
| **CalendarEventShowAs** | FREE, TENTATIVE, BUSY, OOF, WORKING_ELSEWHERE, UNKNOWN |

#### CalendarEvent (Frozen Dataclass)

```python
@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    organizer: CalendarAttendee
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    is_recurring: bool
    attendees: tuple[CalendarAttendee, ...]
    locations: tuple[CalendarLocation, ...]
    importance: CalendarEventImportance
    sensitivity: CalendarEventSensitivity
    show_as: CalendarEventShowAs
    has_attachments: bool
    online_meeting_url: Optional[str]
    recurrence_pattern: Optional[str]
```

### 4.3 Apple Notes (`src/integrations/apple/notes_models.py`)

#### AppleNote (Dataclass)

```python
@dataclass
class AppleNote:
    id: str
    folder: str
    title: str
    content: str                     # HTML
    created_at: datetime
    modified_at: datetime
    pinned: bool
    labels: list[str]

    def content_as_markdown(self) -> str
    def content_as_text(self) -> str
```

#### SyncResult (Dataclass)

```python
@dataclass
class SyncResult:
    success: bool
    created_count: int
    updated_count: int
    deleted_count: int
    error_count: int
    errors: list[str]
```

---

## 5. Patterns de Conception

### 5.1 Immutabilité Hiérarchique

| Niveau | Type | Justification |
|--------|------|---------------|
| **Events universels** | `frozen=True` | Thread-safety, intégrité |
| **Working Memory** | Mutable | État évolutif |
| **Summaries/Results** | `frozen=True` | Immuable après création |
| **Config** | Pydantic | Validation + sérialisation |

### 5.2 Validation Exhaustive

```python
# Pydantic pour configs et API
class Config(BaseModel):
    value: int = Field(ge=0, le=100)

# Dataclass __post_init__ pour events
@dataclass
class Entity:
    confidence: float

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Invalid confidence")
```

### 5.3 Sérialisation Omniprésente

```python
# Tous les modèles ont to_dict()
def to_dict(self) -> dict[str, Any]:
    return {
        "field": self.field,
        "datetime_field": self.datetime_field.isoformat(),
    }

# Et from_dict() classmethod
@classmethod
def from_dict(cls, data: dict) -> "Self":
    return cls(**data)
```

### 5.4 Types Énumérés

- Tous les statuts/types utilisent Enum
- String value pour JSON sérialisation
- Validation automatique

```python
class EmailAction(str, Enum):
    DELETE = "delete"
    ARCHIVE = "archive"
    # ...
```

### 5.5 Champs Optionnels Robustes

```python
# Default sensé
field: Optional[str] = None

# Validation croisée
def __post_init__(self):
    if self.is_correction and not self.correct_action:
        raise ValueError("correct_action required when is_correction=True")
```

---

## Résumé par Domaine

| Domaine | Modèles Clés | Type |
|---------|--------------|------|
| **Core Events** | PerceivedEvent, Entity | Frozen Dataclass |
| **Core Memory** | WorkingMemory, Hypothesis, ReasoningPass | Mutable Class/Dataclass |
| **Core Config** | ScapinConfig, EmailConfig | Pydantic Settings |
| **Core Schemas** | EmailMetadata, EmailAnalysis | Pydantic BaseModel |
| **API Responses** | APIResponse[T], QueueItemResponse | Pydantic Generic |
| **Notes** | NoteType, ReviewConfig | Enum + Frozen Dataclass |
| **Cross-Source** | SourceItem, CrossSourceResult | Mutable Dataclass |
| **Teams** | TeamsMessage, TeamsChat | Frozen Dataclass |
| **Calendar** | CalendarEvent, CalendarAttendee | Frozen Dataclass |
| **Apple Notes** | AppleNote, SyncResult | Mutable Dataclass |
