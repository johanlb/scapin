# 01 - Core : Événements, Mémoire et Configuration

**Module** : `src/core/`
**Lignes de code** : ~8,500
**Rôle** : Fondations du système cognitif

---

## Vue d'Ensemble

Le module `src/core/` contient les briques fondamentales de SCAPIN :

```
src/core/
├── events/
│   ├── universal_event.py      # PerceivedEvent, Entity, Enums
│   └── normalizers/            # Convertisseurs source → PerceivedEvent
├── memory/
│   ├── working_memory.py       # WorkingMemory, Hypothesis, ReasoningPass
│   └── continuity_detector.py  # Détection conversations continues
├── extractors/
│   └── entity_extractor.py     # Extraction d'entités NER
├── config_manager.py           # Configuration Pydantic + .env
├── secrets.py                  # Keychain macOS
├── schemas.py                  # Schémas partagés (~1000 lignes)
├── interfaces.py               # Contrats abstraits (6 interfaces)
├── exceptions.py               # Hiérarchie d'exceptions
├── processing_events.py        # Event bus pub/sub
├── error_handling.py           # Patterns réutilisables
├── state_manager.py            # État de session
├── entities.py                 # Types d'entités
└── constants.py                # Constantes centralisées
```

---

## 1. Événements Universels

### 1.1 EventSource (Enum)

**Fichier** : `src/core/events/universal_event.py`

```python
class EventSource(str, Enum):
    EMAIL = "email"
    TEAMS = "teams"
    FILE = "file"
    QUESTION = "question"
    DOCUMENT = "document"
    CALENDAR = "calendar"
    WEB = "web"
    TASK = "task"
    NOTE = "note"
    UNKNOWN = "unknown"
```

**Usage** : Catégorise l'origine d'un événement.

---

### 1.2 EventType (Enum)

```python
class EventType(str, Enum):
    REQUEST = "request"              # Quelqu'un demande quelque chose
    INFORMATION = "information"      # FYI, news, updates
    DECISION_NEEDED = "decision"     # Requiert décision utilisateur
    ACTION_REQUIRED = "action"       # Utilisateur doit agir
    REMINDER = "reminder"            # Rappel temporel
    DEADLINE = "deadline"            # Contrainte de temps
    REFERENCE = "reference"          # À sauvegarder
    LEARNING = "learning"            # Contenu éducatif
    INSIGHT = "insight"              # Nouvelle compréhension
    STATUS_UPDATE = "status"         # Rapport de progression
    ERROR = "error"                  # Problème
    CONFIRMATION = "confirmation"    # Accusé de réception
    INVITATION = "invitation"        # Invitation réunion/événement
    REPLY = "reply"                  # Réponse à événement précédent
    UNKNOWN = "unknown"
```

**Usage** : Classification sémantique de haut niveau.

---

### 1.3 UrgencyLevel (Enum)

```python
class UrgencyLevel(str, Enum):
    CRITICAL = "critical"   # Action immédiate
    HIGH = "high"           # Aujourd'hui
    MEDIUM = "medium"       # Cette semaine
    LOW = "low"             # Quand possible
    NONE = "none"           # Pas urgent
```

---

### 1.4 Entity (Dataclass)

```python
@dataclass
class Entity:
    type: str          # person, organization, date, location, topic, project, amount, url, phone
    value: str         # Valeur extraite
    confidence: float  # 0.0-1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __eq__(self, other):
        """Égalité basée sur type + value uniquement"""
        return self.type == other.type and self.value == other.value

    def __hash__(self):
        """Hashable pour utilisation en set"""
        return hash((self.type, self.value))
```

**Metadata par type** :

| Type | Metadata |
|------|----------|
| `person` | `{"email": "...", "role": "sender\|recipient\|mentioned"}` |
| `date` | `{"parsed": datetime, "type": "deadline\|event\|mention"}` |
| `amount` | `{"value": 1500.0, "currency": "EUR"}` |
| `project` | `{"note_id": "...", "match_score": 0.95}` |

