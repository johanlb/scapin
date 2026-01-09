# Spécification CrossSourceEngine

**Version** : 1.0
**Date** : 8 janvier 2026
**Statut** : ✅ IMPLÉMENTÉ — 112 tests, 8 adapters

---

## 1. Vue d'Ensemble

### 1.1 Objectif

Le CrossSourceEngine permet à Scapin d'interroger **toutes les sources d'information disponibles** pour :
1. Enrichir l'analyse des emails (ReasoningEngine)
2. Enrichir les révisions de notes (NoteReviewer)
3. Répondre aux questions en chat (DiscussionService)

### 1.2 Vision

> **"Le cerveau étendu"** — Scapin a accès à toute l'information disponible,
> comme si toutes les sources étaient un seul lac de données unifié.

### 1.3 Sources Supportées

| Source | Accès | Priorité |
|--------|-------|----------|
| **Emails archivés** | IMAP SEARCH | Phase 1 |
| **Calendrier** | Microsoft Graph API | Phase 1 |
| **Teams** | Microsoft Graph API | Phase 1 |
| **WhatsApp** | SQLite local (Desktop) | Phase 1 |
| **Fichiers locaux** | ripgrep | Phase 1 |
| **Web/Internet** | Tavily API | Phase 1 |
| **Notes** | Passepartout (existant) | Déjà intégré |

---

## 2. Architecture

### 2.1 Emplacement

```
src/passepartout/
├── context_engine.py          # Existant - utilise CrossSourceEngine
├── note_manager.py            # Existant
├── note_reviewer.py           # Existant - utilise CrossSourceEngine
└── cross_source/              # NOUVEAU
    ├── __init__.py
    ├── engine.py              # CrossSourceEngine principal
    ├── cache.py               # TTLCache 15 minutes
    ├── models.py              # CrossSourceResult, SourceResult, LinkedSource
    ├── config.py              # CrossSourceConfig
    └── adapters/
        ├── __init__.py
        ├── base.py            # SourceAdapter (Protocol)
        ├── email_adapter.py   # IMAP search dans archives
        ├── calendar_adapter.py # Graph API events
        ├── teams_adapter.py   # Graph API messages
        ├── whatsapp_adapter.py # SQLite local
        ├── files_adapter.py   # ripgrep
        └── web_adapter.py     # Tavily API
```

### 2.2 Diagramme de flux

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CrossSourceEngine                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  search(query, preferred_sources?, context?)                        │
│      │                                                               │
│      ▼                                                               │
│  ┌─────────────┐                                                    │
│  │ Check Cache │ ─── HIT ───▶ Return cached results                │
│  └──────┬──────┘                                                    │
│         │ MISS                                                       │
│         ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Parallel Adapter Execution                       │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │   │
│  │  │ Email  │ │Calendar│ │ Teams  │ │WhatsApp│ │ Files  │    │   │
│  │  │Adapter │ │Adapter │ │Adapter │ │Adapter │ │Adapter │    │   │
│  │  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘    │   │
│  │      │          │          │          │          │          │   │
│  │      └──────────┴──────────┴──────────┴──────────┘          │   │
│  │                           │                                   │   │
│  │                  asyncio.gather()                            │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Result Aggregator                          │   │
│  │  - Score par source (pondération)                            │   │
│  │  - Score par fraîcheur                                       │   │
│  │  - Déduplication                                              │   │
│  │  - Limite 50 résultats                                       │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────┐                                                    │
│  │ Store Cache │ (TTL: 15 min)                                     │
│  └─────────────┘                                                    │
│                              │                                       │
│                              ▼                                       │
│                     CrossSourceResult                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Mode Asynchrone

Toutes les recherches s'exécutent en **parallèle** avec `asyncio.gather()` :

```python
async def search(self, query: str, ...) -> CrossSourceResult:
    tasks = [
        self._search_with_timeout(adapter, query, timeout=10.0)
        for adapter in self.enabled_adapters
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return self._aggregate_results(results)
```

**Timeout par adapter** : 10 secondes max. Si un adapter échoue ou timeout, les autres retournent quand même leurs résultats (mode dégradé).

---

## 3. Modèles de Données

### 3.1 CrossSourceResult

