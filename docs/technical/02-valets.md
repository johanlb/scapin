# 02 - Les 7 Valets : Modules Cognitifs

**Modules** : `src/trivelin/`, `src/sancho/`, `src/passepartout/`, `src/planchet/`, `src/figaro/`, `src/sganarelle/`, `src/jeeves/`
**Lignes de code** : ~15,000
**Rôle** : Implémentation de l'architecture cognitive

---

## Vue d'Ensemble

Les 7 valets forment le cœur cognitif de SCAPIN, chacun avec une responsabilité distincte :

| Valet | Module | Responsabilité |
|-------|--------|----------------|
| **Trivelin** | `src/trivelin/` | Perception & triage des événements |
| **Sancho** | `src/sancho/` | Raisonnement IA multi-pass |
| **Passepartout** | `src/passepartout/` | Base de connaissances & contexte |
| **Planchet** | `src/planchet/` | Planification & évaluation risques |
| **Figaro** | `src/figaro/` | Orchestration DAG & exécution |
| **Sganarelle** | `src/sganarelle/` | Apprentissage continu |
| **Jeeves** | `src/jeeves/` | Interface CLI & API |

---

## 1. TRIVELIN - Perception & Triage

### Responsabilité

Normalise tous les types d'entrées (emails, Teams, Calendar) en représentation universelle (`PerceivedEvent`).

### Structure

```
src/trivelin/
├── processor.py          # EmailProcessor (~1,261 lignes)
├── cognitive_pipeline.py # Orchestrateur multi-pass (~497 lignes)
├── teams_processor.py    # TeamsProcessor (~419 lignes)
├── calendar_processor.py # CalendarProcessor (~467 lignes)
├── omnifocus_processor.py# OmniFocusProcessor (~317 lignes)
└── action_factory.py     # Factory actions (~160 lignes)
```

### EmailProcessor

```python
class EmailProcessor:
    def __init__(self):
        self.config = get_config()
        self.state = get_state_manager()
        self.imap_client = IMAPClient()
        self.ai_router = get_ai_router()
        self.event_bus = get_event_bus()
        self.error_manager = get_error_manager()
        self.queue_storage = get_queue_storage()
        self.note_manager = NoteManager()
        self.cognitive_pipeline = CognitivePipeline()

    def process_inbox(
        self,
        limit: int = 20,
        preview_mode: bool = False,
        auto_execute: bool = False
    ) -> ProcessingResult:
        """Traite un batch d'emails"""
        # 1. Fetch emails non traités (batch de 20)
        # 2. Pour chaque email:
        #    a. Normaliser en PerceivedEvent
        #    b. Passer au CognitivePipeline
        #    c. Exécuter ou queuer selon confiance
        # 3. Émettre ProcessingEvent sur EventBus
```

### CognitivePipeline

```python
@dataclass
class CognitivePipelineResult:
    perceived_event: PerceivedEvent
    reasoning_result: ReasoningResult    # De Sancho
    action_plan: ActionPlan              # De Planchet
    execution_result: ExecutionResult    # De Figaro
    learning_result: LearningResult      # De Sganarelle
    total_duration_seconds: float
    error: Optional[str] = None

class CognitivePipeline:
    def __init__(
        self,
        ai_router: AIRouter,
        template_manager: TemplateManager,
        planning_engine: PlanningEngine,
        action_orchestrator: ActionOrchestrator,
        learning_engine: LearningEngine,
        context_engine: Optional[ContextEngine] = None,
        cross_source_engine: Optional[CrossSourceEngine] = None,
        timeout_seconds: int = 60
    ): ...

    async def process_event(
        self,
        perceived_event: PerceivedEvent
    ) -> CognitivePipelineResult:
        """Pipeline complet : Sancho → Planchet → Figaro → Sganarelle"""
```

### Interactions

```
Email/Teams/Calendar → Trivelin.normalize()
                           │
                           ▼
                    PerceivedEvent
                           │
                           ▼
              CognitivePipeline.process_event()
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
         Sancho        Planchet       Figaro
      (reasoning)    (planning)    (execution)
                           │
                           ▼
                      Sganarelle
                     (learning)
```

---

## 2. SANCHO - Raisonnement Multi-Pass (v2.2)

### Responsabilité

Analyse les événements via architecture multi-pass avec escalade intelligente Haiku → Sonnet → Opus.

> **Spec complète** : [docs/specs/MULTI_PASS_SPEC.md](../specs/MULTI_PASS_SPEC.md)