---

### 1.5 PerceivedEvent (Dataclass - FROZEN)

**Concept clé** : Représentation universelle et **immuable** de tout événement.

```python
@dataclass(frozen=True)
class PerceivedEvent:
    # Identité
    event_id: str                          # UUID unique
    source: EventSource                    # D'où vient l'événement
    source_id: str                         # ID dans le système source

    # Timing (tous timezone-aware)
    occurred_at: datetime                  # Quand l'événement s'est produit
    received_at: datetime                  # Quand on l'a reçu
    perceived_at: datetime = field(default_factory=now_utc)  # Traitement

    # Contenu
    title: str                             # Sujet/résumé
    content: str                           # Corps complet
    summary: Optional[str] = None          # Résumé IA pour contenu long

    # Classification
    event_type: EventType
    urgency: UrgencyLevel

    # Entités extraites
    entities: list[Entity]
    topics: list[str]
    keywords: list[str]

    # Participants
    from_person: str
    to_people: list[str]
    cc_people: list[str]

    # Contexte conversation
    thread_id: Optional[str] = None
    references: list[str] = field(default_factory=list)
    in_reply_to: Optional[str] = None

    # Pièces jointes
    has_attachments: bool
    attachment_count: int
    attachment_types: list[str]
    urls: list[str] = field(default_factory=list)

    # Qualité
    perception_confidence: float           # 0.0-1.0
    needs_clarification: bool
    clarification_questions: list[str]

    # Extensibilité
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Validations (`__post_init__`)** :

| Règle | Description |
|-------|-------------|
| Timezone-aware | Tous les datetimes doivent avoir tzinfo |
| Strings non vides | title, event_id, source_id |
| Confiance 0-1 | `0.0 <= perception_confidence <= 1.0` |
| Ordre temporel | `occurred_at <= received_at <= perceived_at` |
| Pas dans le futur | `occurred_at <= now + 1 seconde` |
| Cohérence attachments | Si `has_attachments`, alors `attachment_count > 0` |
| Count = len | `attachment_count == len(attachment_types)` |

**Méthodes** :

```python
def get_entities_by_type(self, entity_type: str) -> list[Entity]:
    """Filtre les entités par type"""

def has_entity(self, entity_type: str, value: str) -> bool:
    """Vérifie si une entité spécifique existe"""

def is_part_of_thread(self) -> bool:
    """True si thread_id ou in_reply_to défini"""

def is_urgent(self) -> bool:
    """True si CRITICAL ou HIGH"""

def to_dict(self) -> dict[str, Any]:
    """Sérialisation pour JSON/API"""
```

**Design** :

- **Frozen** : Empêche modification accidentelle pendant traitement concurrent
- **Source-agnostic** : Même structure pour email, Teams, calendar, etc.
- **Rich context** : Capture toutes les informations pertinentes
- **Extensible** : `metadata` pour données source-spécifiques
- **Traçable** : Provenance complète

---

## 2. Mémoire de Travail

### 2.1 MemoryState (Enum)

```python
class MemoryState(str, Enum):
    INITIALIZED = "initialized"   # Juste créé
    PERCEIVING = "perceiving"     # Traitement perception
    REASONING = "reasoning"       # Boucle raisonnement
    PLANNING = "planning"         # Génération plan
    EXECUTING = "executing"       # Exécution actions
    COMPLETE = "complete"         # Traitement terminé
    ARCHIVED = "archived"         # Archivé mémoire long terme
```

---

### 2.2 Hypothesis (Dataclass)

```python
@dataclass
class Hypothesis:
    id: str
    description: str           # "User should approve this request"
    confidence: float          # 0.0-1.0
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_evidence(self, evidence: str, supporting: bool = True):
        if supporting:
            self.supporting_evidence.append(evidence)
        else:
            self.contradicting_evidence.append(evidence)
        self.updated_at = now_utc()

    def update_confidence(self, new_confidence: float):
        self.confidence = new_confidence
        self.updated_at = now_utc()