```python
@dataclass
class CrossSourceResult:
    """Résultat agrégé d'une recherche cross-source"""

    query: str
    items: list[SourceItem]           # Résultats triés par score
    sources_searched: list[str]       # ["email", "calendar", "teams", ...]
    sources_failed: list[str]         # Sources en erreur/timeout
    total_results: int
    search_duration_ms: int
    from_cache: bool

@dataclass
class SourceItem:
    """Un résultat individuel d'une source"""

    source: str                       # "email", "calendar", "teams", etc.
    type: str                         # "message", "event", "file", etc.
    title: str                        # Sujet email, nom fichier, etc.
    content: str                      # Extrait du contenu (max 500 chars)
    url: str | None                   # Lien vers l'item si applicable
    timestamp: datetime               # Date de l'item
    relevance_score: float            # 0.0 - 1.0 (après pondération)
    metadata: dict[str, Any]          # Données spécifiques à la source
```

### 3.2 LinkedSource (pour notes)

```python
@dataclass
class LinkedSource:
    """Source liée à une note (définie dans frontmatter)"""

    type: str                         # "folder", "whatsapp", "email", "teams"
    identifier: str                   # Path, contact name, filter, chat name
    priority: int = 1                 # 1 = haute, 2 = moyenne, 3 = basse

# Exemple depuis frontmatter YAML:
# linked_sources:
#   - type: folder
#     path: ~/Documents/Projets/Anahita
#   - type: whatsapp
#     contact: "Équipe Anahita"
```

### 3.3 CrossSourceRequest (pour l'IA)

```python
@dataclass
class CrossSourceRequest:
    """Requête de recherche cross-source (peut venir de l'IA)"""

    query: str
    preferred_sources: list[str] | None = None  # Sources prioritaires
    exclude_sources: list[str] | None = None    # Sources à exclure
    include_web: bool = False                    # Recherche web explicite
    max_results: int = 50
    context_note_id: str | None = None          # Note de contexte (pour linked_sources)
```

---

## 4. Configuration

### 4.1 Paramètres

```python
@dataclass
class CrossSourceConfig:
    """Configuration du CrossSourceEngine"""

    # Général
    enabled: bool = True
    cache_ttl_seconds: int = 900              # 15 minutes
    max_results_per_source: int = 20
    max_total_results: int = 50
    adapter_timeout_seconds: float = 10.0

    # Déclenchement automatique
    auto_trigger_confidence_threshold: float = 0.75  # Si confiance < 75%

    # Scoring
    source_weights: dict[str, float] = field(default_factory=lambda: {
        "email": 1.0,
        "calendar": 1.0,
        "teams": 0.9,
        "whatsapp": 0.9,
        "files": 0.8,
        "web": 0.6,
    })
    freshness_decay_days: int = 30            # Pénalité pour items > 30 jours

    # Sources
    email: EmailAdapterConfig = field(default_factory=EmailAdapterConfig)
    calendar: CalendarAdapterConfig = field(default_factory=CalendarAdapterConfig)
    teams: TeamsAdapterConfig = field(default_factory=TeamsAdapterConfig)
    whatsapp: WhatsAppAdapterConfig = field(default_factory=WhatsAppAdapterConfig)
    files: FilesAdapterConfig = field(default_factory=FilesAdapterConfig)
    web: WebAdapterConfig = field(default_factory=WebAdapterConfig)
```

### 4.2 Configuration par Adapter

```python
@dataclass
class EmailAdapterConfig:
    search_body: bool = True                  # Chercher dans le corps
    date_range_days: int | None = None        # Illimité
    max_results: int = 20

@dataclass
class CalendarAdapterConfig:
    past_days: int = 365                      # 1 an en arrière
    future_days: int = 90                     # 3 mois en avant
    include_description: bool = True
    max_results: int = 20

@dataclass
class TeamsAdapterConfig:
    include_all_chats: bool = True
    include_files: bool = True
    max_results: int = 20

@dataclass
class WhatsAppAdapterConfig:
    db_path: Path = Path("~/Library/Containers/net.whatsapp.WhatsApp/Data/Library/Application Support/WhatsApp/Media/ChatStorage.sqlite")
    max_results: int = 20

@dataclass
class FilesAdapterConfig:
    default_paths: list[Path] = field(default_factory=lambda: [
        Path("~/Documents"),
    ])
    extensions_tier1: list[str] = field(default_factory=lambda: [
        ".md", ".txt", ".json", ".yaml", ".yml"
    ])
    extensions_tier2: list[str] = field(default_factory=lambda: [
        ".pdf", ".docx", ".xlsx", ".pptx"
    ])
    max_file_size_mb: int = 10
    max_results: int = 20

@dataclass
class WebAdapterConfig:
    provider: str = "tavily"
    api_key: str = ""                         # Via env: TAVILY_API_KEY
    trigger: str = "on_request"               # "on_request" | "no_local" | "always"
    max_results: int = 10
```

