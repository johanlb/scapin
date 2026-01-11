# Documentation Technique SCAPIN

**Version** : 1.0.0-RC
**Dernière mise à jour** : 11 janvier 2026
**Public cible** : IA (Claude, assistants de code)

---

## Vue d'Ensemble

SCAPIN est un **gardien cognitif personnel** avec une architecture inspirée du raisonnement humain. Il transforme le flux d'emails et d'informations en connaissances organisées via une analyse IA multi-passes, une mémoire contextuelle et une planification d'actions intelligente.

**Mission fondamentale** : *"Prendre soin de Johan mieux que Johan lui-même."*

---

## Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCAPIN ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   SOURCES   │    │   TRIVELIN  │    │   SANCHO    │    │ PASSEPARTOUT│  │
│  │             │───▶│ Perception  │───▶│ Raisonnement│◀──▶│  Contexte   │  │
│  │ Email/Teams │    │   Triage    │    │  5-passes   │    │    Notes    │  │
│  │  Calendar   │    └─────────────┘    └──────┬──────┘    └─────────────┘  │
│  └─────────────┘                              │                             │
│                                               ▼                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   JEEVES    │◀───│   FIGARO    │◀───│  PLANCHET   │    │ SGANARELLE  │  │
│  │  API/CLI    │    │ Orchestration│    │ Planification│───▶│Apprentissage│  │
│  │  Frontend   │    │   Actions   │    │   Risques   │    │  Patterns   │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Table des Matières

| Document | Description | Lignes de code |
|----------|-------------|----------------|
| [01-core.md](01-core.md) | Événements universels, mémoire de travail, configuration | ~8,500 |
| [02-valets.md](02-valets.md) | Les 7 valets (Trivelin, Sancho, Passepartout, etc.) | ~15,000 |
| [03-integrations.md](03-integrations.md) | Email IMAP, Microsoft Graph, Apple Notes | ~7,800 |
| [04-api.md](04-api.md) | API REST FastAPI, endpoints, WebSocket | ~6,000 |
| [05-web.md](05-web.md) | Frontend SvelteKit, stores, composants | ~12,000 |
| [06-data-models.md](06-data-models.md) | 120+ modèles Pydantic/dataclasses | — |
| [07-flows.md](07-flows.md) | Flux de données bout-en-bout | — |

---

## Cartographie des Fichiers

### Structure du Projet

