# 03 - Intégrations : Email, Microsoft, Apple

**Module** : `src/integrations/`
**Lignes de code** : ~7,800
**Rôle** : Connexion aux systèmes externes

---

## Vue d'Ensemble

```
src/integrations/
├── email/                    # IMAP (~1,700 lignes)
│   ├── imap_client.py        # Client IMAP
│   ├── processed_tracker.py  # SQLite tracking
│   └── folder_preferences.py # Préférences dossiers
├── microsoft/                # Graph API (~2,200 lignes)
│   ├── auth.py               # MSAL OAuth
│   ├── graph_client.py       # HTTP client
│   ├── models.py             # Teams models
│   ├── calendar_models.py    # Calendar models
│   ├── teams_client.py       # Teams client
│   ├── calendar_client.py    # Calendar client
│   ├── teams_normalizer.py   # → PerceivedEvent
│   └── calendar_normalizer.py# → PerceivedEvent
├── apple/                    # AppleScript (~2,400 lignes)
│   ├── notes_client.py       # Apple Notes
│   ├── notes_models.py       # Models
│   ├── notes_sync.py         # Sync bidirectionnelle
│   ├── omnifocus_client.py   # OmniFocus
│   ├── omnifocus_models.py   # Models
│   └── omnifocus_normalizer.py
└── storage/                  # JSON (~1,500 lignes)
    ├── queue_storage.py      # File d'attente
    ├── draft_storage.py      # Brouillons
    ├── discussion_storage.py # Discussions
    ├── action_history.py     # Historique
    └── snooze_storage.py     # Rappels
```

---

## 1. Intégration Email (IMAP)

### IMAPClient

**Fichier** : `src/integrations/email/imap_client.py` (~1,426 lignes)

```python
class IMAPClient:
    def __init__(self, config: EmailAccountConfig):
        self.config = config
        self._connection: Optional[IMAP4_SSL] = None
        self._lock = threading.Lock()

    @contextmanager
    def connect(self):
        """Context manager pour connexion"""
        try:
            self._connection = IMAP4_SSL(
                self.config.imap_host,
                self.config.imap_port,
                timeout=self.config.imap_timeout
            )
            self._connection.login(
                self.config.imap_username,
                self.config.imap_password
            )
            yield self
        finally:
            self._connection.logout()
```

**Méthodes principales** :

| Méthode | Description |
|---------|-------------|
| `list_folders()` | Liste des dossiers IMAP |
| `fetch_emails(folder, limit, unread_only)` | Récupère emails avec batch |
| `fetch_metadata(message_ids)` | Métadonnées en batch |
| `fetch_content(message_id)` | Contenu complet |
| `move_email(msg_id, from_folder, to_folder)` | Déplace email |
| `add_flag(message_ids, flags)` | Ajoute flags |
| `mark_as_processed(message_id)` | Flag Scapin |
| `get_attachment(msg_id, filename)` | Télécharge pièce jointe |

**Encodage IMAP UTF-7** :

```python
def encode_imap_folder_name(folder_name: str) -> str:
    """Convertit noms avec caractères non-ASCII"""
    # "À Archiver" → "&AMA--Archiver"
```

**Optimisation Batch** :

```python
def _fetch_emails_batch(self, msg_ids, folder, batch_size=50):
    """Réduit round-trips réseau"""
    # Au lieu de N requêtes, ceil(N/50) requêtes
```

### ProcessedEmailTracker

**Fichier** : `src/integrations/email/processed_tracker.py` (~272 lignes)

**Problème** : iCloud IMAP ne supporte pas `KEYWORD/UNKEYWORD` search.

**Solution** : SQLite local.