```

---

### 2.3 ReasoningPass (Dataclass)

```python
@dataclass
class ReasoningPass:
    pass_number: int                        # 1, 2, 3, 4, 5
    pass_type: str                          # initial_analysis, context_enrichment, etc.
    started_at: datetime = field(default_factory=now_utc)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # État d'entrée
    input_confidence: float = 0.0
    input_hypotheses_count: int = 0

    # Actions effectuées
    context_queries: list[str] = field(default_factory=list)
    context_retrieved: list[str] = field(default_factory=list)
    ai_prompts: list[str] = field(default_factory=list)
    ai_responses: list[str] = field(default_factory=list)

    # État de sortie
    output_confidence: float = 0.0
    output_hypotheses_count: int = 0
    confidence_delta: float = 0.0

    # Insights
    insights: list[str] = field(default_factory=list)
    questions_raised: list[str] = field(default_factory=list)
    entities_extracted: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def complete(self):
        self.completed_at = now_utc()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
```

---

### 2.4 ContextItem (Dataclass)

```python
@dataclass
class ContextItem:
    source: str              # "pkm", "memory", "web", "conversation"
    type: str                # "note", "entity", "relationship", "thread"
    content: str             # Contenu réel
    relevance_score: float   # 0.0-1.0
    retrieved_at: datetime = field(default_factory=now_utc)
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

### 2.5 WorkingMemory (Classe)

**Concept** : Hub central pour tout l'état cognitif pendant le traitement d'un événement.

```python
class WorkingMemory:
    def __init__(self, event: PerceivedEvent):
        # Core
        self.event = event
        self.state = MemoryState.INITIALIZED
        self.created_at = now_utc()
        self.updated_at = now_utc()

        # Hypothèses
        self.hypotheses: dict[str, Hypothesis] = {}
        self.current_best_hypothesis: Optional[Hypothesis] = None
        self.overall_confidence: float = event.perception_confidence

        # Historique raisonnement
        self.reasoning_passes: list[ReasoningPass] = []
        self.current_pass: Optional[ReasoningPass] = None

        # Contexte récupéré
        self.context_items: list[ContextItem] = []
        self.related_events: list[str] = []

        # Questions ouvertes
        self.open_questions: list[str] = []
        self.uncertainties: list[str] = []

        # Continuité
        self.is_continuous: bool = False
        self.conversation_id: Optional[str] = None
        self.previous_events: list[PerceivedEvent] = []

        self.metadata: dict[str, Any] = {}
```

**Méthodes principales** :

```python
# Gestion des hypothèses
def add_hypothesis(self, hypothesis: Hypothesis, replace: bool = False):
    """Ajoute ou remplace une hypothèse"""

def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
    """Récupère une hypothèse par ID"""

def get_top_hypotheses(self, n: int = 3) -> list[Hypothesis]:
    """Top N hypothèses par confiance"""

# Gestion des passes
def start_reasoning_pass(self, pass_number: int, pass_type: str) -> ReasoningPass:
    """Démarre une nouvelle passe de raisonnement"""

def complete_reasoning_pass(self):
    """Termine la passe courante"""

# Gestion du contexte
def add_context(self, context: ContextItem):
    """Ajoute un item de contexte"""

def add_context_simple(self, source: str, type: str, content: str, relevance: float = 1.0):
    """Shortcut pour ajout simple"""

def get_context_by_source(self, source: str) -> list[ContextItem]:
    """Filtre par source"""

def get_top_context(self, n: int = 5) -> list[ContextItem]:
    """Top N par pertinence"""

# État
def add_question(self, question: str):
    """Ajoute une question ouverte"""

def add_uncertainty(self, uncertainty: str):
    """Ajoute une incertitude"""

def update_confidence(self, new_confidence: float):
    """Met à jour la confiance globale"""

def is_confident(self, threshold: float = 0.95) -> bool:
    """Vérifie si confiance >= seuil"""

def needs_more_reasoning(self, threshold: float = 0.95, max_passes: int = 5) -> bool:
    """Vérifie si plus de raisonnement nécessaire"""

# Continuité
def set_continuous(self, conversation_id: str, previous_events: list[PerceivedEvent]):
    """Marque comme conversation continue"""

# Introspection
def get_reasoning_summary(self) -> dict[str, Any]:
    """Retourne un résumé des passes"""

def to_dict(self) -> dict[str, Any]:
    """Sérialisation complète"""
```