### Structure

```
src/sancho/
├── convergence.py            # Logique convergence + escalade (~420 lignes) ✅ Sprint 7
├── context_searcher.py       # Wrapper recherche contexte (~640 lignes) ✅ Sprint 7
├── multi_pass_analyzer.py    # MultiPassAnalyzer v2.2 (TODO Sprint 7)
├── router.py                 # AIRouter + JSON repair (~500 lignes)
├── analyzer.py               # EventAnalyzer v2.1 (~476 lignes)
├── model_selector.py         # Sélection modèle (~200 lignes)
├── templates.py              # TemplateManager Jinja2 (~300 lignes)
├── template_renderer.py      # Rendu templates v2.2 (~235 lignes) ✅ Sprint 7
└── providers/
    ├── base.py               # Interface abstraite
    └── anthropic_provider.py # Provider Claude
```

### Convergence (convergence.py) — Sprint 7

Module de logique de convergence et d'escalade pour l'analyse multi-pass.

```python
@dataclass
class DecomposedConfidence:
    """Confiance décomposée par dimension"""
    entity_confidence: float       # Personnes/projets identifiés ?
    action_confidence: float       # Action suggérée correcte ?
    extraction_confidence: float   # Faits capturés ?
    completeness: float            # Rien d'oublié ?

    @property
    def overall(self) -> float:
        return min(self.entity_confidence, self.action_confidence,
                   self.extraction_confidence, self.completeness)

@dataclass
class PassResult:
    """Résultat d'une passe d'analyse"""
    pass_number: int
    pass_type: PassType
    model_used: str
    extractions: list[Extraction]
    action: str
    confidence: DecomposedConfidence
    entities_discovered: set[str]
    changes_made: list[str]

def should_stop(current: PassResult, previous: PassResult | None, config: MultiPassConfig) -> tuple[bool, str]:
    """Détermine si on doit arrêter les passes"""
    # Critères: confiance ≥ 95%, pas de changements, max passes, action simple

def select_model(pass_number: int, confidence: float, context: AnalysisContext, config: MultiPassConfig) -> tuple[ModelTier, str]:
    """Sélectionne le modèle pour la passe suivante"""
    # Pass 1-3: Haiku, Pass 4: Sonnet si conf < 80%, Pass 5: Opus si conf < 75%

def is_high_stakes(extractions: list[Extraction], context: AnalysisContext, config: MultiPassConfig) -> bool:
    """Détecte les décisions critiques nécessitant Opus"""
    # Montant > 10k€, deadline < 48h, VIP sender
```

**Messages UI** (voir UI_VOCABULARY.md) :
- Pass 1: "Sancho jette un coup d'œil au contenu..."
- Pass 2: "Sancho investigue..."
- Pass 3: "Sancho enquête de manière approfondie..."
- Pass 4: "Sancho consulte ses sources..."
- Pass 5: "Sancho délibère sur cette affaire..."

### ContextSearcher (context_searcher.py) — Sprint 7

Wrapper qui coordonne les recherches entre NoteManager et CrossSourceEngine pour construire un contexte structuré.

```python
@dataclass
class StructuredContext:
    """Contexte structuré pour injection dans les prompts"""
    query_entities: list[str]           # Entités recherchées
    search_timestamp: datetime
    sources_searched: list[str]         # ["notes", "calendar", "email"]

    notes: list[NoteContextBlock]       # Notes PKM pertinentes
    calendar: list[CalendarContextBlock] # Événements liés
    tasks: list[TaskContextBlock]       # Tâches OmniFocus
    emails: list[EmailContextBlock]     # Historique email

    entity_profiles: dict[str, EntityProfile]  # Profils consolidés
    conflicts: list[ConflictBlock]             # Conflits détectés

    def to_prompt_format(self) -> str:
        """Génère le contexte formaté pour le prompt"""

@dataclass
class EntityProfile:
    """Profil consolidé d'une entité depuis plusieurs sources"""
    name: str
    canonical_name: str    # Nom dans les notes PKM
    entity_type: str       # personne, projet, entreprise
    role: str | None       # "Tech Lead", "Client"
    key_facts: list[str]   # 3-5 faits importants
    related_entities: list[str]

class ContextSearcher:
    def __init__(self, note_manager: NoteManager, cross_source_engine: CrossSourceEngine): ...

    async def search_for_entities(
        self,
        entities: list[str],
        config: ContextSearchConfig,
        sender_email: str | None = None
    ) -> StructuredContext:
        # 1. Recherche notes par nom d'entité
        # 2. Recherche cross-source (calendar, tasks, email)
        # 3. Construction des profils d'entités
        # 4. Détection des conflits
```