```python
class ProcessedEmailTracker:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path("data/processed_emails.db")
        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )
        self._create_table()

    def is_processed(self, message_id: str) -> bool:
        """Vérifie si email déjà traité"""

    def mark_processed(
        self,
        message_id: str,
        account_id: str,
        subject: str,
        from_address: str
    ):
        """Marque comme traité"""

    def get_unprocessed_message_ids(
        self,
        all_message_ids: list[str],
        account_id: str
    ) -> list[str]:
        """Filtre les non-traités"""

    def clear_old_entries(self, days: int = 365) -> int:
        """Nettoie anciennes entrées"""
```

**Flag IMAP** :
```python
SCAPIN_PROCESSED_FLAG = "$MailFlagBit6"  # Drapeau gris Apple Mail
```

---

## 2. Intégration Microsoft

### Authentification MSAL

**Fichier** : `src/integrations/microsoft/auth.py` (~226 lignes)

```python
class MicrosoftAuthenticator:
    def __init__(self, config: MicrosoftAccountConfig, cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir
        self._app = msal.PublicClientApplication(
            config.client_id,
            authority=f"https://login.microsoftonline.com/{config.tenant_id}"
        )

    def get_token(self) -> str:
        """Récupère token (cache ou interactive)"""
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(
                self.config.scopes,
                account=accounts[0]
            )
            if result:
                return result["access_token"]

        return self._interactive_login()

    def _interactive_login(self) -> str:
        """Device code flow"""
        flow = self._app.initiate_device_flow(scopes=self.config.scopes)
        print(f"Go to {flow['verification_uri']} and enter {flow['user_code']}")
        result = self._app.acquire_token_by_device_flow(flow)
        return result["access_token"]
```

### GraphClient

**Fichier** : `src/integrations/microsoft/graph_client.py` (~343 lignes)

```python
@dataclass
class GraphClient:
    authenticator: MicrosoftAuthenticator
    base_url: str = "https://graph.microsoft.com/v1.0"
    max_retries: int = 3
    timeout_seconds: float = 30.0

    async def get(self, endpoint: str, params: dict = None) -> dict:
        """GET avec retry + rate limiting"""

    async def post(self, endpoint: str, json_data: dict) -> dict:
        """POST"""

    async def get_all_pages(self, endpoint: str, max_pages: int = 100) -> list:
        """Pagination automatique (@odata.nextLink)"""

    async def get_delta(self, resource: str) -> tuple[list, str]:
        """Delta queries pour polling efficace"""
```

### TeamsClient

**Fichier** : `src/integrations/microsoft/teams_client.py` (~367 lignes)

```python
class TeamsClient:
    def __init__(self, graph_client: GraphClient):
        self.client = graph_client

    async def get_chats(self) -> list[TeamsChat]:
        """Liste les chats"""

    async def get_messages(
        self,
        chat_id: str,
        limit: int = 50,
        since: datetime = None
    ) -> list[TeamsMessage]:
        """Messages d'un chat"""

    async def get_recent_messages(
        self,
        limit_per_chat: int = 10,
        mentions_only: bool = False
    ) -> list[TeamsMessage]:
        """Messages récents tous chats"""

    async def send_message(
        self,
        chat_id: str,
        content: str
    ) -> TeamsMessage:
        """Envoie un message"""

    async def reply_to_message(
        self,
        chat_id: str,
        message_id: str,
        content: str
    ) -> TeamsMessage:
        """Répond à un message"""

    async def get_presence(self, user_id: str = None) -> dict:
        """Statut de présence"""
```

### CalendarClient

**Fichier** : `src/integrations/microsoft/calendar_client.py` (~400 lignes)

```python
class CalendarClient:
    def __init__(self, graph_client: GraphClient):
        self.client = graph_client

    async def get_events(
        self,
        days_ahead: int = 7,
        days_behind: int = 0,
        limit: int = 100
    ) -> list[CalendarEvent]:
        """Événements dans une plage"""

    async def get_calendar_view(
        self,
        start: datetime,
        end: datetime
    ) -> list[CalendarEvent]:
        """Vue calendrier (expand recurring)"""

    async def get_upcoming_events(
        self,
        hours_ahead: int = 24
    ) -> list[CalendarEvent]:
        """Événements à venir"""

    async def create_event(
        self,
        subject: str,
        start: datetime,
        end: datetime,
        attendees: list[str] = None,
        is_online: bool = False
    ) -> CalendarEvent:
        """Crée un événement"""

    async def respond_to_event(
        self,
        event_id: str,
        response: str  # accept, tentative, decline
    ) -> bool:
        """RSVP"""
```