**Validations** :
- Transitions d'état respectées (pas de start_pass sur COMPLETE)
- Une seule passe active à la fois
- IDs hypothèses uniques (sauf replace=True)

**Design** :
- **Non thread-safe** par design (un événement à la fois)
- **Transitoire** (effacé après traitement)
- **Hub central** (tous les composants lisent/écrivent ici)
- **Explicable** (trace complète du raisonnement)

---

## 3. Configuration

### 3.1 EmailAccountConfig

```python
class EmailAccountConfig(BaseModel):
    account_id: str                    # "personal", "work"
    account_name: str                  # Nom affiché
    imap_host: str                     # imap.gmail.com
    imap_port: int = 993
    imap_username: EmailStr            # Validé
    imap_password: str                 # Min 8 chars
    imap_timeout: int = 30             # 5-300s
    imap_read_timeout: int = 30        # 10-600s
    inbox_folder: str = "INBOX"
    archive_folder: str = "Archive"
    reference_folder: str = "Référence"
    delete_folder: str = "_Scapin/À supprimer"
    max_workers: int = 2               # 1-50
    batch_size: int = 50               # 1-1000
    enabled: bool = True
```

**Validateurs** :
- `password_not_empty` : Rejette placeholders, min 8 chars
- `username_valid` : Format email valide
- `account_id_valid` : Alphanumérique + `_-`
- `port_valid` : 1-65535, warning si non-standard

---

### 3.2 EmailConfig

```python
class EmailConfig(BaseModel):
    accounts: list[EmailAccountConfig] = []
    default_account_id: Optional[str] = None

    # Legacy (auto-migré si accounts vide)
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None
    ...
```

**Méthodes** :
- `get_account(account_id)` : Récupère par ID
- `get_enabled_accounts()` : Filtre les actifs
- `get_default_account()` : Défaut ou premier actif

---

### 3.3 AIConfig

```python
class AIConfig(BaseModel):
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    confidence_threshold: float = 0.85
    rate_limit_per_minute: int = 50
```

---

### 3.4 ProcessingConfig

```python
class ProcessingConfig(BaseModel):
    # Pipeline cognitif
    enable_cognitive_reasoning: bool = True
    cognitive_confidence_threshold: float = 0.85
    cognitive_timeout_seconds: int = 20
    cognitive_max_passes: int = 5
    fallback_on_failure: bool = True

    # Enrichissement contexte (Pass 2)
    enable_context_enrichment: bool = True
    context_top_k: int = 5
    context_min_relevance: float = 0.3

    # Traitement background
    auto_execute_threshold: float = 0.85
    batch_size: int = 20
    max_queue_size: int = 30
    polling_interval_seconds: int = 300
```

---

### 3.5 MicrosoftAccountConfig

```python
class MicrosoftAccountConfig(BaseModel):
    client_id: str
    tenant_id: str
    client_secret: Optional[str] = None
    scopes: list[str] = [
        "User.Read",
        "Chat.Read",
        "Chat.ReadWrite",
        "Calendars.ReadWrite",
        "Presence.Read"
    ]
```

---

### 3.6 AuthConfig

```python
class AuthConfig(BaseModel):
    enabled: bool = True
    jwt_secret_key: str                # Min 32 chars
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080    # 7 jours
    pin_hash: Optional[str] = None     # bcrypt hash
```

---

### 3.7 ScapinConfig (Root)