### TemplateRenderer (template_renderer.py) — Sprint 7

Rendu des templates Jinja2 pour les prompts multi-pass. Gère les templates dans `templates/ai/v2/`.

```python
class TemplateRenderer:
    """Rendu des templates Jinja2 pour prompts multi-pass"""

    def __init__(
        self,
        template_dir: Path | None = None,  # Défaut: templates/ai/v2/
        auto_reload: bool = True,          # Hot reload dev
    ):
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            auto_reload=auto_reload,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Filtres personnalisés
        self._env.filters["truncate_smart"] = self._truncate_smart
        self._env.filters["format_date"] = self._format_date
        self._env.filters["format_confidence"] = self._format_confidence

    def render(self, template_name: str, **context: Any) -> str:
        """Rend un template avec contexte"""

    def render_pass1(self, event: Any, max_content_chars: int = 8000) -> str:
        """Template Pass 1 (Extraction aveugle)"""

    def render_pass2(
        self,
        event: Any,
        previous_result: dict,
        context: Any,                 # StructuredContext
        max_content_chars: int = 8000,
        max_context_notes: int = 5,
    ) -> str:
        """Template Pass 2+ (Raffinement contextuel)"""

    def render_pass4(
        self,
        event: Any,
        passes: list[dict],           # Historique des passes
        full_context: Any,            # StructuredContext complet
        unresolved_issues: list[str],
    ) -> str:
        """Template Pass 4-5 (Raisonnement profond)"""

def get_template_renderer() -> TemplateRenderer:
    """Instance singleton"""
```

**Templates** (`templates/ai/v2/`):
- `pass1_blind_extraction.j2` — Extraction aveugle sans contexte
- `pass2_contextual_refinement.j2` — Raffinement avec StructuredContext
- `pass4_deep_reasoning.j2` — Raisonnement Sonnet/Opus

**Filtres Jinja2 personnalisés** :
- `truncate_smart` — Tronque au mot (pas au milieu)
- `format_date` — Formatage date ISO → "12 janvier 2026"
- `format_confidence` — 0.85 → "85%"

### Architecture Multi-Pass v2.2

**Innovation** : Extraction → Contexte → Raffinement (flux inversé vs v2.1)

| Pass | Modèle | Confiance | Description |
|------|--------|-----------|-------------|
| 1 | **Haiku** | 60-80% | Extraction AVEUGLE (sans contexte) |
| 2-3 | **Haiku** | 80-95% | Raffinement avec contexte entités |
| 4 | **Sonnet** | 85-95% | Escalade si conf < 80% |
| 5 | **Opus** | 90-99% | Escalade si conf < 75% OU high-stakes |

**Critères de convergence** :
- Confiance ≥ 95%
- 0 changements entre passes
- Maximum 5 passes atteint

**High-Stakes Detection** (escalade Opus automatique) :
- Montant financier > 10,000€
- Deadline < 48 heures
- Expéditeur VIP (CEO, partenaire clé)
- Implications légales/contractuelles

### AIRouter

```python
class AIRouter:
    def __init__(self, config: AIConfig):
        self.config = config
        self.rate_limiter = RateLimiter()
        self.request_history = deque(maxlen=1000)

    async def analyze_email(
        self,
        content: EmailContent,
        metadata: EmailMetadata,
        context: Optional[str] = None,
        model: AIModel = AIModel.STANDARD
    ) -> EmailAnalysis:
        """Route avec retry + JSON repair"""

    def _repair_json(self, json_str: str) -> str:
        """Stratégie multi-niveau"""
        # Level 1: Parse direct
        # Level 2: json-repair library
        # Level 3: Regex cleaning + json-repair
```

---

## 3. PASSEPARTOUT - Base de Connaissances

### Responsabilité

Gère les notes Markdown avec versioning Git, recherche sémantique, et enrichissement contexte.

### Structure