---

## 5. Adapters

### 5.1 Interface Commune

```python
class SourceAdapter(Protocol):
    """Protocol pour tous les adapters de source"""

    @property
    def source_name(self) -> str:
        """Nom de la source (ex: 'email', 'calendar')"""
        ...

    @property
    def is_available(self) -> bool:
        """True si la source est configurée et accessible"""
        ...

    async def search(
        self,
        query: str,
        max_results: int = 20,
        context: dict[str, Any] | None = None,
    ) -> list[SourceItem]:
        """Recherche dans la source"""
        ...
```

### 5.2 Email Adapter

```python
class EmailAdapter(SourceAdapter):
    """Recherche dans les emails archivés via IMAP SEARCH"""

    source_name = "email"

    async def search(self, query: str, ...) -> list[SourceItem]:
        # IMAP SEARCH avec:
        # - OR (SUBJECT query) (BODY query) (FROM query)
        # - Pas de limite de date (illimité)
        # - Recherche dans le corps complet
```

### 5.3 Files Adapter

```python
class FilesAdapter(SourceAdapter):
    """Recherche dans les fichiers locaux via ripgrep"""

    source_name = "files"

    async def search(
        self,
        query: str,
        paths: list[Path] | None = None,  # Peut venir de linked_sources
        ...
    ) -> list[SourceItem]:
        # 1. Déterminer les chemins à chercher:
        #    - paths fournis (ex: depuis linked_sources de la note)
        #    - Sinon: default_paths (~/Documents)
        # 2. ripgrep avec extensions Tier1 + Tier2
        # 3. Pour PDF: extraction texte avec pdfplumber/pymupdf
```

### 5.4 WhatsApp Adapter

```python
class WhatsAppAdapter(SourceAdapter):
    """Recherche dans WhatsApp Desktop via SQLite"""

    source_name = "whatsapp"

    # Base de données WhatsApp Desktop macOS:
    # ~/Library/Containers/net.whatsapp.WhatsApp/Data/Library/Application Support/WhatsApp/ChatStorage.sqlite

    async def search(
        self,
        query: str,
        contact: str | None = None,  # Filtrer par contact (depuis linked_sources)
        ...
    ) -> list[SourceItem]:
        # SELECT * FROM ZWAMESSAGE WHERE ZTEXT LIKE '%query%'
        # JOIN avec ZWACHATSESSION pour le nom du contact
```

### 5.5 Web Adapter

```python
class WebAdapter(SourceAdapter):
    """Recherche sur Internet via Tavily"""

    source_name = "web"

    async def search(self, query: str, ...) -> list[SourceItem]:
        # Tavily API:
        # - Optimisé pour agents IA
        # - Retourne résumés structurés
        # - $0.01/recherche
```

---

## 6. Intégration Pipeline

### 6.1 ReasoningEngine (Pass 2+)

```python
# Dans src/sancho/reasoning_engine.py

async def _pass2_context_enrichment(self, wm: WorkingMemory) -> None:
    # Contexte existant (notes)
    context_items = await self.context_engine.retrieve_context(wm.event)

    # Cross-source automatique si confiance < 75%
    if wm.overall_confidence < self.cross_source_threshold:
        cross_source_result = await self.cross_source_engine.search(
            query=self._build_query(wm.event),
            context_note_id=self._find_related_note(wm.event),
        )
        context_items.extend(cross_source_result.items)

    # Ou si l'IA demande explicitement dans Pass 1
    if wm.ai_requested_cross_source:
        cross_source_result = await self.cross_source_engine.search(
            query=wm.ai_cross_source_query,
            preferred_sources=wm.ai_preferred_sources,
            include_web=wm.ai_requested_web,
        )
        context_items.extend(cross_source_result.items)
```

### 6.2 NoteReviewer

```python
# Dans src/passepartout/note_reviewer.py

async def _collect_review_context(self, note: Note) -> ReviewContext:
    # Extraire linked_sources du frontmatter
    linked_sources = self._parse_linked_sources(note.frontmatter)

    # Recherche cross-source ciblée
    cross_source_result = await self.cross_source_engine.search(
        query=note.title,
        preferred_sources=[ls.type for ls in linked_sources],
        context_note_id=note.id,
    )

    return ReviewContext(
        note=note,
        cross_source_items=cross_source_result.items,
        ...
    )
```