```python
class ScapinConfig(BaseSettings):
    email: EmailConfig = EmailConfig()
    ai: AIConfig = AIConfig()
    storage: StorageConfig = StorageConfig()
    processing: ProcessingConfig = ProcessingConfig()
    teams: TeamsConfig = TeamsConfig()
    calendar: CalendarConfig = CalendarConfig()
    briefing: BriefingConfig = BriefingConfig()
    auth: AuthConfig = AuthConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    integrations: IntegrationsConfig = IntegrationsConfig()

    model_config = SettingsConfigDict(
        env_nested_delimiter="__"
    )
```

**Chargement** :
1. `config/defaults.yaml`
2. Variables d'environnement (`EMAIL__ACCOUNTS__0__IMAP_HOST`)
3. Overrides programmatiques

---

### 3.8 ConfigManager (Singleton)

```python
class ConfigManager:
    _instance: Optional[ScapinConfig] = None
    _lock = threading.Lock()

    @classmethod
    def load(cls, config_path=None, env_file=None) -> ScapinConfig:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ScapinConfig(...)
        return cls._instance

    @classmethod
    def reload(cls) -> ScapinConfig:
        with cls._lock:
            cls._instance = None
        return cls.load()

    @classmethod
    def get(cls) -> ScapinConfig:
        if cls._instance is None:
            return cls.load()
        return cls._instance
```

---

## 4. Event Bus

### 4.1 ProcessingEventType (Enum)

```python
class ProcessingEventType(str, Enum):
    # Processing-level
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"

    # Account-level
    ACCOUNT_STARTED = "account_started"
    ACCOUNT_COMPLETED = "account_completed"
    ACCOUNT_ERROR = "account_error"

    # Email-level
    EMAIL_STARTED = "email_started"
    EMAIL_ANALYZING = "email_analyzing"
    EMAIL_COMPLETED = "email_completed"
    EMAIL_QUEUED = "email_queued"
    EMAIL_EXECUTED = "email_executed"
    EMAIL_ERROR = "email_error"

    # Batch
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"
    BATCH_PROGRESS = "batch_progress"

    # System
    SYSTEM_READY = "system_ready"
    SYSTEM_ERROR = "system_error"
```

---

### 4.2 ProcessingEvent (Dataclass)

```python
@dataclass
class ProcessingEvent:
    event_type: ProcessingEventType
    timestamp: datetime = field(default_factory=now_utc)

    # Contexte compte
    account_id: Optional[str] = None
    account_name: Optional[str] = None

    # Contexte email
    email_id: Optional[int] = None
    subject: Optional[str] = None
    from_address: Optional[str] = None
    email_date: Optional[datetime] = None
    preview: Optional[str] = None      # Max 80 chars

    # Résultats analyse
    action: Optional[str] = None
    confidence: Optional[int] = None   # 0-100
    category: Optional[str] = None
    reasoning: Optional[str] = None

    # Progression
    current: Optional[int] = None
    total: Optional[int] = None

    # Erreurs
    error: Optional[str] = None
    error_type: Optional[str] = None

    metadata: dict[str, Any] = field(default_factory=dict)
```

---

### 4.3 EventBus (Singleton)

```python
class EventBus:
    def __init__(self):
        self._subscribers: dict[ProcessingEventType, list[Callable]] = {}
        self._lock = threading.Lock()
        self._event_count = 0
        self._max_events = 10000

    def subscribe(self, event_type: ProcessingEventType, callback: Callable):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: ProcessingEventType, callback: Callable):
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(callback)

    def emit(self, event: ProcessingEvent):
        with self._lock:
            self._event_count += 1
            if self._event_count > self._max_events:
                logger.warning("High event count, consider clearing")

        # Callbacks exécutés hors lock
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

    def clear(self):
        with self._lock:
            self._subscribers.clear()
            self._event_count = 0
```

**Fonctions globales** :
```python
def get_event_bus() -> EventBus:
    """Singleton thread-safe"""

def reset_event_bus():
    """Pour tests"""
```

---

## 5. Exceptions