```
src/passepartout/
├── note_manager.py       # CRUD + cache LRU (~800 lignes)
├── context_engine.py     # Récupération contexte (~600 lignes)
├── vector_store.py       # Stockage vecteurs (~400 lignes)
├── embeddings.py         # Sentence-transformers (~350 lignes)
├── note_metadata.py      # SM-2 SQLite (~500 lignes)
├── note_types.py         # Classification (~250 lignes)
├── note_reviewer.py      # Analyse + suggestions (~700 lignes)
├── note_enricher.py      # Enrichissement auto (~350 lignes)
├── note_merger.py        # Fusion duplicatas (~300 lignes)
├── note_scheduler.py     # Planning révisions (~400 lignes)
├── git_versioning.py     # Git (~450 lignes)
├── background_worker.py  # Async tasks (~250 lignes)
└── cross_source/
    ├── engine.py         # Orchestrateur (~800 lignes)
    └── adapters/         # 6 adapters
        ├── email_adapter.py
        ├── calendar_adapter.py
        ├── teams_adapter.py
        ├── whatsapp_adapter.py
        ├── files_adapter.py
        └── web_adapter.py
```

### NoteManager

```python
@dataclass(slots=True)
class Note:
    note_id: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    tags: list[str]
    entities: list[Entity]
    metadata: dict
    file_path: Optional[Path]

class NoteManager:
    def __init__(
        self,
        notes_dir: Path,
        auto_index: bool = True,
        cache_size: int = 2000
    ):
        self.notes_dir = notes_dir
        self.vector_store = VectorStore()
        self.embedder = EmbeddingGenerator()
        self._cache = OrderedDict()  # LRU cache
        self._cache_lock = threading.Lock()
        self.git_manager = GitVersionManager(notes_dir)

    def create_note(
        self,
        title: str,
        content: str,
        tags: list[str] = None,
        metadata: dict = None
    ) -> Note:
        """Crée note avec YAML frontmatter + Git commit"""

    async def search_semantic(
        self,
        query: str,
        top_k: int = 5,
        min_relevance: float = 0.3
    ) -> list[Note]:
        """Recherche par embedding"""

    def get_all_notes(self, cached: bool = True) -> list[Note]:
        """Utilise cache mémoire pour performance"""
```

### ContextEngine

```python
@dataclass(slots=True)
class ContextRetrievalResult:
    context_items: list[ContextItem]
    total_retrieved: int
    sources_used: list[str]
    retrieval_duration_seconds: float

class ContextEngine:
    def __init__(
        self,
        note_manager: NoteManager,
        cross_source_engine: Optional[CrossSourceEngine] = None,
        top_k: int = 5,
        min_relevance: float = 0.3
    ): ...

    async def retrieve_context(
        self,
        perceived_event: PerceivedEvent,
        context_types: list[str] = None
    ) -> ContextRetrievalResult:
        """Récupère contexte : entités + sémantique + cross-source"""
```

### CrossSourceEngine

```python
class CrossSourceEngine:
    def __init__(self, config: CrossSourceConfig = None):
        self._adapters: dict[str, SourceAdapter] = {}
        self._cache = CrossSourceCache()
        self._health: dict[str, AdapterHealth] = {}

    def register_adapter(self, source: str, adapter: SourceAdapter):
        """Register: Email, Calendar, Teams, WhatsApp, Files, Web"""

    async def search(
        self,
        query: str,
        sources: Optional[list[str]] = None,
        limit: int = 10
    ) -> CrossSourceResult:
        """Recherche parallèle + aggregation + circuit breaker"""
```

### SM-2 Spaced Repetition

```python
@dataclass
class SM2Metadata:
    repetitions: int = 0
    ease_factor: float = 2.5
    interval_days: int = 1
    next_review_date: datetime
    last_review_date: Optional[datetime] = None

class NoteMetadataStore:
    def __init__(self, db_path: Path):
        self.connection = sqlite3.connect(db_path, check_same_thread=False)

    def get_due_for_review(self, limit: int = 20) -> list[str]:
        """Notes dues aujourd'hui"""

    def record_review(self, note_id: str, quality: int) -> SM2Metadata:
        """Update SM-2 après révision (quality 0-5)"""
```

---

## 4. PLANCHET - Planification

### Responsabilité

Convertit WorkingMemory en plan d'actions avec évaluation des risques.

### Structure

```
src/planchet/
└── planning_engine.py    # ~600 lignes
```

### PlanningEngine