```
scapin/
├── src/
│   ├── core/                    # Fondations (events, memory, config)
│   │   ├── events/              # PerceivedEvent, normalizers
│   │   ├── memory/              # WorkingMemory, continuity
│   │   ├── extractors/          # Entity extraction
│   │   ├── config_manager.py    # Configuration Pydantic
│   │   ├── schemas.py           # Schémas partagés
│   │   ├── exceptions.py        # Exceptions custom
│   │   ├── interfaces.py        # Contrats abstraits
│   │   └── processing_events.py # Event bus pub/sub
│   │
│   ├── trivelin/                # Perception & triage
│   │   ├── processor.py         # EmailProcessor principal
│   │   ├── cognitive_pipeline.py# Orchestrateur multi-pass
│   │   ├── teams_processor.py   # Processeur Teams
│   │   ├── calendar_processor.py# Processeur Calendar
│   │   └── action_factory.py    # Factory actions
│   │
│   ├── sancho/                  # Raisonnement IA
│   │   ├── reasoning_engine.py  # Moteur 5-passes
│   │   ├── router.py            # Routeur IA + JSON repair
│   │   ├── model_selector.py    # Sélection modèle
│   │   ├── templates.py         # Templates Jinja2
│   │   └── providers/           # Anthropic, OpenAI
│   │
│   ├── passepartout/            # Base de connaissances
│   │   ├── note_manager.py      # CRUD notes + cache
│   │   ├── context_engine.py    # Récupération contexte
│   │   ├── vector_store.py      # Stockage vecteurs
│   │   ├── embeddings.py        # Sentence-transformers
│   │   ├── note_metadata.py     # SM-2 spaced repetition
│   │   ├── note_types.py        # Classification notes
│   │   ├── git_versioning.py    # Versioning Git
│   │   └── cross_source/        # Recherche multi-source
│   │       ├── engine.py        # Orchestrateur
│   │       └── adapters/        # Email, Teams, Web, etc.
│   │
│   ├── planchet/                # Planification
│   │   └── planning_engine.py   # Risk assessment + DAG
│   │
│   ├── figaro/                  # Exécution
│   │   ├── orchestrator.py      # DAG orchestrator
│   │   └── actions/             # Actions concrètes
│   │       ├── base.py          # Classe abstraite
│   │       ├── email.py         # Archive, Draft, Flag
│   │       ├── teams.py         # Reply, Flag
│   │       ├── calendar.py      # RSVP, Create
│   │       └── notes.py         # Create, Update
│   │
│   ├── sganarelle/              # Apprentissage
│   │   ├── learning_engine.py   # Orchestrateur
│   │   ├── feedback_processor.py# Analyse feedback
│   │   ├── pattern_store.py     # Patterns appris
│   │   ├── provider_tracker.py  # Quality tracking
│   │   └── confidence_calibrator.py # Calibration
│   │
│   ├── jeeves/                  # Interface
│   │   ├── cli.py               # Typer CLI
│   │   ├── display_manager.py   # Rich rendering
│   │   ├── api/                 # FastAPI
│   │   │   ├── app.py           # Application factory
│   │   │   ├── deps.py          # Dependency injection
│   │   │   ├── auth/            # JWT + rate limiting
│   │   │   ├── routers/         # 13 routers
│   │   │   ├── services/        # 8 services
│   │   │   ├── models/          # Request/Response
│   │   │   └── websocket/       # Real-time
│   │   ├── journal/             # Journaling
│   │   └── briefing/            # Briefings
│   │
│   └── integrations/            # Systèmes externes
│       ├── email/               # IMAP client
│       ├── microsoft/           # Teams, Calendar, Graph
│       ├── apple/               # Notes, OmniFocus
│       └── storage/             # JSON persistence
│
├── web/                         # Frontend SvelteKit
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/             # Client API TypeScript
│   │   │   ├── components/      # 90+ composants Svelte
│   │   │   ├── stores/          # Stores réactifs Svelte 5
│   │   │   └── utils/           # Formatters, shortcuts
│   │   └── routes/              # Pages (file-based routing)
│   └── static/                  # PWA (manifest, sw.js)
│
├── tests/                       # 1824+ tests
├── docs/                        # Documentation
└── config/                      # Configuration YAML
```

---

## Statistiques du Projet

| Métrique | Valeur |
|----------|--------|
| **Lignes de code Python** | ~50,000 |
| **Lignes de code TypeScript/Svelte** | ~15,000 |
| **Fichiers Python** | ~150 |
| **Fichiers Frontend** | ~100 |
| **Tests** | 1,824+ |
| **Couverture** | 95% |
| **Modèles de données** | 120+ |
| **Endpoints API** | 60+ |

---

## Dépendances Principales

### Backend (Python 3.11+)

| Catégorie | Packages |
|-----------|----------|
| **Web** | FastAPI, Uvicorn, Pydantic |
| **IA** | Anthropic, sentence-transformers, numpy |
| **Email** | imaplib (stdlib) |
| **Microsoft** | msgraph-core, azure-identity, msal |
| **Storage** | SQLite, gitpython |
| **CLI** | Typer, Rich |
| **Tests** | pytest, pytest-asyncio |

### Frontend (Node 20+)

| Catégorie | Packages |
|-----------|----------|
| **Framework** | Svelte 5, SvelteKit 2 |
| **Build** | Vite 7 |
| **Styling** | TailwindCSS 4 |
| **Tests** | Playwright, Vitest |
| **Markdown** | marked, isomorphic-dompurify |

---

## Principes Architecturaux

### 1. Immutabilité des Événements

```python
@dataclass(frozen=True)
class PerceivedEvent:
    """Frozen = immuable après création"""
```

Les événements sont **gelés** pour empêcher toute modification accidentelle pendant le traitement concurrent.

### 2. Validation à la Construction

```python
def __post_init__(self):
    if not (0.0 <= self.confidence <= 1.0):
        raise ValueError("Invalid confidence")
```

Échec rapide : validation dès la construction pour éviter les états invalides.