### Modèles Teams

```python
@dataclass(frozen=True)
class TeamsSender:
    user_id: str
    display_name: str
    email: Optional[str] = None

@dataclass(frozen=True)
class TeamsChat:
    chat_id: str
    chat_type: TeamsChatType  # ONE_ON_ONE, GROUP, MEETING
    created_at: datetime
    topic: Optional[str] = None
    members: tuple[TeamsSender, ...] = ()

@dataclass(frozen=True)
class TeamsMessage:
    message_id: str
    chat_id: str
    sender: TeamsSender
    content: str              # HTML
    content_plain: str        # Text
    created_at: datetime
    importance: TeamsMessageImportance  # NORMAL, HIGH, URGENT
    mentions: tuple[str, ...]
    attachments: tuple[str, ...]
    is_reply: bool
    reply_to_id: Optional[str] = None
    chat: Optional[TeamsChat] = None
```

### Modèles Calendar

```python
@dataclass(frozen=True)
class CalendarAttendee:
    email: str
    display_name: str
    response_status: CalendarResponseStatus
    attendee_type: str = "required"
    is_organizer: bool = False

@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    calendar_id: str
    subject: str
    body_preview: str
    body_content: str
    start: datetime
    end: datetime
    timezone: str
    is_all_day: bool
    organizer: CalendarAttendee
    attendees: tuple[CalendarAttendee, ...]
    location: Optional[CalendarLocation] = None
    is_online_meeting: bool = False
    online_meeting_url: Optional[str] = None
    is_cancelled: bool = False
    is_recurring: bool = False

    @property
    def duration_minutes(self) -> int: ...

    @property
    def is_meeting(self) -> bool: ...

    @property
    def is_in_progress(self) -> bool: ...
```

### Normalizers

```python
class TeamsNormalizer:
    def normalize(self, message: TeamsMessage) -> PerceivedEvent:
        """TeamsMessage → PerceivedEvent"""
        # event_type basé sur importance/mentions
        # entities: sender, mentions, chat topic
        # metadata: message_id, sender_id, importance

class CalendarNormalizer:
    def normalize(self, event: CalendarEvent) -> PerceivedEvent:
        """CalendarEvent → PerceivedEvent"""
        # event_type: INVITATION si future, INFORMATION si passé
        # entities: organizer, attendees, location
```

---

## 3. Intégration Apple

### AppleNotesClient

**Fichier** : `src/integrations/apple/notes_client.py` (~450 lignes)

```python
class AppleNotesClient:
    def __init__(self, timeout: int = 180):
        self.timeout = timeout  # 3 min pour gros dossiers

    def get_folders(self) -> list[AppleFolder]:
        """Liste dossiers via AppleScript"""

    def get_notes_in_folder(self, folder_path: str) -> list[AppleNote]:
        """Notes d'un dossier"""

    def get_all_notes(self) -> list[AppleNote]:
        """Toutes les notes"""

    def get_note_by_id(self, note_id: str) -> Optional[AppleNote]:
        """Note par ID"""

    def create_note(
        self,
        folder_name: str,
        title: str,
        body_html: str
    ) -> Optional[str]:
        """Crée une note, retourne ID"""

    def update_note(
        self,
        note_id: str,
        title: str = None,
        body_html: str = None
    ) -> bool:
        """Met à jour une note"""

    def delete_note(self, note_id: str) -> bool:
        """Supprime une note"""

    def move_note_to_folder(self, note_id: str, folder_path: str) -> bool:
        """Déplace une note"""

    def _run_applescript(self, script: str) -> str:
        """Exécute AppleScript via subprocess"""
```