### 6.3 Format Prompt IA

```python
# L'IA peut demander une recherche cross-source dans sa réponse JSON:
{
    "analysis": { ... },
    "cross_source_request": {
        "needed": true,
        "query": "budget projet désalinisation Anahita 2026",
        "preferred_sources": ["files", "whatsapp"],
        "include_web": false,
        "reason": "Besoin de plus de contexte sur le budget actuel"
    }
}
```

---

## 7. Sources Liées aux Notes (linked_sources)

### 7.1 Format Frontmatter

```yaml
---
title: Projet Désalinisation Anahita
type: projet
tags: [anahita, eau, environnement]

linked_sources:
  - type: folder
    path: ~/Documents/Projets/Anahita
    priority: 1
  - type: whatsapp
    contact: "Équipe Anahita"
    priority: 1
  - type: email
    filter: "from:@anahita.com OR subject:désalinisation"
    priority: 2
  - type: teams
    chat: "Projet Anahita"
    priority: 2
---

# Projet Désalinisation Anahita

...contenu de la note...
```

### 7.2 Utilisation

1. **Recherche ciblée** : Quand on recherche "Anahita budget", le CrossSourceEngine priorise les sources liées
2. **Révision intelligente** : Le NoteReviewer cherche d'abord dans les sources liées
3. **Suggestions** : Scapin propose d'ajouter des sources quand il détecte des patterns récurrents

### 7.3 Extraction

```python
def parse_linked_sources(frontmatter: dict) -> list[LinkedSource]:
    """Parse linked_sources depuis le frontmatter YAML"""
    sources = []
    for item in frontmatter.get("linked_sources", []):
        sources.append(LinkedSource(
            type=item["type"],
            identifier=item.get("path") or item.get("contact") or item.get("filter") or item.get("chat"),
            priority=item.get("priority", 2),
        ))
    return sources
```

---

## 8. Scoring & Agrégation

### 8.1 Calcul du Score

```python
def calculate_score(item: SourceItem, config: CrossSourceConfig) -> float:
    """Calcule le score final d'un item"""

    # Score de base par source
    source_weight = config.source_weights.get(item.source, 0.5)

    # Pénalité fraîcheur (items vieux = moins pertinents)
    days_old = (datetime.now() - item.timestamp).days
    freshness_factor = max(0.5, 1.0 - (days_old / config.freshness_decay_days) * 0.5)

    # Score combiné
    return item.relevance_score * source_weight * freshness_factor
```

### 8.2 Agrégation

```python
def aggregate_results(results: list[list[SourceItem]], config: CrossSourceConfig) -> list[SourceItem]:
    """Agrège et trie les résultats de toutes les sources"""

    all_items = []
    for source_results in results:
        all_items.extend(source_results)

    # Calculer scores finaux
    for item in all_items:
        item.final_score = calculate_score(item, config)

    # Trier par score décroissant
    all_items.sort(key=lambda x: x.final_score, reverse=True)

    # Déduplication (même contenu de sources différentes)
    deduplicated = deduplicate(all_items)

    # Limiter
    return deduplicated[:config.max_total_results]
```

---

## 9. Cache

### 9.1 Implémentation

```python
from cachetools import TTLCache

class CrossSourceCache:
    """Cache TTL pour les résultats de recherche"""

    def __init__(self, ttl_seconds: int = 900, max_size: int = 100):
        self._cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)

    def _make_key(self, query: str, sources: list[str]) -> str:
        """Génère une clé de cache"""
        sources_str = ",".join(sorted(sources))
        return f"{query.lower().strip()}|{sources_str}"

    def get(self, query: str, sources: list[str]) -> CrossSourceResult | None:
        key = self._make_key(query, sources)
        return self._cache.get(key)

    def set(self, query: str, sources: list[str], result: CrossSourceResult) -> None:
        key = self._make_key(query, sources)
        self._cache[key] = result
```

### 9.2 Paramètres

- **TTL** : 15 minutes (900 secondes)
- **Max entries** : 100
- **Invalidation** : Automatique par TTL, pas d'invalidation manuelle

---

## 10. Sécurité & Exclusions

### 10.1 Dossiers Exclus (Files Adapter)