```python
class RiskLevel(str, Enum):
    LOW = "low"           # Réversible, sans effet externe
    MEDIUM = "medium"     # Partiellement réversible
    HIGH = "high"         # Difficilement réversible
    CRITICAL = "critical" # Irréversible, effet majeur

@dataclass
class RiskAssessment:
    action_id: str
    risk_level: RiskLevel
    reversible: bool
    impact_score: float        # 0-1
    concerns: list[str]
    mitigations: list[str]

    def requires_approval(self) -> bool:
        return self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

@dataclass
class ActionPlan:
    actions: list[Action]       # Tri topologique
    execution_mode: ExecutionMode  # AUTO, REVIEW, MANUAL
    risks: list[RiskAssessment]
    rationale: str
    estimated_duration: float
    confidence: float

    def requires_approval(self) -> bool:
        return any(r.requires_approval() for r in self.risks)

class PlanningEngine:
    def generate_plan(
        self,
        working_memory: WorkingMemory,
        pattern_store: Optional[PatternStore] = None
    ) -> ActionPlan:
        """WorkingMemory → ActionPlan"""
        # 1. Extraire recommandations des hypothèses
        # 2. Valider dépendances
        # 3. Tri topologique (DAG)
        # 4. Évaluer risques
        # 5. Déterminer mode exécution
```

### Évaluation Risques

| Action | Risk | Réversible |
|--------|------|------------|
| Move email | LOW | Oui |
| Create task | LOW | Oui |
| Archive email | MEDIUM | Partiellement |
| Delete note | HIGH | Via Git |
| Send email | HIGH | Non |

---

## 5. FIGARO - Orchestration

### Responsabilité

Exécute les plans d'action avec résolution DAG, parallélisation, et rollback.

### Structure

```
src/figaro/
├── orchestrator.py       # DAG orchestrator (~500 lignes)
└── actions/
    ├── base.py           # Action ABC (~300 lignes)
    ├── email.py          # Email actions (~800 lignes)
    ├── teams.py          # Teams actions (~700 lignes)
    ├── calendar.py       # Calendar actions (~600 lignes)
    ├── notes.py          # Notes actions (~400 lignes)
    └── tasks.py          # Tasks actions (~400 lignes)
```

### Action (Abstract Base)

```python
class ExecutionMode(str, Enum):
    AUTO = "auto"         # Exécution immédiate
    REVIEW = "review"     # Queue pour review
    MANUAL = "manual"     # User execute

@dataclass
class ActionResult:
    success: bool
    duration: float
    output: Any = None
    error: Optional[Exception] = None
    executed_at: Optional[datetime] = None

class Action(ABC):
    @property
    @abstractmethod
    def action_id(self) -> str: ...

    @property
    @abstractmethod
    def action_type(self) -> str: ...

    @abstractmethod
    def validate(self) -> ValidationResult: ...

    @abstractmethod
    async def execute(self) -> ActionResult: ...

    @abstractmethod
    async def undo(self) -> ActionResult: ...

    def get_dependencies(self) -> list[str]:
        return []
```

### ActionOrchestrator

```python
@dataclass
class ExecutionResult:
    success: bool
    executed_actions: list[ActionResult]
    duration: float
    error: Optional[Exception] = None
    rolled_back: bool = False

class ActionOrchestrator:
    def __init__(
        self,
        parallel_execution: bool = False,
        fail_fast: bool = True
    ):
        self.parallel_execution = parallel_execution
        self.fail_fast = fail_fast
        self._executed_pairs: list[tuple[Action, ActionResult]] = []

    async def execute_plan(
        self,
        action_plan: ActionPlan
    ) -> ExecutionResult:
        """Exécute plan avec DAG + rollback"""
        # 1. Valider toutes les actions
        # 2. Build DAG dépendances
        # 3. Tri topologique
        # 4. Exécuter par niveaux
        # 5. Rollback si échec

    async def _rollback(self):
        """Rollback en ordre inverse"""
```

### Actions Concrètes

```python
# Email
class ArchiveEmailAction(Action): ...
class CreateDraftAction(Action): ...
class FlagEmailAction(Action): ...

# Teams
class ReplyTeamsMessageAction(Action): ...
class FlagTeamsMessageAction(Action): ...
class CreateTaskFromTeamsAction(Action): ...

# Calendar
class RespondCalendarAction(Action): ...
class CreateCalendarEventAction(Action): ...
class BlockTimeAction(Action): ...

# Notes
class CreateNoteAction(Action): ...
class UpdateNoteAction(Action): ...
class ArchiveNoteAction(Action): ...
```

---

## 6. SGANARELLE - Apprentissage