### AppleNotesSync

**Fichier** : `src/integrations/apple/notes_sync.py` (~600 lignes)

```python
class SyncDirection(str, Enum):
    APPLE_TO_SCAPIN = "apple_to_scapin"
    SCAPIN_TO_APPLE = "scapin_to_apple"
    BIDIRECTIONAL = "bidirectional"

class ConflictResolution(str, Enum):
    APPLE_WINS = "apple_wins"
    SCAPIN_WINS = "scapin_wins"
    NEWER_WINS = "newer_wins"
    MANUAL = "manual"

@dataclass
class SyncResult:
    success: bool
    direction: SyncDirection
    created: list[str]
    updated: list[str]
    deleted: list[str]
    conflicts: list[SyncConflict]
    errors: list[str]
    started_at: datetime
    completed_at: Optional[datetime] = None

class AppleNotesSync:
    def __init__(
        self,
        notes_client: AppleNotesClient,
        scapin_notes_dir: Path,
        mappings_file: Path
    ):
        self.notes_client = notes_client
        self.scapin_notes_dir = scapin_notes_dir
        self.mappings = self._load_mappings()

    def sync(
        self,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        conflict_resolution: ConflictResolution = ConflictResolution.NEWER_WINS,
        dry_run: bool = False
    ) -> SyncResult:
        """Exécute la synchronisation"""
        # 1. Récupère notes Apple
        # 2. Récupère notes Scapin
        # 3. Détermine actions (create, update, delete, conflict)
        # 4. Exécute actions
        # 5. Sauvegarde mappings
```

**Mappings** (`data/apple_notes_sync.json`) :

```json
{
  "x-coredata://...ID": {
    "apple_id": "...",
    "scapin_path": "Entités/Jean Dupont.md",
    "apple_modified": "2026-01-11T10:30:00",
    "scapin_modified": "2026-01-11T09:15:00",
    "last_synced": "2026-01-11T10:31:00"
  }
}
```

### OmniFocusClient

**Fichier** : `src/integrations/apple/omnifocus_client.py`

```python
class OmniFocusClient:
    def get_inbox_tasks(self) -> list[OmniFocusTask]:
        """Tâches inbox"""

    def get_due_tasks(self, days_ahead: int = 7) -> list[OmniFocusTask]:
        """Tâches dues"""

    def get_flagged_tasks(self) -> list[OmniFocusTask]:
        """Tâches flaggées"""

    def get_projects(self) -> list[OmniFocusProject]:
        """Projets actifs"""

    def create_task(
        self,
        title: str,
        project: str = None,
        due_date: datetime = None,
        note: str = None
    ) -> Optional[str]:
        """Crée une tâche"""

    def complete_task(self, task_id: str) -> bool:
        """Marque comme complète"""
```

---

## 4. Storage

### QueueStorage

**Fichier** : `src/integrations/storage/queue_storage.py` (~300 lignes)

```python
class QueueStorage:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.queue_file = storage_dir / "queue.json"
        self._lock = threading.Lock()
        self._processed_message_ids: set[str] = set()

    def save_item(
        self,
        metadata: EmailMetadata,
        analysis: EmailAnalysis,
        preview: str,
        account_id: str,
        html_body: str = None,
        full_text: str = None
    ) -> Optional[str]:
        """Sauvegarde item en queue"""

    def load_queue(
        self,
        account_id: str = None,
        status: str = "pending"
    ) -> list[dict]:
        """Charge queue avec filtres"""

    def get_item(self, item_id: str) -> Optional[dict]:
        """Récupère un item"""

    def update_item_status(
        self,
        item_id: str,
        status: str,
        decision: str = None
    ) -> bool:
        """Met à jour statut"""

    def remove_item(self, item_id: str) -> bool:
        """Supprime item"""

    def get_stats(self) -> dict:
        """Statistiques queue"""

    def is_email_known(self, message_id: str) -> bool:
        """Déduplication (bug #60 fix)"""
```