```python
class ScapinError(Exception):
    """Base pour toutes les exceptions"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}

class EmailProcessingError(ScapinError): pass
class AIAnalysisError(ScapinError): pass
class ValidationError(ScapinError): pass
class RateLimitError(ScapinError): pass
class AuthenticationError(ScapinError): pass
class ConfigurationError(ScapinError): pass
class DatabaseError(ScapinError): pass
class IMAPError(ScapinError): pass
class NetworkError(ScapinError): pass
class SerializationError(ScapinError): pass
```

---

## 6. Interfaces

**Fichier** : `src/core/interfaces.py` (~653 lignes)

```python
class IEmailClient(ABC):
    @abstractmethod
    def connect(self): ...
    @abstractmethod
    def disconnect(self): ...
    @abstractmethod
    def list_folders(self) -> list[str]: ...
    @abstractmethod
    def fetch_metadata(self, message_ids: list[int]) -> list[EmailMetadata]: ...
    @abstractmethod
    def fetch_content(self, message_id: int) -> EmailContent: ...
    @abstractmethod
    def move_email(self, message_id: int, destination: str) -> int: ...
    @abstractmethod
    def add_flags(self, message_ids: list[int], flags: list[str]): ...
    @abstractmethod
    def health_check(self) -> HealthCheck: ...

class IAIRouter(ABC):
    @abstractmethod
    def analyze_email(self, metadata, content, context) -> EmailAnalysis: ...
    @abstractmethod
    def extract_knowledge(self, email) -> Optional[KnowledgeEntry]: ...
    @abstractmethod
    def health_check(self) -> HealthCheck: ...

class IStorage(ABC): ...
class IKnowledgeBase(ABC): ...
class IReviewSystem(ABC): ...
class IEmailProcessor(ABC): ...
```

---

## 7. Constantes

**Fichier** : `src/core/constants.py`

```python
# Processing
DEFAULT_PROCESSING_LIMIT = 20
MAX_EMAIL_CONTENT_SIZE = 200_000
MAX_CONTENT_CHARS = 10_000

# Rate Limiting
MAX_BACKOFF_SECONDS = 60
DEFAULT_API_RATE_LIMIT = 50

# Calendar
CALENDAR_URGENCY_URGENT_HOURS = 2
CALENDAR_URGENCY_HIGH_HOURS = 6
CONFLICT_MIN_TRAVEL_GAP_MINUTES = 30

# Notes & Review
MAX_DAILY_REVIEWS = 50
AUTO_APPLY_CONFIDENCE_THRESHOLD = 0.90

# Journal
MAX_LOW_CONFIDENCE_QUESTIONS = 5
MAX_PATTERN_QUESTIONS = 5

# WebSocket
WS_PING_INTERVAL_MS = 30_000
WS_RECONNECT_DELAY_MS = 3_000
```

---

## 8. Patterns d'Erreur

**Fichier** : `src/core/error_handling.py`

```python
@dataclass
class ErrorResult:
    success: bool
    error: Optional[str] = None
    exception: Optional[Exception] = None

@contextmanager
def safe_operation(operation_name: str, logger):
    """Context manager pour logging automatique"""
    try:
        yield
    except Exception as e:
        logger.error(f"{operation_name} failed: {e}")

def with_error_handling(operation_name: str, default=None):
    """Decorator pour gestion d'erreur uniforme"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{operation_name}: {e}")
                return default
        return wrapper
    return decorator
```

---

## Résumé

Le module Core fournit :

1. **PerceivedEvent** : Représentation universelle immuable des événements
2. **WorkingMemory** : État cognitif transitoire avec trace de raisonnement
3. **Configuration** : Pydantic + .env avec validation stricte
4. **EventBus** : Pub/sub thread-safe pour découplage
5. **Interfaces** : Contrats pour injection de dépendances
6. **Exceptions** : Hiérarchie pour gestion d'erreur précise

---

*Voir aussi* : [02-valets.md](02-valets.md) pour l'utilisation de ces fondations.
