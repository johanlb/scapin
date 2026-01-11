# Flux de Données

**Version** : 1.0.0-RC
**Dernière mise à jour** : 11 janvier 2026

---

## Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Flux Email](#2-flux-email)
3. [Flux Teams](#3-flux-teams)
4. [Flux Calendar](#4-flux-calendar)
5. [Flux Notes](#5-flux-notes)
6. [Flux Journal](#6-flux-journal)
7. [Flux API REST](#7-flux-api-rest)
8. [Transformations de Données](#8-transformations-de-données)
9. [Points d'Extension](#9-points-dextension)

---

## 1. Vue d'Ensemble

### Architecture Cognitive

Tous les flux suivent le pattern **Trivelin → Sancho → Planchet → Figaro → Sganarelle** :

```
┌──────────────────────────────────────────────────────────────────┐
│  FLUX UNIVERSELS (Email, Teams, Calendar, Notes, Journal)        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Trivelin (Perception) ────→ Normalisation universelle       │
│                                 (PerceivedEvent)                │
│                                           ↓                     │
│  2. Sancho (Raisonnement) ──→ Multi-passes + Contexte           │
│                                 (ReasoningResult)               │
│                                           ↓                     │
│  3. Planchet (Planification) → DAG Actions + Risques            │
│                                 (ActionPlan)                    │
│                                           ↓                     │
│  4. Figaro (Exécution) ──────→ Orchestration rollback           │
│                                 (ExecutionResult)               │
│                                           ↓                     │
│  5. Sganarelle (Apprentissage) → Patterns + Calibration         │
│                                   (LearningResult)              │
│                                           ↓                     │
│  Jeeves (Interface) ────────→ API REST / CLI / WebSockets       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Flux Email

### 2.1 IMAP → PerceivedEvent

**Fichiers** :
- `src/integrations/email/imap_client.py`
- `src/integrations/email/processed_tracker.py`
- `src/trivelin/processor.py`
- `src/core/events/normalizers/email_normalizer.py`

```
IMAPClient.connect()
    ↓
IMAPClient.fetch_emails(limit=20)
    ├─ Batch 200 headers avec early-stop
    ├─ Filter: UNSEEN + !$MailFlagBit6
    ├─ ProcessedTracker check (SQLite)
    └─ Récupère: text + HTML + attachments
        ↓
EmailMetadata + EmailContent
        ↓
EmailNormalizer.normalize()
    ├─ Extrait entités: From, To, Subject, Dates
    ├─ Parse HTML → Plain text
    ├─ Détecte: Thread, Réponse, Forward
    └─ Scoring importance
        ↓
PerceivedEvent
```

**Optimisations** :
- Batch 200 avec early-stop : 1s vs 43s
- Connection IMAP réutilisée
- ProcessedTracker SQLite (iCloud compat)
- Dual flag : IMAP + SQLite

### 2.2 Cognitive Pipeline

**Fichiers** :
- `src/trivelin/cognitive_pipeline.py`
- `src/sancho/reasoning_engine.py`
- `src/planchet/planning_engine.py`
- `src/figaro/orchestrator.py`

```
CognitivePipeline.process(metadata, content)
│
├─ Stage 1: NORMALIZE (Trivelin) ~50ms
│  └─ EmailNormalizer.normalize() → PerceivedEvent
│
├─ Stage 2: REASON (Sancho) — Voir détails ci-dessous
│
├─ Stage 3: PLAN (Planchet) ~100ms
│  ├─ Construit DAG d'actions
│  ├─ Évalue risques
│  └─ ActionPlan {
│         actions: [archive, create_note, log],
│         requires_approval: false,
│         estimated_risk: 0.05
│     }
│
├─ Stage 4: EXECUTE (Figaro) ~200-500ms
│  ├─ Exécute en parallèle (où safe)
│  ├─ Rollback sur erreur
│  └─ ExecutionResult {
│         success: true,
│         executed_actions: [...],
│         failed_actions: []
│     }
│
└─ Stage 5: LEARN (Sganarelle) ~50ms
   └─ Mets à jour: patterns, calibration, confidence
```

### 2.2.1 Raisonnement Multi-Pass (Sancho) — Détail

Le moteur de raisonnement `ReasoningEngine` exécute une boucle itérative jusqu'à convergence de confiance :

```
while confidence < 95% AND passes < 5:
    execute_pass(pass_number)
```

#### Pass 1 : Analyse Initiale

| Aspect | Valeur |
|--------|--------|
| **Modèle** | Claude Haiku (rapide, économique) |
| **Objectif** | Comprendre rapidement l'événement |
| **Confiance cible** | 60-70% |
| **Durée** | 2-3 secondes |
| **Entrées** | PerceivedEvent + PatternStore (patterns appris) |

```
_pass1_initial_analysis(working_memory)
    ├─ PatternStore.find_matching_patterns(event)
    │  └─ Patterns avec confidence >= 0.5, max 5
    │
    ├─ TemplateManager.render("ai/pass1_initial")
    │  └─ Prompt avec event + learned_patterns
    │
    ├─ AIRouter.analyze_with_prompt(model=HAIKU)
    │
    └─ Hypothesis {
           id: "pass1_initial",
           confidence: 0.65,
           metadata: { analysis, model: "haiku" }
       }
```

#### Pass 2 : Enrichissement Contexte

| Aspect | Valeur |
|--------|--------|
| **Modèle** | Claude Sonnet (équilibré) |
| **Objectif** | Ré-analyser avec le contexte récupéré |
| **Confiance cible** | 75-85% |
| **Durée** | 3-5 secondes |
| **Condition** | `enable_context=true` dans config |

**Sources de contexte** :

```
┌─────────────────────────────────────────────────────────────────┐
│  ContextEngine (Notes Scapin)                                   │
│  ───────────────────────────────                                │
│  • Entity-based (40%) : Notes mentionnant mêmes entités        │
│    └─ NoteManager.get_notes_by_entity(entity, top_k=10)        │
│                                                                 │
│  • Semantic (40%) : Similarité vectorielle FAISS               │
│    └─ NoteManager.search_notes(query, top_k=10)                │
│    └─ Embeddings: sentence-transformers (all-MiniLM-L6-v2)     │
│                                                                 │
│  • Thread-based (20%) : Même fil de discussion                 │
│    └─ search_notes(f"thread:{thread_id}", top_k=5)             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CrossSourceEngine (Sources externes)                           │
│  ────────────────────────────────────                           │
│  • Calendar : Événements proches temporellement                 │
│  • Teams : Messages récents pertinents                          │
│  • Email : Historique d'échanges avec mêmes contacts           │
│  • WhatsApp : Conversations récentes (si configuré)            │
│  • Files : Fichiers locaux pertinents (ripgrep)                │
│  • Web : Recherche Tavily/DuckDuckGo (si configuré)            │
└─────────────────────────────────────────────────────────────────┘
```

**Flux** :

```
_pass2_context_enrichment(working_memory)
    │
    ├─ ContextEngine.retrieve_context_sync(event)
    │  ├─ _retrieve_by_entities() → 40% poids
    │  ├─ _retrieve_by_semantic() → 40% poids
    │  └─ _retrieve_by_thread()   → 20% poids
    │     ↓
    │  _rank_and_deduplicate(candidates, top_k=5, min_relevance=0.3)
    │
    ├─ CrossSourceEngine.search(query, max_results=5)
    │  └─ Convertit SourceItem → ContextItem
    │
    ├─ WorkingMemory.add_context_simple(source, type, content, relevance)
    │
    ├─ TemplateManager.render("ai/pass2_context")
    │  └─ Prompt avec event + pass1_hypothesis + context_items
    │
    └─ AIRouter.analyze_with_prompt(model=SONNET)
        ↓
    Hypothesis {
        id: "pass2_context",
        confidence: 0.80,
        metadata: { analysis, context_count }
    }
```

#### Pass 3 : Raisonnement Profond

| Aspect | Valeur |
|--------|--------|
| **Modèle** | Claude Sonnet |
| **Objectif** | Chain-of-thought, exploration alternatives, validation logique |
| **Confiance cible** | 85-92% |
| **Durée** | 2-4 secondes |

```
_pass3_deep_reasoning(working_memory)
    ├─ TemplateManager.render("ai/pass3_deep")
    │  └─ Prompt avec event + pass2_hypothesis + confiance actuelle
    │
    ├─ AIRouter.analyze_with_prompt(model=SONNET)
    │
    └─ Hypothesis {
           id: "pass3_deep",
           confidence: 0.88,
           supporting_evidence: [logic_chain]
       }
```

#### Pass 4 : Validation (STUB)

| Aspect | Valeur |
|--------|--------|
| **État** | Non implémenté (Phase 2.5) |
| **Objectif prévu** | Consensus multi-provider (Anthropic + OpenAI) |
| **Comportement actuel** | Pas d'augmentation artificielle de confiance |

#### Pass 5 : Clarification Utilisateur

| Aspect | Valeur |
|--------|--------|
| **Modèle** | Claude Sonnet |
| **Objectif** | Générer questions ciblées pour lever les incertitudes |
| **Confiance cible** | 95-99% |
| **Condition** | Exécuté uniquement si confiance < seuil après Pass 3/4 |

```
_pass5_user_clarification(working_memory)
    ├─ TemplateManager.render("ai/pass5_clarification")
    │
    ├─ AIRouter.analyze_with_prompt(model=SONNET)
    │
    └─ Questions ajoutées à WorkingMemory.open_questions
       └─ Présentées dans la queue de review
```

### 2.2.2 Configuration du Pipeline Cognitif

```python
# src/core/config_manager.py → ProcessingConfig
enable_cognitive_reasoning: bool = True
cognitive_max_passes: int = 5
cognitive_confidence_threshold: float = 0.95   # Seuil de convergence
cognitive_timeout_seconds: int = 30

# Contexte (Pass 2)
enable_context_enrichment: bool = True
context_top_k: int = 5                         # Nombre d'items contexte
context_min_relevance: float = 0.3             # Score minimum
```

### 2.2.3 Résultat du Raisonnement

```python
ReasoningResult {
    working_memory: WorkingMemory,        # État cognitif complet
    final_analysis: EmailAnalysis,        # Décision finale
    reasoning_trace: list[ReasoningPass], # Trace complète des passes
    confidence: float,                    # 0.0-1.0
    passes_executed: int,                 # Nombre de passes exécutées
    total_duration_seconds: float,
    converged: bool,                      # True si confidence >= seuil
    key_factors: list[str],
    uncertainties: list[str],
    questions_for_user: list[dict]
}
```

### 2.3 Auto-apply Proposals

```
EmailAnalysis.proposed_notes[]
    ↓
_auto_apply_proposals()
    ├─ Si confidence >= 0.90:
    │  ├─ Action="create": NoteManager.create_note()
    │  └─ Action="enrich": NoteManager.update_note()
    │
    └─ Si confidence < 0.90:
       └─ Reste dans UI pour review
```

### 2.4 Queueing

```
Si confidence < threshold OU auto_execute=false:
    ↓
QueueStorage.save_item()
    ├─ HTML body + Full text sauvegardés
    ├─ Flag email: IMAP + SQLite
    └─ Emit ProcessingEvent(EMAIL_QUEUED)
        ↓
    WebSocket → Frontend (UI live update)
```

### 2.5 Actions Exécutées

| Action | Implémentation |
|--------|----------------|
| **ARCHIVE** | `IMAP.move_email(to_folder)` |
| **DELETE** | `IMAP.move_email(trash)` |
| **TASK** | OmniFocus MCP |
| **QUEUE** | Queue storage automatique |

---

## 3. Flux Teams

### 3.1 Polling Teams

**Fichiers** :
- `src/integrations/microsoft/teams_client.py`
- `src/trivelin/teams_processor.py`
- `src/integrations/microsoft/teams_normalizer.py`

```
TeamsProcessor.poll_and_process()
    ↓
TeamsClient.get_recent_messages(limit_per_chat=20, since=_last_poll)
    ├─ GET /me/chats (Graph API)
    ├─ GET /me/chats/{chatId}/messages
    └─ Pagination: $skip/$top
        ↓
List[TeamsMessage]
    ↓
TeamsNormalizer.normalize()
    ├─ Extrait: sender, mentions, topic, attachments
    ├─ Parse Markdown → Plain text
    ├─ Détecte @mention utilisateur
    └─ Scoring urgence
        ↓
PerceivedEvent {
    event_type: "TEAMS_MESSAGE",
    source: "teams",
    importance_score: 0.65
}
```

### 3.2 Traitement

```
TeamsProcessor._process_message(message)
    ├─ Normalize → PerceivedEvent
    ├─ Check _is_processed(event_id)
    │
    └─ CognitivePipeline.reasoning_engine.reason(event)
        ↓
    ReasoningResult {
        action: "REPLY",
        suggested_response: "..."
    }
        ↓
    Si confidence >= seuil:
        ├─ PlanningEngine.plan()
        └─ TeamsClient.reply_to_message()
```

---

## 4. Flux Calendar

### 4.1 Fetch Calendrier

**Fichiers** :
- `src/integrations/microsoft/calendar_client.py`
- `src/trivelin/calendar_processor.py`
- `src/integrations/microsoft/calendar_normalizer.py`

```
CalendarProcessor.poll_and_process()
    ↓
CalendarClient.get_events(days_ahead=7, days_behind=1)
    ├─ GET /me/calendarview (Graph API)
    └─ Pagination
        ↓
List[CalendarEvent]
    ↓
CalendarNormalizer.normalize()
    ├─ Extrait: organizer, attendees, location, topic
    └─ Scoring importance
        ↓
PerceivedEvent {
    event_type: "CALENDAR_EVENT",
    source: "calendar"
}
```

### 4.2 Briefing Generation

**Note** : Le briefing bypass le cognitive pipeline.

```
BriefingService.generate_morning_briefing(hours_ahead=24)
    ├─ Récupère: Urgent items, Calendar events, Pending emails, Teams unread
    ├─ Trie par: Priority + Time
    ├─ Détecte: Conflits horaires
    │
    └─ BriefingResponse {
           urgent_items: [...],
           calendar_today: [...],
           pending_actions: 3,
           unread_messages: 5
       }
```

---

## 5. Flux Notes

### 5.1 Création

```
EmailAnalysis.proposed_notes[0] { action: "create", ... }
    ↓
_auto_apply_proposals()
    ↓
NoteManager.create_note(title, content, tags, metadata)
    ├─ Crée fichier: notes/{note_id}.md
    ├─ Format YAML frontmatter + content
    ├─ Génère embeddings (vector store)
    └─ Ajoute à Git (versioning)
```

### 5.2 Sync Apple Notes

```
POST /api/notes/sync-apple
    ↓
NotesSync.sync_bidirectional(direction="BIDIRECTIONAL")
    ├─ AppleNotesClient.get_folders()
    ├─ AppleNotesClient.get_notes_in_folder()
    │
    └─ Pour chaque Apple Note:
        ├─ Convertit HTML → Markdown
        ├─ NoteManager.create_note()
        └─ Enregistre mapping: apple_id ↔ scapin_note_id
```

### 5.3 Indexation & Embedding

```
NoteManager.__init__(auto_index=True)
    ├─ Charge tous les fichiers .md
    ├─ Pour chaque note:
    │  ├─ EmbeddingGenerator.generate(content)
    │  │  └─ sentence-transformers (all-MiniLM-L6-v2, dim=384)
    │  └─ VectorStore.add(note_id, embedding)
    └─ VectorStore.persist(index_path)
```

### 5.4 Context Retrieval (Pass 2)

```
ReasoningEngine._pass2_context_enrichment(event)
    ↓
ContextEngine.find_relevant_notes(query, entities, top_k=5)
    ├─ Mode Entity-based: notes contenant entities
    ├─ Mode Semantic: VectorStore.search(embedding)
    └─ Mode Hybrid: combine les deux
        ↓
List[NoteReference] {
    note_id, title, relevance_score, snippet
}
    ↓
WorkingMemory.context_notes = [...]
    ↓
Inclus dans prompt AI → meilleure analyse
```

### 5.5 Révision SM-2

```
GET /api/notes/reviews/due
    ↓
NoteScheduler.get_notes_due(limit=50)
    └─ Query SQLite: WHERE next_review <= NOW()
        ↓
NotesDueResponse {
    notes: [{
        note_id, title, review_count,
        easiness_factor, interval_hours
    }]
}

POST /api/notes/{id}/review { quality: 4 }
    ↓
NoteScheduler.record_review(note_id, quality=4)
    ├─ Applique SM-2:
    │  EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    │  interval *= EF si q >= 3
    │  interval = 1 jour si q < 3
    └─ Enregistre: next_review = now + interval
```

---

## 6. Flux Journal

### 6.1 Génération Pré-remplissage

**Fichiers** :
- `src/jeeves/journal/generator.py`
- `src/jeeves/journal/providers/`

```
JournalGenerator.generate_entry(date)
    ├─ Récupère processing history:
    │  ├─ Emails traitées (date)
    │  ├─ Tasks créées (date)
    │  ├─ Messages Teams (date)
    │  ├─ Événements calendar (date)
    │  └─ Activité OmniFocus (date)
    │
    ├─ Génère questions auto:
    │  ├─ Pattern detection
    │  ├─ Preference learning
    │  └─ Calibration
    │
    └─ JournalEntry {
           date, summary, emails[], questions[], metadata
       }
```

### 6.2 Feedback Loop

```
POST /api/journal/answer { answers: {...} }
    ↓
FeedbackProcessor.process_feedback(journal_responses)
    ├─ Analyse divergence: User vs AI prediction
    ├─ Mise à jour LearningEngine:
    │  ├─ Pattern patterns_store.db
    │  ├─ Calibration seuils par source
    │  └─ Confidence scores entities
    │
    └─ Prochaine session: AI utilise patterns appris
```

---

## 7. Flux API REST

### 7.1 Structure Générale

```
HTTP Request
    ↓
FastAPI Middleware (CORS, Error Handling)
    ↓
Router (e.g., /api/briefing)
    ├─ Route matching
    ├─ Dependency injection
    └─ Handler function
        ├─ Validation (Pydantic)
        ├─ Call service method
        └─ Wrap in APIResponse
            ↓
HTTP 200 + JSON
```

### 7.2 Exemple : GET /api/briefing/morning

```
GET /api/briefing/morning?hours_ahead=24
    ↓
[Router] briefing_router.get_morning_briefing()
    ├─ Parse: hours_ahead=24
    ├─ DI: service = Depends(get_briefing_service)
    └─ service.generate_morning_briefing(24)
        ↓
[Service] BriefingService.generate_morning_briefing()
    ├─ CalendarClient.get_events() → HTTP Microsoft Graph
    ├─ QueueStorage.get_items() → SQLite
    ├─ TeamsClient.get_recent_messages() → HTTP Graph
    ├─ Trie & groupe par priorité
    ├─ ConflictDetector.detect_conflicts()
    └─ BriefingResult
        ↓
[Router] APIResponse[BriefingResponse]
    └─ HTTP 200 { success: true, data: {...} }
```

### 7.3 Queue Approve

```
POST /api/queue/{item_id}/approve
    ↓
[Service] QueueService.approve_item(item_id)
    ├─ Charge item: QueueStorage.get_item()
    ├─ Exécute action:
    │  ├─ archive → IMAPClient.move_email()
    │  ├─ task → OmniFocusClient.create_task()
    │  └─ note → NoteManager.create_note()
    ├─ FeedbackProcessor.process_feedback()
    ├─ QueueStorage.delete_item()
    └─ NotificationService.create()
        ↓
APIResponse { success: true, action_executed: "archive" }
```

### 7.4 WebSocket

```
Frontend: new WebSocket("/ws/live")
    ↓
[Server] Authenticate token
    ↓
Écoute EventBus:
    ├─ EMAIL_STARTED
    ├─ EMAIL_COMPLETED
    ├─ EMAIL_QUEUED
    └─ PROCESSING_COMPLETED
        ↓
Broadcast to client:
{
    type: "EMAIL_STARTED",
    email_id: "...",
    progress_percent: 15
}
```

---

## 8. Transformations de Données

### 8.1 Chaîne de Types

```
Source brute (IMAP/GraphAPI/SQL)
    ↓
Metadata schema (EmailMetadata/TeamsMessage/CalendarEvent)
    ↓
Normalizer → PerceivedEvent
    ↓
ReasoningResult → EmailAnalysis
    ↓
ActionPlan → List[Action]
    ↓
ExecutionResult
    ↓
APIResponse[T]
```

### 8.2 Modèles Clés

**PerceivedEvent** : Représentation universelle normalisée
```python
{
    event_type: EventType,
    event_id: str,
    source: SourceType,
    timestamp: datetime,
    entities: list[Entity],
    payload: dict,
    importance_score: float,
    perception_confidence: float
}
```

**EmailAnalysis** : Résultat d'analyse
```python
{
    action: EmailAction,
    confidence: int,  # 0-100
    category: EmailCategory,
    reasoning: str,
    proposed_notes: list[dict],
    proposed_tasks: list[dict],
    context_used: list[str]
}
```

---

## 9. Points d'Extension

### 9.1 Ajouter un Canal (e.g., Slack)

```
1. src/integrations/slack/client.py    # API wrapper
2. src/integrations/slack/normalizer.py # → PerceivedEvent
3. src/trivelin/slack_processor.py     # Orchestration
4. src/jeeves/api/routers/slack.py     # REST endpoints
5. src/jeeves/api/services/slack_service.py
6. Enregistrer dans app.py
```

### 9.2 Customiser le Scoring

```python
# src/core/events/normalizers/email_normalizer.py
def _calculate_importance_score(metadata: EmailMetadata) -> float:
    score = 0.5
    if "urgent" in metadata.subject.lower():
        score += 0.3
    if metadata.from_address in VIP_SENDERS:
        score += 0.2
    return min(1.0, score)
```

### 9.3 Ajouter une Action (Figaro)

```python
# src/figaro/actions/custom_action.py
class CustomAction(Action):
    def execute(self) -> bool:
        # Implémentation
        return True

# src/figaro/action_factory.py
ACTION_REGISTRY = {
    "CUSTOM_ACTION": CustomAction,
    # ...
}
```

---

## Performance et Optimisations

| Composant | Problème | Solution | Résultat |
|-----------|----------|----------|----------|
| IMAP | Relecture tous emails | Batch 200 + early-stop | 1s vs 43s |
| Notes | Re-indexing 227 notes | Singleton cache | 1min → <100ms |
| Vector search | Lenteur | FAISS persistence | <50ms |
| iCloud | Keyword search fails | Dual flag (IMAP + SQLite) | Compat full |

---

## Logging et Observabilité

### Événements Clés

| Type | Événement |
|------|-----------|
| **Processing** | processing_started, processing_completed |
| **Email** | email_started, email_completed, email_queued, email_error |
| **Batch** | batch_started, batch_completed, batch_progress |
| **System** | system_ready, system_error |

### Consommateurs

- **WebSocket** : Real-time frontend updates
- **CLI** : Progress bar / status display
- **Logs** : Audit trail

---

## Résumé

| Flux | Composants | Durée | Sortie |
|------|-----------|-------|--------|
| **Email** | IMAP → Normalize → Pipeline → Queue | 1-3s | Analysis + Actions |
| **Teams** | Graph → Normalize → Reason → Execute | 500ms-2s | Reply + Flags |
| **Calendar** | Graph → Normalize → Briefing | 200ms | BriefingResponse |
| **Notes** | Create/Sync → Index → SM-2 → Vector | 50-100ms | RelevantNotes[] |
| **Journal** | Fetch → Generate → Record → Learn | 1-5s | JournalEntry |
| **API** | HTTP → Router → Service → Response | <100ms | APIResponse[T] |