**Structure Item** :

```json
{
  "id": "uuid",
  "account_id": "personal",
  "queued_at": "2026-01-11T10:30:00",
  "metadata": {
    "id": 12345,
    "subject": "...",
    "from_address": "...",
    "message_id": "<id@domain>"
  },
  "analysis": {
    "action": "ARCHIVE",
    "confidence": 0.65,
    "category": "INFORMATION",
    "reasoning": "..."
  },
  "content": {
    "preview": "...",
    "html_body": "...",
    "full_text": "..."
  },
  "status": "pending"
}
```

### DraftStorage

```python
class DraftStorage:
    def save_draft(
        self,
        account_id: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str = None
    ) -> str:
        """Sauvegarde brouillon"""

    def get_draft(self, draft_id: str) -> Optional[dict]:
        """Récupère brouillon"""

    def list_drafts(
        self,
        account_id: str = None,
        status: str = "draft"
    ) -> list[dict]:
        """Liste brouillons"""

    def update_draft(self, draft_id: str, **updates) -> bool:
        """Met à jour"""

    def delete_draft(self, draft_id: str) -> bool:
        """Supprime"""
```

---

## Flux d'Intégration

### Email → Traitement

```
IMAPClient.fetch_emails()
    │
    ▼
EmailMetadata + EmailContent
    │
    ▼
EmailNormalizer.normalize()
    │
    ▼
PerceivedEvent
    │
    ▼
CognitivePipeline
    │
    ├─ Confiance >= 0.85 → Figaro.execute()
    │                          │
    │                          ▼
    │                      IMAPClient.move_email()
    │
    └─ Confiance < 0.85 → QueueStorage.save_item()
```

### Teams → Briefing

```
TeamsClient.get_recent_messages()
    │
    ▼
list[TeamsMessage]
    │
    ▼
TeamsNormalizer.normalize() (pour chaque)
    │
    ▼
list[PerceivedEvent]
    │
    ▼
BriefingGenerator (groupe par importance)
    │
    ▼
MorningBriefing
```

### Apple Notes ↔ Scapin

```
AppleNotesSync.sync()
    │
    ├─ _get_apple_notes() ─────────┐
    │                              ▼
    │                     dict[id → AppleNote]
    │                              │
    ├─ _get_scapin_notes() ────────┤
    │                              ▼
    │                     dict[path → (file, mtime)]
    │                              │
    └─ _determine_sync_actions() ──┘
                   │
                   ▼
           list[(id, action, data)]
                   │
                   ▼
           _execute_sync_actions()
                   │
           ┌───────┼───────┐
           ▼       ▼       ▼
        CREATE  UPDATE  DELETE
                   │
                   ▼
           _save_mappings()
```

---

## Contraintes et Limites

### Email IMAP

| Contrainte | Détail |
|------------|--------|
| iCloud KEYWORD | Pas de support → SQLite local |
| Batch size | Max 50 pour éviter timeout |
| Dossiers imbriqués | Support `Archive/2025/Personal` |
| Flags | Custom via SQLite, pas IMAP |

### Microsoft Graph

| Contrainte | Détail |
|------------|--------|
| Pagination | Max 100 items/page |
| Rate limiting | Retry automatique avec Retry-After |
| Delta queries | Stocke deltaLink pour polling |
| Teams threads | Non supporté (limitation API) |

### Apple

| Contrainte | Détail |
|------------|--------|
| macOS only | AppleScript exclusif |
| Synchrone | Pas d'async possible |
| Timeout | 180s pour gros volumes |
| IDs opaques | `x-coredata://...` |

---

*Voir aussi* : [04-api.md](04-api.md) pour l'API REST.
