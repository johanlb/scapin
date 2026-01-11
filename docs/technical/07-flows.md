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
├─ Stage 2: REASON (Sancho) ~500ms-2s
│  ├─ Pass 1: Perception + Entity Recognition
│  ├─ Pass 2: Context Retrieval (Passepartout)
│  ├─ Pass 3: Analysis + Proposals
│  ├─ Pass 4: Cross-source Enrichment
│  ├─ Pass 5: Convergence + Confidence
│  └─ Continue jusqu'à: convergence OU max_passes (5)
│     ↓
│  ReasoningResult {
│      confidence: 0.92,
│      converged: true,
│      passes_executed: 3,
│      final_analysis: EmailAnalysis
│  }
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
