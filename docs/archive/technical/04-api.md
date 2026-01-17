# API REST FastAPI

**Version** : 0.8.0
**Dernière mise à jour** : 11 janvier 2026
**Répertoire** : `src/jeeves/api/`

---

## Table des Matières

1. [Architecture de l'Application](#1-architecture-de-lapplication)
2. [Système d'Authentification JWT](#2-système-dauthentification-jwt)
3. [Dependency Injection](#3-dependency-injection)
4. [Middleware et CORS](#4-middleware-et-cors)
5. [Modèles Request/Response](#5-modèles-requestresponse)
6. [Routers et Endpoints](#6-routers-et-endpoints)
7. [Services](#7-services)
8. [WebSocket](#8-websocket)
9. [Gestion d'Erreurs](#9-gestion-derreurs)

---

## 1. Architecture de l'Application

### 1.1 Factory Pattern (`src/jeeves/api/app.py`)

L'application utilise le **Factory Pattern** pour la création et configuration de l'instance FastAPI.

```python
def create_app() -> FastAPI:
    """Crée et configure l'application FastAPI avec tous les routers et middleware."""
```

**Caractéristiques** :
- **Titre** : "Scapin API"
- **Version** : "0.8.0"
- **Docs** : `/docs` (Swagger UI)
- **ReDoc** : `/redoc` (OpenAPI viewer)
- **OpenAPI Schema** : `/openapi.json`

### 1.2 Lifespan Management

Le gestionnaire de cycle de vie `lifespan` :

**Au démarrage** :
- Affiche un warning si l'authentification est désactivée en production
- Lance une tâche de nettoyage des notifications (toutes les heures)

**À l'arrêt** :
- Annule la tâche de nettoyage
- Log l'arrêt du système

### 1.3 Configuration des Routers

L'application inclut **16 routers** :

| Préfixe | Router | Tags |
|---------|--------|------|
| `/api/auth` | `auth_router` | Authentication |
| `/api` | `system_router` | System |
| `/api/briefing` | `briefing_router` | Briefing |
| `/api/discussions` | `discussions_router` | Discussions |
| `/api/drafts` | `drafts_router` | Drafts |
| `/api/events` | `events_router` | Events |
| `/api/journal` | `journal_router` | Journal |
| `/api/queue` | `queue_router` | Queue |
| `/api/email` | `email_router` | Email |
| `/api/calendar` | `calendar_router` | Calendar |
| `/api/teams` | `teams_router` | Teams |
| `/api/notes` | `notes_router` | Notes |
| `/api/search` | `search_router` | Search |
| `/api/stats` | `stats_router` | Stats |
| `/api/notifications` | `notifications_router` | Notifications |
| `/api/valets` | `valets_router` | Valets |
| `/ws` | `ws_router` | WebSocket |

### 1.4 Exception Handler Global

```python
@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Capture toutes les exceptions non gérées."""
```

- Log les détails complets
- Retourne un message générique au client (sécurité)
- Statut HTTP : `500 Internal Server Error`

---

## 2. Système d'Authentification JWT

### 2.1 JWT Handler (`src/jeeves/api/auth/jwt_handler.py`)

**Classe** : `JWTHandler`

```python
def __init__(
    self,
    secret_key: Optional[str] = None,      # JWT secret
    algorithm: Optional[str] = None,        # Default: "HS256"
    expire_minutes: Optional[int] = None,   # Default: 10080 (7 jours)
) -> None:
```

**Méthodes** :

| Méthode | Description | Retour |
|---------|-------------|--------|
| `create_access_token(subject)` | Crée un token JWT | `str` |
| `verify_token(token)` | Vérifie et décode | `Optional[TokenData]` |

### 2.2 Modèle TokenData

```python
class TokenData(BaseModel):
    sub: str        # Subject (username)
    exp: datetime   # Expiration
    iat: datetime   # Issued at
```

### 2.3 Rate Limiting (`src/jeeves/api/auth/rate_limiter.py`)

**Classe** : `LoginRateLimiter`

Protection contre les attaques par force brute :

```python
max_attempts: int = 5              # Tentatives avant verrouillage
window_seconds: int = 300          # Fenêtre de temps (5 min)
lockout_seconds: int = 60          # Durée initiale verrouillage
lockout_multiplier: float = 2.0    # Multiplicateur (exponentiel)
max_lockout_seconds: int = 3600    # Max 1 heure
```

**Méthodes** :

| Méthode | Description |
|---------|-------------|
| `check_rate_limit(client_id)` | Vérifie si tentative autorisée |
| `record_attempt(client_id, success)` | Enregistre tentative |
| `cleanup(max_age_seconds)` | Nettoie entrées anciennes |
| `get_stats()` | Statistiques du limiteur |

### 2.4 Authentification par PIN

Système mono-utilisateur avec PIN 4-6 chiffres :

```python
def verify_pin(pin: str, pin_hash: str) -> bool:
    """Vérifie le PIN contre le hash stocké."""
```

---

## 3. Dependency Injection

### 3.1 Configuration (`src/jeeves/api/deps.py`)

```python
@lru_cache
def get_cached_config() -> ScapinConfig:
    """Configuration singleton en cache."""
```

### 3.2 JWT Handler

```python
@lru_cache
def get_jwt_handler() -> JWTHandler:
    """Instance globale JWTHandler."""
```

### 3.3 Authentification Utilisateur

```python
def get_current_user(credentials, jwt_handler) -> Optional[TokenData]:
    """Vérifie token JWT et retourne utilisateur."""
```

**Comportement** :
- Auth désactivée : Retourne `None` (accès autorisé)
- Auth activée + token valide : Retourne `TokenData`
- Auth activée + token invalide : `401 Unauthorized`

### 3.4 Services (Singletons)

| Service | Fonction | Caching |
|---------|----------|---------|
| `BriefingService` | `get_briefing_service()` | Par requête |
| `NotesService` | `get_notes_service()` | **Singleton global** |
| `NotesReviewService` | `get_notes_review_service()` | **Singleton global** |
| `QueueService` | `get_queue_service()` | Par requête |
| `EmailService` | `get_email_service()` | Par requête |
| `DiscussionService` | `get_discussion_service()` | Par requête |

---

## 4. Middleware et CORS

### Configuration CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=config.api.cors_methods,
    allow_headers=config.api.cors_headers,
)
```

**Variables d'environnement** :
- `API__CORS_ORIGINS` : `["http://localhost:3000", "http://localhost:5173"]`
- `API__CORS_METHODS` : `["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]`
- `API__CORS_HEADERS` : `["*"]`

---

## 5. Modèles Request/Response

### 5.1 APIResponse (Wrapper Standard)

```python
class APIResponse(BaseModel, Generic[T]):
    success: bool                      # Succès ou échec
    data: T | None = None             # Données retournées
    error: str | None = None          # Message d'erreur
    timestamp: datetime                # Horodatage UTC
```

### 5.2 PaginatedResponse

```python
class PaginatedResponse(APIResponse[T]):
    total: int         # Nombre total d'items
    page: int          # Page courante
    page_size: int     # Items par page
    has_more: bool     # Autres pages?
```

### 5.3 HealthResponse

```python
class HealthCheckResult(BaseModel):
    name: str                  # Nom du check
    status: str                # "ok", "warning", "error"
    message: str | None        # Détail optionnel
    latency_ms: float | None   # Latence en ms

class HealthResponse(BaseModel):
    status: str                        # "healthy", "degraded", "unhealthy"
    checks: list[HealthCheckResult]    # Résultats individuels
    uptime_seconds: float
    version: str
```

### 5.4 SystemStatusResponse

```python
class ComponentStatus(BaseModel):
    name: str              # Nom du composant
    state: str             # "active", "idle", "disabled", "error"
    last_activity: datetime | None
    details: str | None

class SystemStatusResponse(BaseModel):
    state: str                         # "idle", "running", "paused", "stopped", "error"
    current_task: str | None
    active_connections: int
    components: list[ComponentStatus]
    session_stats: SessionStatsResponse
    uptime_seconds: float
    last_activity: datetime | None
```

---

## 6. Routers et Endpoints

### 6.1 Authentification (`/api/auth`)

#### POST /api/auth/login

Authentification avec PIN.

**Request** :
```json
{ "pin": "1234" }
```

**Response** (200 OK) :
```json
{
    "success": true,
    "data": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer",
        "expires_in": 604800
    },
    "timestamp": "2026-01-11T10:30:00Z"
}
```

**Erreurs** : 400 (format), 401 (incorrect), 429 (rate limit), 500 (non configuré)

#### GET /api/auth/check

Vérification du statut d'authentification.

**Response** (200 OK) :
```json
{
    "success": true,
    "data": {
        "authenticated": true,
        "user": "johan",
        "auth_required": true
    }
}
```

---

### 6.2 Système (`/api`)

#### GET /api/health

Santé du système.

**Response** (200 OK) :
```json
{
    "success": true,
    "data": {
        "status": "healthy",
        "checks": [
            {"name": "config", "status": "ok", "message": "Configuration loaded"},
            {"name": "email", "status": "ok", "message": "2 account(s) configured"},
            {"name": "teams", "status": "ok", "message": "Teams integration enabled"}
        ],
        "uptime_seconds": 3600.5,
        "version": "0.8.0"
    }
}
```

#### GET /api/stats

Statistiques de traitement.

#### GET /api/config

Configuration système (secrets masqués).

#### GET /api/status

Statut en temps réel.

---

### 6.3 Briefing (`/api/briefing`)

#### GET /api/briefing/morning

Briefing du matin.

**Query Parameters** :
- `hours_ahead` (int, 1-48, default: 24)

**Response** (200 OK) :
```json
{
    "success": true,
    "data": {
        "date": "2026-01-11",
        "generated_at": "2026-01-11T08:00:00Z",
        "urgent_count": 3,
        "meetings_today": 5,
        "urgent_items": [...],
        "calendar_today": [...],
        "emails_pending": [...],
        "teams_unread": [...],
        "ai_summary": "You have 3 urgent items...",
        "key_decisions": [...]
    }
}
```

#### GET /api/briefing/meeting/{id}

Briefing pré-réunion avec contexte participants.

---

### 6.4 Queue (`/api/queue`)

#### GET /api/queue

Liste des items en attente.

**Query Parameters** :
- `account_id` (string, optional)
- `status` (string, default: "pending")
- `page` (int, default: 1)
- `page_size` (int, default: 20, max: 100)

#### GET /api/queue/stats

Statistiques de la queue.

#### POST /api/queue/{id}/approve

Approuver un item.

**Request** :
```json
{
    "execute_action": true,
    "notes": "Approved - looks good"
}
```

#### POST /api/queue/{id}/reject

Rejeter un item.

#### POST /api/queue/{id}/snooze

Reporter un item.

#### DELETE /api/queue/{id}

Supprimer un item.

---

### 6.5 Notes (`/api/notes`)

#### GET /api/notes/tree

Arbre des notes avec hiérarchie dossiers.

**Query Parameters** :
- `recent_limit` (int, 1-50, default: 10)

#### GET /api/notes

Liste des notes avec filtres.

**Query Parameters** :
- `path` (string, optional)
- `tags` (string, comma-separated)
- `pinned` (bool, default: false)
- `page`, `page_size`

#### GET /api/notes/{id}

Note complète avec contenu.

#### POST /api/notes

Créer une note.

#### PUT /api/notes/{id}

Mettre à jour une note.

#### GET /api/notes/reviews/due

Notes à réviser (SM-2).

#### POST /api/notes/{id}/review

Enregistrer révision (rating 0-5).

---

### 6.6 Journal (`/api/journal`)

#### GET /api/journal/{date}

Entrée journal pour une date.

#### GET /api/journal

Liste des entrées.

#### POST /api/journal/{date}/answer

Soumettre réponse à une question.

---

### 6.7 Discussions (`/api/discussions`)

#### POST /api/discussions

Créer une discussion.

#### GET /api/discussions

Lister les discussions.

#### GET /api/discussions/{id}

Discussion complète avec messages.

#### POST /api/discussions/{id}/messages

Ajouter un message.

---

### 6.8 Email (`/api/email`)

#### GET /api/email/accounts

Comptes email configurés.

#### GET /api/email/stats

Statistiques traitement email.

#### POST /api/email/process

Lancer traitement inbox.

#### POST /api/email/analyze

Analyser un email spécifique.

---

### 6.9 Teams (`/api/teams`)

#### GET /api/teams/chats

Lister les chats.

#### GET /api/teams/chats/{chat_id}/messages

Messages d'un chat.

#### POST /api/teams/chats/{chat_id}/messages/{msg_id}/reply

Répondre à un message.

#### POST /api/teams/poll

Synchroniser Teams.

---

### 6.10 Calendar (`/api/calendar`)

#### GET /api/calendar/events

Lister les événements.

#### GET /api/calendar/events/{id}

Détails d'un événement.

#### GET /api/calendar/today

Événements du jour.

#### POST /api/calendar/events/{id}/respond

Répondre à une invitation.

#### POST /api/calendar/poll

Synchroniser calendrier.

---

## 7. Services

### 7.1 BriefingService

**Fichier** : `src/jeeves/api/services/briefing_service.py`

```python
async def generate_morning_briefing(hours_ahead: int = 24) -> MorningBriefing
async def generate_pre_meeting_briefing(event_id: str) -> PreMeetingBriefing
```

### 7.2 NotesService

**Fichier** : `src/jeeves/api/services/notes_service.py`

```python
def get_notes_tree(recent_limit: int) -> NotesTreeResponse
def list_notes(path, tags, pinned_only, limit, offset) -> tuple[list, int]
def get_note(note_id: str) -> NoteResponse
def create_note(request: NoteCreateRequest) -> NoteResponse
def update_note(note_id: str, request: NoteUpdateRequest) -> NoteResponse
def delete_note(note_id: str) -> None
def search_notes(query: str, limit: int) -> NoteSearchResponse
def sync_apple_notes() -> NoteSyncStatus
```

### 7.3 NotesReviewService

**Fichier** : `src/jeeves/api/services/notes_review_service.py`

```python
def get_notes_due(limit: int) -> NotesDueResponse
def record_review(note_id: str, rating: int) -> RecordReviewResponse
def postpone_review(note_id: str, hours: int) -> PostponeReviewResponse
def get_review_stats() -> ReviewStatsResponse
def get_review_workload() -> ReviewWorkloadResponse
```

### 7.4 QueueService

**Fichier** : `src/jeeves/api/services/queue_service.py`

```python
def list_items(account_id, status, page, page_size) -> tuple[list, int]
def get_item(item_id: str) -> dict | None
def approve_item(item_id: str, execute: bool) -> dict
def reject_item(item_id: str, reason: str) -> dict
def snooze_item(item_id: str, until: datetime, reason: str) -> dict
def delete_item(item_id: str) -> None
def get_stats() -> QueueStatsResponse
```

### 7.5 EmailService

**Fichier** : `src/jeeves/api/services/email_service.py`

```python
def get_accounts() -> list[dict]
def get_stats() -> dict
def process_inbox(limit, auto_execute, confidence_threshold, ...) -> dict
def analyze_email(email_id: str, account_id: str) -> dict
```

### 7.6 DiscussionService

**Fichier** : `src/jeeves/api/services/discussion_service.py`

```python
def create_discussion(request: DiscussionCreateRequest) -> DiscussionDetailResponse
def list_discussions(discussion_type, attached_to_id, page, page_size) -> DiscussionListResponse
def get_discussion(discussion_id: str) -> DiscussionDetailResponse
def add_message(discussion_id: str, content: str) -> MessageResponse
def get_suggestions(discussion_id: str) -> list[SuggestionResponse]
```

---

## 8. WebSocket

### 8.1 Endpoint

**URL** : `/ws/live`

**Fichier** : `src/jeeves/api/websocket/router.py`

### 8.2 Authentification

**Méthode 1 : Message d'authentification** (recommandée)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live');
ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'auth', token: 'JWT_TOKEN' }));
};
```

**Méthode 2 : Query parameter** (dépréciée)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live?token=JWT_TOKEN');
```

### 8.3 Messages Reçus

```json
{ "type": "authenticated" }
{ "type": "connected", "timestamp": "2026-01-11T10:30:00Z" }
{ "type": "event", "data": { "event_type": "email_started", ... } }
```

### 8.4 Types d'Événements

| Catégorie | Événements |
|-----------|------------|
| **Processing** | processing_started, processing_completed |
| **Account** | account_started, account_completed, account_error |
| **Email** | email_started, email_analyzing, email_completed, email_queued, email_executed, email_error |
| **Batch** | batch_started, batch_completed, batch_progress |
| **System** | system_ready, system_error |

### 8.5 ConnectionManager

**Fichier** : `src/jeeves/api/websocket/manager.py`

- Thread-safe pour connexions concurrentes
- Souscription automatique à EventBus
- Diffusion asynchrone aux clients
- Gestion des déconnexions gracieuses

---

## 9. Gestion d'Erreurs

### 9.1 Codes HTTP

| Code | Raison |
|------|--------|
| **200** | OK |
| **201** | Created |
| **400** | Bad Request |
| **401** | Unauthorized |
| **403** | Forbidden |
| **404** | Not Found |
| **429** | Too Many Requests |
| **500** | Internal Server Error |

### 9.2 Format d'Erreur

```json
{
    "success": false,
    "error": "Description de l'erreur",
    "timestamp": "2026-01-11T10:30:00Z"
}
```

### 9.3 Erreurs de Validation

FastAPI retourne 422 Unprocessable Entity :

```json
{
    "detail": [
        {
            "loc": ["body", "pin"],
            "msg": "ensure this value has at least 4 characters",
            "type": "value_error.string.too_short"
        }
    ]
}
```

---

## Résumé

L'API FastAPI fournit :

- **16 routers** couvrant tous les domaines
- **Authentification JWT** avec rate limiting
- **Modèles Pydantic** pour validation automatique
- **WebSocket** pour événements temps-réel
- **Singletons** pour services coûteux
- **Documentation Swagger** sur `/docs`

**Documentation interactive** : `http://localhost:8000/docs`