### 3. Thread-Safety via Singletons

```python
_lock = threading.Lock()

@classmethod
def load(cls):
    if cls._instance is None:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
    return cls._instance
```

Double-check locking pour initialisation thread-safe.

### 4. Injection de Dépendances

```python
@lru_cache
def get_notes_service() -> NotesService:
    return NotesService(get_cached_config())
```

Caching singleton pour éviter re-création coûteuse.

### 5. Extensibilité via Metadata

```python
metadata: dict[str, Any]  # Données source-spécifiques
```

Dictionnaire flexible pour données futures sans changer le schéma.

---

## Flux Principal

```
1. ENTRÉE
   ┌──────────────────────────────────────────────────────┐
   │ Email IMAP / Teams Graph API / Calendar / Question   │
   └──────────────────────────────────────────────────────┘
                              │
                              ▼
2. PERCEPTION (Trivelin)
   ┌──────────────────────────────────────────────────────┐
   │ Normalisation → PerceivedEvent (immutable, validé)   │
   └──────────────────────────────────────────────────────┘
                              │
                              ▼
3. RAISONNEMENT (Sancho) - 5 Passes
   ┌──────────────────────────────────────────────────────┐
   │ Pass 1: Analyse initiale (~60-70% confiance)        │
   │ Pass 2: Enrichissement contexte (Passepartout)      │
   │ Pass 3: Raisonnement profond                        │
   │ Pass 4: Validation patterns (Sganarelle)            │
   │ Pass 5: Clarification utilisateur (si nécessaire)   │
   └──────────────────────────────────────────────────────┘
                              │
                              ▼
4. PLANIFICATION (Planchet)
   ┌──────────────────────────────────────────────────────┐
   │ WorkingMemory → ActionPlan (DAG + évaluation risques)│
   └──────────────────────────────────────────────────────┘
                              │
                              ▼
5. EXÉCUTION (Figaro)
   ┌──────────────────────────────────────────────────────┐
   │ Résolution DAG → Exécution parallèle → Rollback     │
   └──────────────────────────────────────────────────────┘
                              │
                              ▼
6. APPRENTISSAGE (Sganarelle)
   ┌──────────────────────────────────────────────────────┐
   │ Feedback → Patterns → Calibration → Knowledge Base  │
   └──────────────────────────────────────────────────────┘
                              │
                              ▼
7. INTERFACE (Jeeves)
   ┌──────────────────────────────────────────────────────┐
   │ CLI / API REST / WebSocket / Frontend SvelteKit     │
   └──────────────────────────────────────────────────────┘
```

---

## Glossaire

| Terme | Définition |
|-------|------------|
| **PerceivedEvent** | Représentation universelle et immuable de tout événement |
| **WorkingMemory** | État cognitif transitoire pendant le traitement |
| **Hypothesis** | Supposition sur l'action appropriée avec confiance |
| **ReasoningPass** | Une itération du raisonnement multi-pass |
| **ActionPlan** | Plan d'exécution avec ordre topologique et risques |
| **Pattern** | Comportement récurrent appris pour suggestion future |
| **SM-2** | Algorithme Supermemo 2 pour révision espacée |
| **DAG** | Directed Acyclic Graph pour dépendances d'actions |

---

## Navigation Rapide

- **Comprendre les événements** → [01-core.md](01-core.md)
- **Comprendre le raisonnement** → [02-valets.md](02-valets.md) § Sancho
- **Ajouter une intégration** → [03-integrations.md](03-integrations.md)
- **Créer un endpoint API** → [04-api.md](04-api.md)
- **Modifier le frontend** → [05-web.md](05-web.md)
- **Comprendre un modèle** → [06-data-models.md](06-data-models.md)
- **Suivre un flux** → [07-flows.md](07-flows.md)

---

## Prochaines Étapes

Pour une IA travaillant sur ce projet :

1. **Lire le fichier pertinent** selon la tâche
2. **Vérifier les dépendances** avant modification
3. **Respecter les patterns** (immutabilité, validation, etc.)
4. **Exécuter les tests** après modification
5. **Mettre à jour la doc** si nécessaire

---

*Documentation générée le 11 janvier 2026*