### Responsabilité

Ferme la boucle cognitive : feedback → patterns → calibration → knowledge update.

### Structure

```
src/sganarelle/
├── learning_engine.py       # Orchestrateur (~600 lignes)
├── feedback_processor.py    # Analyse feedback (~570 lignes)
├── knowledge_updater.py     # Enrichissement notes (~590 lignes)
├── pattern_store.py         # Patterns JSON (~560 lignes)
├── provider_tracker.py      # Quality tracking (~620 lignes)
├── confidence_calibrator.py # Calibration (~580 lignes)
├── types.py                 # Dataclasses (~380 lignes)
└── constants.py             # Tuning (~220 lignes)
```

### LearningEngine

```python
@dataclass
class LearningResult:
    knowledge_updates: list[KnowledgeUpdate]
    pattern_updates: list[Pattern]
    provider_scores: dict[str, ProviderScore]
    confidence_adjustments: dict[str, float]
    duration: float
    updates_applied: int
    updates_failed: int
    timestamp: datetime = field(default_factory=now_utc)

class LearningEngine:
    def __init__(self, note_manager: NoteManager, storage_path: Path):
        self.feedback_processor = FeedbackProcessor()
        self.knowledge_updater = KnowledgeUpdater(note_manager)
        self.pattern_store = PatternStore(storage_path / "patterns.json")
        self.provider_tracker = ProviderTracker(storage_path / "providers.json")
        self.confidence_calibrator = ConfidenceCalibrator()

    async def learn(
        self,
        perceived_event: PerceivedEvent,
        working_memory: WorkingMemory,
        action_plan: ActionPlan,
        execution_result: ExecutionResult,
        user_feedback: Optional[UserFeedback] = None
    ) -> LearningResult:
        """Apprentissage complet post-exécution"""
```

### FeedbackProcessor

```python
@dataclass
class UserFeedback:
    approval: bool
    rating: Optional[int] = None        # 1-5
    comment: Optional[str] = None
    correction: Optional[str] = None
    action_executed: bool = False
    time_to_action: float = 0.0
    modification: Optional[Action] = None

@dataclass
class FeedbackAnalysis:
    feedback: UserFeedback
    correctness_score: float            # 0-1
    suggested_improvements: list[str]
    confidence_error: float
    action_quality_score: float
    reasoning_quality_score: float

class FeedbackProcessor:
    def analyze_feedback(
        self,
        perceived_event: PerceivedEvent,
        reasoning_result: ReasoningResult,
        user_feedback: UserFeedback
    ) -> FeedbackAnalysis: ...
```

### PatternStore

```python
@dataclass
class Pattern:
    pattern_id: str
    pattern_type: PatternType       # ACTION_SEQUENCE, ENTITY_RELATIONSHIP, TIME_BASED
    conditions: dict[str, Any]
    suggested_actions: list[str]
    confidence: float
    success_rate: float
    occurrences: int
    last_seen: datetime

    def matches(self, event: PerceivedEvent, context: dict) -> bool: ...

class PatternStore:
    def __init__(self, storage_path: Path):
        self.patterns: dict[str, Pattern] = {}
        self._lock = threading.Lock()

    def get_applicable_patterns(
        self,
        perceived_event: PerceivedEvent,
        min_confidence: float = 0.7
    ) -> list[Pattern]: ...

    def record_execution(self, pattern_id: str, success: bool): ...
```

### ConfidenceCalibrator

```python
class ConfidenceCalibrator:
    def add_sample(self, predicted: float, actual_success: bool):
        """Ajoute échantillon de calibration"""
        # predicted=0.9, actual=True → bien calibré
        # predicted=0.9, actual=False → sur-confiant

    def get_calibrated_confidence(self, raw: float) -> float:
        """Ajuste confiance selon calibration"""
        # Si sur-confiant → réduire
        # Si sous-confiant → augmenter
```

---

## 7. JEEVES - Interface

### Responsabilité

Expose toutes les fonctionnalités via CLI (Typer) et API REST (FastAPI).

### Structure