```python
EXCLUDED_PATHS = [
    ".ssh",
    ".gnupg",
    ".aws",
    ".config/gcloud",
    "credentials",
    "secrets",
    ".env",
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
]

EXCLUDED_PATTERNS = [
    "*password*",
    "*secret*",
    "*credential*",
    "*.key",
    "*.pem",
    "*.p12",
    "id_rsa*",
    "id_ed25519*",
]
```

### 10.2 Pas de Persistance Web

Les résultats de recherche web ne sont **jamais** persistés sur disque. Cache mémoire uniquement (15 min).

---

## 11. API REST

### 11.1 Endpoint

```
POST /api/search/cross-source
```

### 11.2 Request

```json
{
    "query": "budget projet désalinisation",
    "preferred_sources": ["files", "whatsapp"],
    "exclude_sources": ["web"],
    "include_web": false,
    "max_results": 30,
    "context_note_id": "projet-desalinisation-anahita"
}
```

### 11.3 Response

```json
{
    "success": true,
    "data": {
        "query": "budget projet désalinisation",
        "items": [
            {
                "source": "files",
                "type": "document",
                "title": "Budget_Anahita_2026.xlsx",
                "content": "Budget prévisionnel: 2.5M€...",
                "url": "file:///Users/johan/Documents/Projets/Anahita/Budget_Anahita_2026.xlsx",
                "timestamp": "2026-01-05T10:30:00Z",
                "relevance_score": 0.95,
                "metadata": {
                    "file_size": 45000,
                    "extension": ".xlsx"
                }
            },
            ...
        ],
        "sources_searched": ["email", "calendar", "teams", "whatsapp", "files"],
        "sources_failed": [],
        "total_results": 23,
        "search_duration_ms": 2340,
        "from_cache": false
    }
}
```

---

## 12. UI

### 12.1 Affichage Sources Consultées

Dans l'UI (page Flux, page Notes), afficher les sources consultées :

```
┌────────────────────────────────────────────────────────┐
│ 📧 Email analysé: "Re: Budget Anahita Q1"             │
│                                                        │
│ 🔍 Sources consultées:                                │
│    ✅ emails (5 résultats)                            │
│    ✅ calendar (2 résultats)                          │
│    ✅ whatsapp (3 résultats)                          │
│    ✅ files (8 résultats)                             │
│    ⏭️ web (non demandé)                               │
│                                                        │
│ Confiance: 94% (enrichi par contexte)                 │
└────────────────────────────────────────────────────────┘
```

### 12.2 Configuration via Settings

L'utilisateur peut voir le statut des sources dans Settings, mais **pas les activer/désactiver individuellement** (décision utilisateur).

---

## 13. Ordre d'Implémentation

### Phase 1 : Core + Email (Sprint Cross-Source début)

1. `models.py` — Modèles de données
2. `config.py` — Configuration
3. `cache.py` — Cache TTL
4. `base.py` — Protocol SourceAdapter
5. `email_adapter.py` — Premier adapter (IMAP)
6. `engine.py` — CrossSourceEngine avec agrégation
7. Tests unitaires
8. Intégration ReasoningEngine (Pass 2)

### Phase 2 : Sources Microsoft (suite)

9. `calendar_adapter.py` — Graph API
10. `teams_adapter.py` — Graph API
11. Tests unitaires

### Phase 3 : Nouvelles Sources

12. `whatsapp_adapter.py` — SQLite local
13. `files_adapter.py` — ripgrep
14. `web_adapter.py` — Tavily
15. Tests unitaires

### Phase 4 : Intégration Complète

16. Intégration NoteReviewer
17. API REST endpoint
18. UI affichage sources
19. linked_sources dans notes
20. Tests E2E

---

## 14. Dépendances

### Python

```toml
# pyproject.toml
[project.dependencies]
tavily-python = "^0.3.0"      # Web search
cachetools = "^5.3.0"         # TTL Cache
pdfplumber = "^0.10.0"        # PDF text extraction (optionnel, pour files)
```

### Existantes (déjà installées)

- `httpx` — Pour Tavily API
- `aiosqlite` — Pour WhatsApp SQLite

---

## 15. Métriques de Succès

| Métrique | Cible |
|----------|-------|
| Temps de recherche moyen | < 3 secondes |
| Cache hit rate | > 30% |
| Sources disponibles | 6/6 |
| Taux d'erreur adapters | < 5% |
| Amélioration confiance analyse | +10-15% |

---

## Historique

| Date | Version | Changement |
|------|---------|------------|
| 2026-01-08 | 1.0 | Création initiale, approuvé |