```
src/jeeves/
├── cli.py                    # Typer commands (~600 lignes)
├── display_manager.py        # Rich rendering (~400 lignes)
├── menu.py                   # Interactive menus (~300 lignes)
├── review_mode.py            # Review interface (~350 lignes)
├── api/
│   ├── app.py                # FastAPI factory (~300 lignes)
│   ├── deps.py               # DI container (~250 lignes)
│   ├── auth/
│   │   ├── jwt_handler.py    # JWT (~300 lignes)
│   │   └── rate_limiter.py   # Login limiting (~200 lignes)
│   ├── routers/              # 13 routers
│   ├── services/             # 8 services
│   ├── models/               # Request/Response
│   └── websocket/            # Real-time
├── journal/
│   ├── models.py             # JournalEntry (~350 lignes)
│   ├── generator.py          # Generation (~500 lignes)
│   ├── interactive.py        # Q&A (~400 lignes)
│   ├── feedback.py           # Processing (~300 lignes)
│   ├── reviews.py            # Weekly/Monthly (~300 lignes)
│   └── providers/            # Teams, Calendar, OmniFocus
└── briefing/
    ├── models.py             # Briefing structures (~250 lignes)
    ├── generator.py          # Generation (~400 lignes)
    └── display.py            # CLI display (~300 lignes)
```

### CLI Commands

```python
app = typer.Typer(name="scapin")

@app.command()
def process(limit: int = 20, preview: bool = False, auto_execute: bool = False):
    """Traite l'inbox"""

@app.command()
def review(date: str = None, interactive: bool = True):
    """Révision notes SM-2"""

@app.command()
def journal(date: str = None, interactive: bool = True):
    """Journal quotidien"""

@app.command()
def briefing(morning: bool = False, meeting: str = None):
    """Briefing matinal ou pré-réunion"""

@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Démarrer API FastAPI"""
```

### API Routers

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| auth | `/api/auth` | login, check |
| system | `/api` | health, status, stats, config |
| briefing | `/api/briefing` | morning, meeting/{id} |
| email | `/api/email` | accounts, stats, process, analyze |
| queue | `/api/queue` | list, approve, reject, snooze, undo |
| notes | `/api/notes` | CRUD, search, reviews |
| calendar | `/api/calendar` | events, today, respond |
| teams | `/api/teams` | chats, messages, reply |
| journal | `/api/journal` | entries, answer, correct |
| discussions | `/api/discussions` | chat, quick-chat |
| search | `/api/search` | global |
| notifications | `/api/notifications` | list, read |
| valets | `/api/valets` | dashboard |

### WebSocket

```
WS /ws

Messages:
- auth: { type: "auth", token: "..." }
- subscribe: { type: "subscribe", channel: "events" }
- ping/pong: { type: "ping" } → { type: "pong" }

Channels:
- events: Processing events
- status: System status
- notifications: Real-time alerts
- discussions: Chat messages
```

---

## Matrice d'Interactions

```
         Trivelin  Sancho  Passepartout  Planchet  Figaro  Sganarelle  Jeeves
Trivelin    —       →→→        →           →→       →→        →         →
Sancho      ←        —        ←→           →                  ←
Passepartout←       ←→         —                              ←         →
Planchet             ←                      —        →         ←
Figaro      ←                                        —        →         →
Sganarelle           →         →            →        ←         —
Jeeves      →                  →                     →                   —

Légende:
→  Appelle/utilise
←  Est appelé par
←→ Bidirectionnel
```

---

## Flux de Données Complet

```
1. Email arrive (IMAP)
   └─→ Trivelin.EmailProcessor.process_inbox()

2. Normalisation
   └─→ PerceivedEvent (frozen, validated)

3. Pipeline Cognitif
   └─→ CognitivePipeline.process_event()
       │
       ├─→ Sancho.ReasoningEngine.reason()
       │   ├─→ Pass 1: analyse initiale
       │   ├─→ Pass 2: Passepartout.ContextEngine.retrieve()
       │   ├─→ Pass 3: raisonnement profond
       │   ├─→ Pass 4: Sganarelle.PatternStore.get_applicable()
       │   └─→ Pass 5: clarification (si nécessaire)
       │
       ├─→ Planchet.PlanningEngine.generate_plan()
       │   └─→ ActionPlan (DAG + risks)
       │
       ├─→ Figaro.ActionOrchestrator.execute_plan()
       │   └─→ ExecutionResult
       │
       └─→ Sganarelle.LearningEngine.learn()
           └─→ LearningResult

4. Interface
   └─→ Jeeves (CLI / API / WebSocket)
       └─→ User interaction
           └─→ Feedback
               └─→ Sganarelle (loop)
```

---

*Voir aussi* : [03-integrations.md](03-integrations.md) pour les intégrations externes.
