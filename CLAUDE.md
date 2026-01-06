# CLAUDE.md — Contexte de Session & État du Projet

**Dernière mise à jour** : 6 janvier 2026
**Projet** : Scapin (anciennement PKM System)  
**Dépôt** : https://github.com/johanlb/scapin  
**Répertoire de travail** : `/Users/johan/Developer/scapin`

---

## 🎯 Démarrage Rapide

### Qu'est-ce que Scapin ?

Scapin est un **gardien cognitif personnel** avec une architecture cognitive inspirée du raisonnement humain. Il transforme le flux d'emails et d'informations en connaissances organisées via une analyse IA multi-passes, une mémoire contextuelle et une planification d'actions intelligente.

**Mission fondamentale** : *"Prendre soin de Johan mieux que Johan lui-même."*

**Tension centrale résolue** : Scapin est simultanément un **déchargeur cognitif** (micro-tâches, contexte factuel) ET un **sparring partner intellectuel** (débat, exploration, challenge). Ces deux rôles libèrent de la bande passante cognitive pour l'essentiel.

---

## 📚 Documents de Référence

### Hiérarchie Documentaire

| Document | Rôle | Quand consulter |
|----------|------|-----------------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | 🎯 **Document fondateur** — Le *pourquoi* | Toujours, pour comprendre l'âme du projet |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Le *comment* technique | Implémentation des modules |
| **[ROADMAP.md](ROADMAP.md)** | Le *quand* | Priorisation des tâches |
| **[UI_VOCABULARY.md](docs/UI_VOCABULARY.md)** | 🎭 **Vocabulaire UI** — Mapping termes UI ↔ technique | Traitement requêtes utilisateur, génération réponses |
| **Ce fichier (CLAUDE.md)** | État actuel | Démarrage de session |

### Les 5 Principes Directeurs

Ces principes guident TOUTES les décisions de développement :

| # | Principe | Implication |
|---|----------|-------------|
| **1** | **Qualité sur vitesse** | 10-20s de raisonnement pour la BONNE décision |
| **2** | **Proactivité maximale** | Anticiper, suggérer, challenger, rappeler — sans attendre |
| **3** | **Intimité totale** | Aucune limite d'accès pour l'efficacité |
| **4** | **Apprentissage progressif** | Seuils de confiance appris, pas de règles rigides |
| **5** | **Construction propre** | Lent mais bien construit dès le début |

### Information en 3 Couches

| Niveau | Contenu | Temps | Usage |
|--------|---------|-------|-------|
| **1** | Résumé actionnable | 30s | Décision rapide, briefing |
| **2** | Contexte et options | 2 min | Compréhension, choix informé |
| **3** | Détails complets | Variable | Auto-alimentation Scapin, audit |

📖 *Référence complète : [DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)*

---

## 🏗️ Architecture Cognitive

### Vue d'Ensemble

```
Boucle Cognitive :
┌─────────────────────────────────────────────────────────┐
│  Entrée (Email/Fichier/Question)                        │
│    ↓                                                     │
│  PerceivedEvent (Normalisation universelle)             │
│    ↓                                                     │
│  Sancho (Raisonnement 5 passes, convergence confiance)  │
│    ↓                                                     │
│  Passepartout (Récupération contexte & connaissances)   │
│    ↓                                                     │
│  Planchet (Planification & évaluation risques)          │
│    ↓                                                     │
│  Figaro (Exécution actions, orchestration DAG)          │
│    ↓                                                     │
│  Sganarelle (Apprentissage feedback & résultats)        │
│    ↓                                                     │
│  WorkingMemory mise à jour → Boucle continue            │
└─────────────────────────────────────────────────────────┘
```

### L'Équipe des Valets

| Valet | Module | Responsabilité |
|-------|--------|----------------|
| **Trivelin** | `src/trivelin/` | Perception & triage des événements |
| **Sancho** | `src/sancho/` | Raisonnement itératif 5 passes |
| **Passepartout** | `src/passepartout/` | Base de connaissances (Markdown + Git + FAISS) |
| **Planchet** | `src/planchet/` | Planification avec évaluation des risques |
| **Figaro** | `src/figaro/` | Orchestration DAG avec rollback |
| **Sganarelle** | `src/sganarelle/` | Apprentissage continu |
| **Jeeves** | `src/jeeves/` | Interface API (FastAPI + WebSockets) |

### Boucle d'Amélioration Continue

Le journaling quotidien (~15 min) est le cœur du système :

```
Journée vécue → Scapin pré-remplit → Johan complète/corrige
     ↓
Enrichissement fiches → Meilleure analyse → Suggestions pertinentes
     ↓
Feedback via prochain journaling → Amélioration système
```

---

## 📊 État Actuel (5 janvier 2026)

### Phases Complétées

| Phase | Nom | Statut | Lignes Code |
|-------|-----|--------|-------------|
| **0** | Fondations | ✅ | — |
| **1** | Intelligence Email | ✅ | — |
| **2** | Expérience Interactive | 80% 🚧 | — |
| **0.5** | Architecture Cognitive | ✅ | ~8000 lignes |
| **0.6** | Refactoring Valet | ✅ | ~5200 lignes migrées |
| **1.7** | Note Enrichment System | ✅ | ~2200 lignes |

### Modules Valets Implémentés

| Valet | Module | Lignes | Statut |
|-------|--------|--------|--------|
| **Sancho** | `router.py`, `model_selector.py`, `templates.py`, `reasoning_engine.py`, `providers/` | ~2650 | ✅ |
| **Passepartout** | `context_engine`, `embeddings`, `note_manager`, `vector_store`, `note_types`, `note_metadata`, `note_scheduler`, `note_reviewer`, `note_enricher`, `note_merger`, `background_worker` | ~4200 | ✅ |
| **Planchet** | `planning_engine.py` | ~400 | ✅ |
| **Figaro** | `orchestrator.py`, `actions/` | ~770 | ✅ |
| **Sganarelle** | 8 modules (learning, feedback, calibration, patterns, etc.) | ~4100 | ✅ |
| **Trivelin** | `processor.py` | ~740 | ✅ |
| **Jeeves** | `cli.py`, `display_manager.py`, `menu.py`, `review_mode.py` | ~2500 | ✅ |

### Phase 1.0 : Trivelin Email — Pipeline Cognitif ✅

**Statut** : COMPLÉTÉ (2 janvier 2026)

| Composant | Fichier | État |
|-----------|---------|------|
| ProcessingConfig | `src/core/config_manager.py` | ✅ |
| CognitivePipeline | `src/trivelin/cognitive_pipeline.py` | ✅ |
| ActionFactory | `src/trivelin/action_factory.py` | ✅ |
| Intégration Processor | `src/trivelin/processor.py` | ✅ |
| Tests unitaires | `tests/unit/test_cognitive_pipeline.py` | ✅ |

**Activation** : `PROCESSING__ENABLE_COGNITIVE_REASONING=true` (opt-in)

### Phase 1.1 : Journaling & Feedback Loop ✅

**Statut** : COMPLÉTÉ (2 janvier 2026)

| Module | Fichier | État |
|--------|---------|------|
| Models | `src/jeeves/journal/models.py` | ✅ |
| Generator | `src/jeeves/journal/generator.py` | ✅ |
| Interactive | `src/jeeves/journal/interactive.py` | ✅ |
| Feedback | `src/jeeves/journal/feedback.py` | ✅ |
| CLI Command | `scapin journal` | ✅ |
| Tests | 56 tests | ✅ |

**Commande** : `scapin journal [--date] [--interactive] [--output] [--format]`

### Phase 1.2 : Intégration Microsoft Teams ✅

**Statut** : COMPLÉTÉ (2 janvier 2026)

| Module | Fichier | État |
|--------|---------|------|
| Auth MSAL | `src/integrations/microsoft/auth.py` | ✅ |
| Graph Client | `src/integrations/microsoft/graph_client.py` | ✅ |
| Models | `src/integrations/microsoft/models.py` | ✅ |
| Teams Client | `src/integrations/microsoft/teams_client.py` | ✅ |
| Normalizer | `src/integrations/microsoft/teams_normalizer.py` | ✅ |
| Processor | `src/trivelin/teams_processor.py` | ✅ |
| Actions | `src/figaro/actions/teams.py` | ✅ |
| CLI Command | `scapin teams` | ✅ |
| Tests | 116 tests | ✅ |

**Commande** : `scapin teams [--poll] [--interactive] [--limit] [--since]`

### Phase 1.3 : Intégration Calendrier Microsoft ✅

**Statut** : COMPLÉTÉ (3 janvier 2026)

| Module | Fichier | État |
|--------|---------|------|
| Models | `src/integrations/microsoft/calendar_models.py` | ✅ |
| Client | `src/integrations/microsoft/calendar_client.py` | ✅ |
| Normalizer | `src/integrations/microsoft/calendar_normalizer.py` | ✅ |
| Processor | `src/trivelin/calendar_processor.py` | ✅ |
| Actions | `src/figaro/actions/calendar.py` | ✅ |
| CLI Command | `scapin calendar` | ✅ |
| Tests | 92 tests | ✅ |

**Commande** : `scapin calendar [--poll] [--briefing] [--hours] [--limit]`

**Configuration** :
```bash
CALENDAR__ENABLED=true
CALENDAR__POLL_INTERVAL_SECONDS=300
CALENDAR__DAYS_AHEAD=7
# Réutilise les credentials Teams (même client_id/tenant_id)
```

### Phase 1.4 : Système de Briefing ✅

**Statut** : COMPLÉTÉ (3 janvier 2026)

| Module | Fichier | État |
|--------|---------|------|
| Models | `src/jeeves/briefing/models.py` | ✅ |
| Generator | `src/jeeves/briefing/generator.py` | ✅ |
| Display | `src/jeeves/briefing/display.py` | ✅ |
| CLI Command | `scapin briefing` | ✅ |
| Tests | 58 tests | ✅ |

**Commande** : `scapin briefing [--morning/-m] [--meeting/-M <id>] [--hours/-H] [--output/-o] [--quiet/-q]`

**Configuration** :
```bash
BRIEFING__ENABLED=true
BRIEFING__MORNING_HOURS_BEHIND=12
BRIEFING__MORNING_HOURS_AHEAD=24
BRIEFING__PRE_MEETING_MINUTES_BEFORE=15
BRIEFING__SHOW_CONFIDENCE=true
```

### Phase 0.7 : API Jeeves (FastAPI) — MVP ✅

**Statut** : MVP COMPLÉTÉ (3 janvier 2026)

| Module | Fichier | État |
|--------|---------|------|
| App Factory | `src/jeeves/api/app.py` | ✅ |
| Response Models | `src/jeeves/api/models/responses.py` | ✅ |
| Common Models | `src/jeeves/api/models/common.py` | ✅ |
| Dependencies | `src/jeeves/api/deps.py` | ✅ |
| System Router | `src/jeeves/api/routers/system.py` | ✅ |
| Briefing Router | `src/jeeves/api/routers/briefing.py` | ✅ |
| Briefing Service | `src/jeeves/api/services/briefing_service.py` | ✅ |
| CLI Command | `scapin serve` | ✅ |
| Tests | 20 tests | ✅ |

**Commande** : `scapin serve [--host] [--port] [--reload]`

**Endpoints disponibles** :

| Groupe | Endpoint | Description |
|--------|----------|-------------|
| **System** | `GET /` | API info |
| | `GET /api/health` | Health check avec status composants |
| | `GET /api/status` | Status temps réel (état, tâche en cours, composants) |
| | `GET /api/stats` | Statistiques de traitement |
| | `GET /api/config` | Configuration (secrets masqués) |
| **Auth** | `POST /api/auth/login` | Login avec PIN |
| | `GET /api/auth/check` | Vérifier token |
| **Briefing** | `GET /api/briefing/morning` | Briefing du matin |
| | `GET /api/briefing/meeting/{id}` | Briefing pré-réunion |
| **Journal** | `GET /api/journal/{date}` | Obtenir entrée journal |
| | `GET /api/journal/list` | Lister entrées |
| | `POST /api/journal/answer` | Soumettre réponse |
| **Queue** | `GET /api/queue` | Lister items en attente |
| | `GET /api/queue/stats` | Statistiques queue |
| | `GET /api/queue/{id}` | Détails item |
| | `POST /api/queue/{id}/approve` | Approuver item |
| | `POST /api/queue/{id}/modify` | Modifier action |
| | `POST /api/queue/{id}/reject` | Rejeter item |
| | `DELETE /api/queue/{id}` | Supprimer item |
| **Email** | `GET /api/email/accounts` | Lister comptes |
| | `GET /api/email/stats` | Statistiques email |
| | `POST /api/email/process` | Traiter inbox |
| | `POST /api/email/analyze` | Analyser email |
| | `POST /api/email/execute` | Exécuter action |
| **Calendar** | `GET /api/calendar/events` | Lister événements |
| | `GET /api/calendar/events/{id}` | Détails événement |
| | `GET /api/calendar/today` | Événements du jour |
| | `POST /api/calendar/events/{id}/respond` | Répondre invitation |
| | `POST /api/calendar/poll` | Synchroniser calendrier |
| **Teams** | `GET /api/teams/chats` | Lister chats |
| | `GET /api/teams/chats/{id}/messages` | Messages d'un chat |
| | `POST /api/teams/chats/{chat_id}/messages/{msg_id}/reply` | Répondre message |
| | `POST /api/teams/chats/{chat_id}/messages/{msg_id}/flag` | Flaguer message |
| | `POST /api/teams/poll` | Synchroniser Teams |
| | `GET /api/teams/stats` | Statistiques Teams |
| **Notes** | `GET /api/notes/reviews/due` | Notes à réviser (SM-2) |
| | `GET /api/notes/reviews/stats` | Statistiques révision |
| | `GET /api/notes/reviews/workload` | Prévision charge |
| | `GET /api/notes/reviews/configs` | Configs par type |
| | `GET /api/notes/{id}/metadata` | Métadonnées SM-2 |
| | `POST /api/notes/{id}/review` | Enregistrer révision (0-5) |
| | `POST /api/notes/{id}/postpone` | Reporter révision |
| | `POST /api/notes/{id}/trigger` | Déclencher révision immédiate |

**Usage** :
```bash
scapin serve                    # Démarrer sur 0.0.0.0:8000
scapin serve --port 8080        # Port personnalisé
scapin serve --reload           # Mode dev avec auto-reload
```

**Documentation** : `http://localhost:8000/docs` (OpenAPI/Swagger)

### Phase 0.8 : Interface Web (SvelteKit) ✅

**Statut** : COMPLÉTÉ (4 janvier 2026)

| Module | Fichier | État |
|--------|---------|------|
| Setup SvelteKit + TailwindCSS v4 | `web/` | ✅ |
| Design System (Button, Card, Badge, Input) | `web/src/lib/components/ui/` | ✅ |
| Layout (Sidebar, MobileNav, ChatPanel) | `web/src/lib/components/layout/` | ✅ |
| Page Briefing (home) | `web/src/routes/+page.svelte` | ✅ |
| Page Flux | `web/src/routes/flux/+page.svelte` | ✅ |
| Page Notes (arbre dossiers, épinglées) | `web/src/routes/notes/+page.svelte` | ✅ |
| Page Discussions | `web/src/routes/discussions/+page.svelte` | ✅ |
| Page Journal | `web/src/routes/journal/+page.svelte` | ✅ |
| Page Stats | `web/src/routes/stats/+page.svelte` | ✅ |
| Page Settings | `web/src/routes/settings/+page.svelte` | ✅ |
| Recherche globale (Cmd+K) | `web/src/lib/components/ui/CommandPalette.svelte` | ✅ |
| Sync Apple Notes | `web/src/routes/notes/+page.svelte` | ✅ |
| PullToRefresh mobile | `web/src/lib/components/ui/PullToRefresh.svelte` | ✅ |
| SwipeableCard gestures | `web/src/lib/components/ui/SwipeableCard.svelte` | ✅ |
| Auth JWT (backend) | `src/jeeves/api/auth/` | ✅ |
| Auth JWT (frontend) | `web/src/lib/stores/auth.svelte.ts` | ✅ |
| Page Login | `web/src/routes/login/+page.svelte` | ✅ |
| WebSockets (backend) | `src/jeeves/api/websocket/` | ✅ |
| WebSockets (frontend) | `web/src/lib/stores/websocket.svelte.ts` | ✅ |

**Commandes** :
```bash
cd web && npm run dev     # Démarrer en mode développement
cd web && npm run build   # Build production
cd web && npm run check   # Vérifier les types
```

### Phase 0.9 : PWA Mobile ✅

**Statut** : COMPLÉTÉ (4 janvier 2026)

| Composant | Fichier | État |
|-----------|---------|------|
| Service Worker v0.9.0 | `web/static/sw.js` | ✅ |
| Notifications Store | `web/src/lib/stores/notifications.svelte.ts` | ✅ |
| Icônes PNG | `web/static/icons/` | ✅ |
| Manifest étendu | `web/static/manifest.json` | ✅ |
| Page Share | `web/src/routes/share/+page.svelte` | ✅ |
| Page Handle | `web/src/routes/handle/+page.svelte` | ✅ |

### Phase 1.6 : Journaling Complet Multi-Source ✅

**Statut** : COMPLÉTÉ (4 janvier 2026)

| Module | Fichier | État |
|--------|---------|------|
| Multi-source models | `src/jeeves/journal/models.py` | ✅ |
| Providers (Teams, Calendar, OmniFocus) | `src/jeeves/journal/providers/` | ✅ |
| Reviews (Weekly, Monthly) | `src/jeeves/journal/reviews.py` | ✅ |
| Calibration Sganarelle | `src/jeeves/journal/feedback.py` | ✅ |
| API Router Journal | `src/jeeves/api/routers/journal.py` | ✅ |
| Service Journal | `src/jeeves/api/services/journal_service.py` | ✅ |
| Frontend Journal | `web/src/routes/journal/+page.svelte` | ✅ |
| Tests | 38 nouveaux tests | ✅ |

**Fonctionnalités** :
- Journaling multi-source : Email, Teams, Calendar, OmniFocus
- Questions enrichies avec catégories pattern/preference/calibration
- Revues hebdomadaires et mensuelles avec détection de patterns
- Calibration par source avec tracking de précision
- API REST complète pour le journal
- Frontend avec tabs multi-sources et corrections inline

### Phases à venir

| Phase | Nom | Priorité | Focus |
|-------|-----|----------|-------|
| **2.5** | IA Multi-Provider | 🟢 BASSE | Consensus |

### Suite des Tests

**Global** : 1736 tests, 95% couverture, 100% pass rate

| Catégorie | Tests | Statut |
|-----------|-------|--------|
| Backend tests | 1736 | ✅ |
| Frontend tests | 8 | ✅ |
| Skipped | 53 | ⏭️ |

### Qualité du Code

**Score** : 10/10
**Ruff** : 0 warning (code parfait)

---

## 🔧 Détails Techniques

### Fichiers Clés

**Architecture Cognitive** :
```
src/core/events/universal_event.py    # PerceivedEvent, Entity, EventType
src/core/memory/working_memory.py     # WorkingMemory, Hypothesis, ReasoningPass
src/core/processing_events.py         # EventBus, ProcessingEvent
```

**Traitement Email** (Trivelin) :
```
src/trivelin/processor.py             # Logique principale
src/integrations/email/imap_client.py # Opérations IMAP
```

**Intégration Teams** (Microsoft Graph) :
```
src/integrations/microsoft/auth.py           # MSAL OAuth
src/integrations/microsoft/graph_client.py   # Client Graph API
src/integrations/microsoft/teams_client.py   # Client Teams
src/integrations/microsoft/models.py         # TeamsMessage, TeamsChat
src/integrations/microsoft/teams_normalizer.py # → PerceivedEvent
src/trivelin/teams_processor.py              # Orchestrateur
src/figaro/actions/teams.py                  # Actions reply/flag/task
```

**Intégration Calendrier** (Microsoft Graph) :
```
src/integrations/microsoft/calendar_models.py      # CalendarEvent, CalendarAttendee
src/integrations/microsoft/calendar_client.py      # Client Calendar API
src/integrations/microsoft/calendar_normalizer.py  # → PerceivedEvent
src/trivelin/calendar_processor.py                 # Orchestrateur
src/figaro/actions/calendar.py                     # Actions create/respond/block
```

**CLI** (Jeeves) :
```
src/jeeves/cli.py                     # Commandes Typer
src/jeeves/display_manager.py         # Rendu Rich
src/jeeves/menu.py                    # Menus interactifs
```

**API REST** (Jeeves) :
```
src/jeeves/api/app.py                 # FastAPI application factory
src/jeeves/api/deps.py                # Dependency injection
src/jeeves/api/models/responses.py    # Pydantic response models
src/jeeves/api/routers/system.py      # /api/health, /api/stats, /api/config
src/jeeves/api/routers/briefing.py    # /api/briefing/* endpoints
src/jeeves/api/routers/notes.py       # /api/notes/* endpoints (CRUD + review)
src/jeeves/api/services/briefing_service.py      # Async briefing service
src/jeeves/api/services/notes_review_service.py  # SM-2 review service
```

**AI** (Sancho) :
```
src/sancho/router.py                  # AI routing + rate limiting
src/sancho/reasoning_engine.py        # Multi-pass reasoning
src/sancho/model_selector.py          # Model selection
src/sancho/templates.py               # Prompt templates
```

**Apprentissage** (Sganarelle) :
```
src/sganarelle/learning_engine.py     # Apprentissage feedback
src/sganarelle/feedback_processor.py  # Analyse feedback
src/sganarelle/knowledge_updater.py   # Mises à jour PKM
```

### Configuration

**Variables d'environnement** (`.env`) :
```bash
# Email
EMAIL_ADDRESS=votre-email@exemple.com
EMAIL_PASSWORD=mot-de-passe-application
IMAP_SERVER=imap.gmail.com

# IA
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-3-5-haiku-20241022

# Stockage
STORAGE_DIR=./data
LOG_FILE=./logs/scapin.log
```

### Règles de Traitement

**Contraintes appliquées à tous les canaux** (Email, Teams, Calendar) :

| Règle | Valeur | Justification |
|-------|--------|---------------|
| **Limite par batch** | 20 items | Évite de surcharger le système et l'IA |
| **Ordre de traitement** | Plus anciens en premier | Gère le backlog chronologiquement |

Ces règles sont définies dans les constantes `DEFAULT_PROCESSING_LIMIT` de chaque processeur :
- `src/trivelin/processor.py` (Email)
- `src/trivelin/teams_processor.py` (Teams)
- `src/trivelin/calendar_processor.py` (Calendar)

### Commandes de Test

```bash
# Tous les tests
.venv/bin/pytest tests/ -v

# Par module
.venv/bin/pytest tests/unit/test_universal_event.py -v
.venv/bin/pytest tests/unit/test_sganarelle_*.py -v

# Couverture
.venv/bin/pytest tests/ --cov=src --cov-report=html
```

---

## 🗺️ Feuille de Route (Révisée selon DESIGN_PHILOSOPHY.md)

### Priorités Q1 2026

> **Principe** : Valeur fonctionnelle AVANT couches techniques

| Phase | Focus | Priorité |
|-------|-------|----------|
| **0.6** | Refactoring Valet & flux bout-en-bout | ✅ COMPLÉTÉ |
| **1.0** | Pipeline Cognitif Trivelin | ✅ COMPLÉTÉ |
| **1.1** | Journaling & Feedback Loop | ✅ COMPLÉTÉ |
| **1.2** | Intégration Teams | ✅ COMPLÉTÉ |
| **1.3** | Intégration Calendrier | ✅ COMPLÉTÉ |

### Priorités Q2 2026

| Phase | Focus | Priorité |
|-------|-------|----------|
| **1.4** | Système de Briefing | ✅ COMPLÉTÉ |
| **0.7** | API Jeeves (FastAPI) | ✅ MVP COMPLÉTÉ |

### Phases Ultérieures

| Phase | Focus |
|-------|-------|
| **0.8** | Interface Web (SvelteKit) |
| **0.9** | PWA Mobile |
| **2.5** | Multi-Provider IA (consensus) |

---

## 📝 Notes de Session

### Session 2026-01-06 (Suite 6) — Test Dependency Fix

**Focus** : Correction des tests en échec dus à des problèmes de configuration

**Problème** :
- 22 tests `TestFolderEndpoints` échouaient avec `ValidationError: email/ai Field required`
- Cause : Les tests utilisaient `patch.object(NotesService, ...)` mais la dépendance `get_notes_service` appelait `get_cached_config()` qui tentait de charger la vraie config

**Solution** :
1. ✅ Override `get_notes_service` dans les dependency overrides (pas juste `get_cached_config`)
2. ✅ Utiliser `AsyncMock` pour les méthodes async du service
3. ✅ Supprimer import `patch` inutilisé

**Fichiers modifiés** :
```
tests/unit/test_notes_folders.py  # Fix dependency mocking
```

**Tests** : 1736 passed, 53 skipped (0 failures)

**Commits** :
- `d4a173c` — fix(tests): properly mock NotesService dependency in endpoint tests
- `cbb7f4f` — fix: remove unused patch import

---

### Session 2026-01-06 (Suite 2) — Infinite Scroll + Virtualisation

**Focus** : Implémentation de l'infinite scroll avec virtualisation pour les listes longues

**Accomplissements** :

1. ✅ **VirtualList.svelte** (`web/src/lib/components/ui/VirtualList.svelte` ~200 lignes)
   - Composant réutilisable avec @tanstack/svelte-virtual
   - Virtualisation : seuls les items visibles sont dans le DOM
   - IntersectionObserver pour auto-chargement au scroll
   - Support Svelte 5 snippets pour personnalisation
   - Props : items, estimatedItemHeight, onLoadMore, hasMore, loading

2. ✅ **Intégration Flux** (`web/src/routes/flux/+page.svelte`)
   - Remplacement `{#each}` par `<VirtualList>` pour approved/rejected
   - Suppression du bouton "Charger plus" (auto-scroll)
   - Height calculé dynamiquement

3. ✅ **Page Test Performance** (`web/src/routes/flux/test-performance/+page.svelte`)
   - Génération données mock (1000 à 50000+ items)
   - Mesure temps de rendu initial
   - Validation scroll fluide avec grands datasets

**Fichiers créés/modifiés** :
```
web/src/lib/components/ui/VirtualList.svelte     # NEW (~200 lignes)
web/src/lib/components/ui/index.ts               # MODIFIED (export)
web/src/routes/flux/+page.svelte                 # MODIFIED (intégration)
web/src/routes/flux/test-performance/+page.svelte # NEW (page test)
web/package.json                                  # MODIFIED (+@tanstack/svelte-virtual)
docs/GAPS_TRACKING.md                            # MODIFIED (17/63 MVP = 27%)
ROADMAP.md                                       # MODIFIED (Sprint 1: 84%)
```

**Tests** : 1722 passed, 53 skipped, svelte-check 0 errors

**Commits** :
- `87acd2e` — feat(web): add Infinite Scroll with VirtualList component

---

### Session 2026-01-06 (Suite 3) — Pre-Meeting Briefing Button

**Focus** : Implémentation du bouton briefing pré-réunion sur les événements calendrier

**Accomplissements** :

1. ✅ **PreMeetingModal.svelte** (`web/src/lib/components/briefing/PreMeetingModal.svelte` ~220 lignes)
   - Modal affichant le briefing complet via API `getPreMeetingBriefing()`
   - Sections : infos réunion, participants avec contexte, agenda, points de discussion suggérés
   - Emails et notes liés au contexte de la réunion
   - États loading (Skeleton), error (bouton retry), données

2. ✅ **Bouton briefing sur événements calendrier** (`web/src/routes/+page.svelte`)
   - Bouton icône document sur les événements `source === 'calendar'`
   - Support clavier complet (Enter/Space)
   - Accessible (role="button", tabindex, aria)
   - Dans les deux sections (urgentEvents et otherEvents)

3. ✅ **Barrel export** (`web/src/lib/components/briefing/index.ts`)
   - Module briefing avec export PreMeetingModal

**Fichiers créés/modifiés** :
```
web/src/lib/components/briefing/PreMeetingModal.svelte  # NEW (~220 lignes)
web/src/lib/components/briefing/index.ts                # NEW (barrel export)
web/src/routes/+page.svelte                             # MODIFIED (+60 lignes)
docs/GAPS_TRACKING.md                                   # MODIFIED (18/63 MVP = 29%)
ROADMAP.md                                              # MODIFIED (Sprint 1: 89%)
```

**Tests** : svelte-check 0 errors, 73 tests briefing passent

---

### Session 2026-01-06 (Suite 5) — Deep Code Review & Critical Fixes

**Focus** : Revue de code approfondie et critique avec corrections de bugs critiques

**Accomplissements** :

1. ✅ **VirtualList.svelte — 3 corrections**
   - 🔴 CRITIQUE: Fix stale closure dans IntersectionObserver callback (hasMore/loading capturés)
   - 🟠 MEDIUM: Ajout guard `isLoadingMore` contre appels multiples rapides de `onLoadMore`
   - 🟡 LOW: Fix positionnement loading indicator quand `totalSize=0`

2. ✅ **PreMeetingModal.svelte — 4 corrections**
   - 🔴 CRITIQUE: AbortSignal maintenant passé à `getPreMeetingBriefing()` (abort fonctionne !)
   - 🟠 MEDIUM: Ajout `getInitials()` avec gestion noms vides
   - 🟠 MEDIUM: Reset état (loading, error) à la fermeture du modal
   - 🟡 LOW: Ajout `data-testid` sur éléments clés

3. ✅ **client.ts**
   - `getPreMeetingBriefing(eventId, signal?)` accepte AbortSignal optionnel

**Détails techniques** :

```typescript
// Avant: AbortController créé mais signal jamais passé !
abortController = new AbortController();
briefing = await getPreMeetingBriefing(eventId); // ❌ signal manquant

// Après: Signal correctement passé
abortController = new AbortController();
briefing = await getPreMeetingBriefing(eventId, abortController.signal); // ✅
```

```svelte
// Avant: Callback capture valeurs périmées à la création de l'observer
observer = new IntersectionObserver((entries) => {
  if (hasMore && !loading) { /* hasMore/loading capturés ici */ }
}, options);

// Après: Callback lit valeurs au moment de l'appel
async function handleIntersection(entries) {
  if (!hasMore || loading || isLoadingMore) return; // ✅ valeurs actuelles
  isLoadingMore = true;
  try { await onLoadMore(); } finally { isLoadingMore = false; }
}
observer = new IntersectionObserver(handleIntersection, options);
```

**Tests** : svelte-check 0 errors, 25 tests frontend passent

**Commits** :
- `37b0637` — fix(web): critical fixes for VirtualList and PreMeetingModal

---

### Session 2026-01-06 (Suite 4) — Code Review & Quality Improvements

**Focus** : Revue de code complète VirtualList + PreMeetingModal, améliorations qualité

**Accomplissements** :

1. ✅ **VirtualList.svelte amélioré** (`web/src/lib/components/ui/VirtualList.svelte`)
   - Ajout `data-testid` sur container, items, loading indicator
   - Fix warning Svelte `overscanProp` (retiré de l'init createVirtualizer, géré par $effect)

2. ✅ **PreMeetingModal.svelte amélioré** (`web/src/lib/components/briefing/PreMeetingModal.svelte`)
   - Ajout `AbortController` pour annuler les requêtes quand le modal se ferme
   - Gestion `AbortError` (ignoré silencieusement, pas d'erreur affichée)

3. ✅ **Tests API getPreMeetingBriefing** (`web/src/lib/api/__tests__/client.test.ts` +3 tests)
   - Test success avec attendees et talking points
   - Test URL encoding des caractères spéciaux dans eventId
   - Test gestion erreur 404

**Fichiers modifiés** :
```
web/src/lib/components/ui/VirtualList.svelte      # data-testid + overscan fix
web/src/lib/components/briefing/PreMeetingModal.svelte  # AbortController
web/src/lib/api/__tests__/client.test.ts          # +3 tests getPreMeetingBriefing
```

**Tests** : 25 tests frontend passent, svelte-check 0 errors/warnings

**Commits** :
- `b8b7fed` — feat(web): add pre-meeting briefing button on calendar events

---

### Session 2026-01-06 (Suite) — Notes Folders API

**Focus** : Implémentation des endpoints de gestion de dossiers pour les notes

**Accomplissements** :

1. ✅ **NoteManager** (`src/passepartout/note_manager.py` +80 lignes)
   - `create_folder(path)` — Création dossiers avec validation sécurité
   - `list_folders()` — Liste tous les dossiers (exclut hidden)
   - Protection contre path traversal attacks (`..`, `.`)
   - Fix bug macOS `/var` vs `/private/var` symlink resolution

2. ✅ **Models Notes** (`src/jeeves/api/models/notes.py` +25 lignes)
   - `FolderCreateRequest` — Validation path (min 1, max 500 chars)
   - `FolderCreateResponse` — path, absolute_path, created (bool)
   - `FolderListResponse` — folders list + total count

3. ✅ **NotesService** (`src/jeeves/api/services/notes_service.py` +30 lignes)
   - `create_folder(path)` — Wrapper async avec détection existed
   - `list_folders()` — Wrapper async retournant FolderListResponse

4. ✅ **Notes Router** (`src/jeeves/api/routers/notes.py` +35 lignes)
   - `POST /api/notes/folders` — Créer dossier
   - `GET /api/notes/folders` — Lister dossiers
   - Gestion erreurs ValueError → 400, Exception → 500

5. ✅ **Tests** (`tests/unit/test_notes_folders.py` 18 tests)
   - TestNoteManagerFolderMethods (10 tests)
   - TestNotesService (3 tests)
   - TestFolderEndpoints (5 tests)

**Fichiers créés/modifiés** :
```
src/passepartout/note_manager.py            # MODIFIED (+80 lignes)
src/jeeves/api/models/notes.py              # MODIFIED (+25 lignes)
src/jeeves/api/services/notes_service.py    # MODIFIED (+30 lignes)
src/jeeves/api/routers/notes.py             # MODIFIED (+35 lignes)
tests/unit/test_notes_folders.py            # NEW (18 tests)
docs/GAPS_TRACKING.md                       # MODIFIED (16/63 MVP = 25%)
```

**Tests** : 1721 passed, 53 skipped

**Commits** :
- `b72989c` — feat(api): add folder management endpoints for notes

---

### Session 2026-01-06 — Stats API Implementation

**Focus** : Implémentation de l'API Stats avec endpoints overview et by-source

**Accomplissements** :

1. ✅ **Models Stats** (`src/jeeves/api/models/stats.py` ~50 lignes)
   - `StatsOverviewResponse` — Statistiques agrégées haut niveau
   - `StatsBySourceResponse` — Détails par source (email, teams, calendar, queue, notes)

2. ✅ **StatsService** (`src/jeeves/api/services/stats_service.py` ~300 lignes)
   - Agrégation stats depuis EmailService, TeamsService, QueueService, NotesReviewService
   - Lecture calendar stats depuis StateManager
   - `get_overview()` et `get_by_source()` avec gestion d'erreurs gracieuse

3. ✅ **Stats Router** (`src/jeeves/api/routers/stats.py` ~65 lignes)
   - `GET /api/stats/overview` — Vue globale KPIs
   - `GET /api/stats/by-source` — Stats détaillées par source

4. ✅ **Frontend Types & Functions** (`client.ts` +80 lignes)
   - Interfaces: `StatsOverview`, `StatsBySource`, `CalendarStats`, `NotesReviewStats`
   - Fonctions: `getStatsOverview()`, `getStatsBySource()`

5. ✅ **Page Stats connectée** (`+page.svelte` refait ~350 lignes)
   - Remplacement données mock par API réelles
   - Loading state avec Skeleton
   - Error state avec bouton retry
   - Affichage détails par source (email, teams, calendar, queue, notes)

6. ✅ **Tests Backend** (`test_api_stats.py` 12 tests)
   - TestStatsModels (3 tests)
   - TestStatsService (3 tests)
   - TestStatsOverviewEndpoint (3 tests)
   - TestStatsBySourceEndpoint (3 tests)

7. ✅ **Tests Frontend** (`client.test.ts` +4 tests)
   - `getStatsOverview` success, error
   - `getStatsBySource` success, null sources

**Fichiers créés/modifiés** :
```
src/jeeves/api/models/stats.py              # NEW (~50 lignes)
src/jeeves/api/services/stats_service.py    # NEW (~300 lignes)
src/jeeves/api/routers/stats.py             # NEW (~65 lignes)
src/jeeves/api/routers/__init__.py          # MODIFIED (export stats_router)
src/jeeves/api/app.py                       # MODIFIED (register router)
web/src/lib/api/client.ts                   # MODIFIED (+80 lignes)
web/src/lib/components/ui/index.ts          # MODIFIED (export Skeleton)
web/src/routes/stats/+page.svelte           # MODIFIED (~350 lignes)
tests/unit/test_api_stats.py                # NEW (12 tests)
web/src/lib/api/__tests__/client.test.ts    # MODIFIED (+4 tests)
```

**Tests** : 22 tests frontend, 12 tests backend stats, svelte-check 0 errors

**Commits** :
- `81492f3` — feat(api): implement Stats API with overview and by-source endpoints

---

### Session 2026-01-05 (Suite 17) — Search API Frontend Integration

**Focus** : Intégration frontend de l'API de recherche globale avec CommandPalette

**Accomplissements** :

1. ✅ **Types Search** (`client.ts` +75 lignes)
   - Types: `SearchResultType`, `GlobalNoteSearchResult`, `GlobalEmailSearchResult`, etc.
   - Interfaces: `GlobalSearchResponse`, `SearchResultsByType`, `RecentSearchesResponse`

2. ✅ **Fonctions API Search** (`client.ts` +20 lignes)
   - `globalSearch(query, options)` — Recherche multi-source avec filtres
   - `getRecentSearches(limit)` — Historique des recherches

3. ✅ **CommandPalette.svelte** (~180 lignes modifiées)
   - Connexion API avec debounce 300ms (après 2 caractères)
   - Transformation résultats API → format d'affichage unifié
   - Navigation par type: note → /notes, email → /flux, event → /calendar, teams → /discussions
   - États visuels: spinner loading, message erreur, "Aucun résultat"
   - Tri par score de pertinence

4. ✅ **Tests** (+5 tests)
   - `globalSearch` success, options, error
   - `getRecentSearches` success, custom limit

**Fichiers modifiés** :
```
web/src/lib/api/client.ts                         # +115 lignes (types + fonctions)
web/src/lib/components/ui/CommandPalette.svelte   # +185 lignes (intégration API)
web/src/lib/api/__tests__/client.test.ts          # +5 tests
```

**Tests** : 18 tests frontend passent, svelte-check 0 errors

**Commits** :
- `318d7ec` — feat(web): integrate Search API with CommandPalette

---

### Session 2026-01-05 (Suite 16) — Notes Git Versioning UI

**Focus** : Implémentation de l'interface utilisateur pour le versioning Git des notes

**Accomplissements** :

1. ✅ **Types & API Client** (`client.ts` +76 lignes)
   - Types: `NoteVersion`, `NoteVersionsResponse`, `NoteVersionContent`, `NoteDiff`
   - Fonctions: `getNoteVersions()`, `getNoteVersionContent()`, `diffNoteVersions()`, `restoreNoteVersion()`

2. ✅ **VersionDiff.svelte** (~110 lignes)
   - Affichage diff unifié avec couleurs (vert additions, rouge deletions)
   - Parsing du diff_text en lignes typées (addition, deletion, context, header)
   - Stats header (+N / -N)

3. ✅ **NoteHistory.svelte** (~260 lignes)
   - Modal historique avec liste des versions
   - Sélection de 2 versions pour comparaison
   - Bouton restaurer avec confirmation
   - Intégration VersionDiff pour affichage du diff

4. ✅ **Intégration page note** (`+page.svelte` +20 lignes)
   - Bouton historique (🕐) dans le header
   - État `showHistory` et `handleRestore`

5. ✅ **Export Modal** (`index.ts`)
   - Ajout de Modal aux exports du barrel UI

6. ✅ **Tests API** (+5 tests)
   - `getNoteVersions`, `getNoteVersionContent`, `diffNoteVersions`, `restoreNoteVersion`

**Corrections appliquées (revue code)** :
- Variables `e` non utilisées dans catch blocks → `_e`

**Tests** : 13 tests frontend passent, svelte-check 0 errors

**Fichiers créés/modifiés** :
```
web/src/lib/api/client.ts                         # +76 lignes (types + fonctions)
web/src/lib/components/notes/VersionDiff.svelte   # Nouveau (~110 lignes)
web/src/lib/components/notes/NoteHistory.svelte   # Nouveau (~260 lignes)
web/src/lib/components/ui/index.ts                # +1 ligne (export Modal)
web/src/routes/notes/[...path]/+page.svelte       # +20 lignes
web/src/lib/api/__tests__/client.test.ts          # +5 tests
```

**Commits** :
- `22c8d43` — feat(web): add Notes Git Versioning UI

---

### Session 2026-01-05 (Suite 15) — UI Components Sprint 1

**Focus** : Implémentation des composants UI réutilisables (Modal, Toast, Tabs, ConfidenceBar, Skeleton)

**Accomplissements** :

1. ✅ **Modal.svelte** (~180 lignes)
   - Dialog avec glass design et animations spring
   - Fermeture via Escape, backdrop click, ou bouton
   - Focus trap et scroll lock
   - Variantes de taille : sm, md, lg, full

2. ✅ **Système Toast** (~200 lignes)
   - `toast.svelte.ts` — Store avec auto-dismiss et gestion des timeouts
   - `Toast.svelte` — Notification individuelle (success/error/warning/info)
   - `ToastContainer.svelte` — Positionnement et empilement
   - Limite 5 toasts, durées personnalisables

3. ✅ **Tabs.svelte** (~170 lignes)
   - 3 variantes : default (segmented), pills, underline
   - Navigation clavier complète (flèches, Home, End)
   - Support tabs désactivés et badges
   - ARIA tablist/tab/tabpanel

4. ✅ **ConfidenceBar.svelte** (~80 lignes)
   - Affichage confiance IA (0-1)
   - Couleurs adaptatives selon le niveau
   - Labels en français (Confiance, Probable, Possible, Incertain, Faible)

5. ✅ **Skeleton.svelte** (~80 lignes)
   - 5 variantes : text, avatar, card, rectangular, circular
   - Animation shimmer avec support prefers-reduced-motion
   - Support multi-lignes pour text

**Corrections appliquées (revue code)** :
- `Tabs.svelte` : Scope le querySelector au composant (évite collision avec autres Tabs)
- `toast.svelte.ts` : Gestion propre des timeouts (clear sur dismiss/clear)

**Tests** : svelte-check 0 errors, 0 warnings

**Fichiers créés** :
```
web/src/lib/components/ui/Modal.svelte
web/src/lib/components/ui/Toast.svelte
web/src/lib/components/ui/ToastContainer.svelte
web/src/lib/components/ui/Tabs.svelte
web/src/lib/components/ui/ConfidenceBar.svelte
web/src/lib/components/ui/Skeleton.svelte
web/src/lib/stores/toast.svelte.ts
```

**Commits** :
- `b65c509` — feat(web): add UI components - Modal, Toast, Tabs, ConfidenceBar, Skeleton

---

### Session 2026-01-05 (Suite 14) — Markdown Editor

**Focus** : Implémentation d'un éditeur Markdown complet pour les notes

**Accomplissements** :

1. ✅ **Configuration Marked** (`web/src/lib/utils/markdown.ts`)
   - Extension wikilinks `[[Note Title]]` custom
   - Fonctions `renderMarkdown()`, `extractWikilinks()`
   - Support GFM et line breaks

2. ✅ **Composants Notes** (4 nouveaux)
   - `MarkdownPreview.svelte` — Rendu HTML avec styles prose
   - `EditorTextarea.svelte` — Textarea avec `insertText()`, `wrapSelection()`
   - `MarkdownToolbar.svelte` — Boutons formatage + mode toggle
   - `MarkdownEditor.svelte` — Composant principal avec auto-save

3. ✅ **Fonctionnalités**
   - Preview temps réel du markdown
   - Wikilinks cliquables dans preview
   - Raccourcis clavier : Cmd+B/I/E/K/W/S
   - Auto-save avec debounce (1s)
   - Modes : Écrire / Aperçu / Split
   - Indicateur de statut (Enregistrement... / Enregistré)
   - Layout responsive (mobile/desktop)

4. ✅ **Intégration** (`web/src/routes/notes/[...path]/+page.svelte`)
   - Remplacement textarea basique par MarkdownEditor
   - Mode lecture avec MarkdownPreview

**Tests** : svelte-check 0 errors, 0 warnings

**Fichiers créés** :
```
web/src/lib/utils/markdown.ts
web/src/lib/components/notes/MarkdownPreview.svelte
web/src/lib/components/notes/EditorTextarea.svelte
web/src/lib/components/notes/MarkdownToolbar.svelte
web/src/lib/components/notes/MarkdownEditor.svelte
```

**Commits** :
- `35a5ef7` — feat(web): implement Markdown Editor with live preview

---

### Session 2026-01-05 (Suite 13) — UI Notes Review (SM-2)

**Focus** : Interface utilisateur complète pour la révision des notes avec SM-2

**Accomplissements** :

1. ✅ **API Client étendu** (`web/src/lib/api/client.ts`)
   - 7 types ajoutés : NoteReviewMetadata, NotesDueResponse, ReviewStatsResponse, etc.
   - 7 fonctions API : getNotesDue, getReviewStats, getReviewWorkload, recordReview, etc.

2. ✅ **Store Svelte 5** (`web/src/lib/stores/notes-review.svelte.ts`)
   - État réactif avec $state et $derived
   - Actions : fetchDueNotes, submitReview, postponeCurrentNote, navigation
   - Gestion session : progress, reviewedThisSession

3. ✅ **Composants UI** (3 nouveaux)
   - `ProgressRing.svelte` — Cercle SVG animé pour progression
   - `QualityRating.svelte` — 6 boutons (0-5) avec emojis et raccourcis clavier
   - `ReviewCard.svelte` — Carte note avec métadonnées SM-2

4. ✅ **Widget Dashboard** (`web/src/routes/+page.svelte`)
   - Affichage conditionnel si notes dues > 0
   - ProgressRing avec pourcentage de notes à jour
   - Navigation vers page révision

5. ✅ **Page Révision** (`web/src/routes/notes/review/+page.svelte`)
   - Mode fullscreen focus
   - États : Loading, Empty, Review, Complete
   - Raccourcis clavier : 1-6 (noter), ←→ (naviguer), s (reporter), Esc (quitter)
   - Feedback visuel après chaque révision

**Tests** : svelte-check 0 errors, 26 tests API passent

**Fichiers créés** :
```
web/src/lib/stores/notes-review.svelte.ts
web/src/lib/components/ui/ProgressRing.svelte
web/src/lib/components/notes/QualityRating.svelte
web/src/lib/components/notes/ReviewCard.svelte
web/src/routes/notes/review/+page.svelte
```

---

### Session 2026-01-05 (Suite 12) — API Notes Review

**Focus** : Création des endpoints API pour exposer le système de révision SM-2

**Accomplissements** :

1. ✅ **Service NotesReviewService** (`src/jeeves/api/services/notes_review_service.py`)
   - Wrapper async autour de NoteScheduler
   - Méthodes: get_notes_due, get_note_metadata, record_review, postpone_review, trigger_immediate_review, get_review_stats, estimate_workload, get_review_configs

2. ✅ **8 nouveaux endpoints** dans `src/jeeves/api/routers/notes.py`
   - GET `/api/notes/reviews/due` — Notes à réviser
   - GET `/api/notes/reviews/stats` — Statistiques révision
   - GET `/api/notes/reviews/workload` — Prévision charge (7j)
   - GET `/api/notes/reviews/configs` — Configuration par type de note
   - GET `/api/notes/{id}/metadata` — Métadonnées SM-2
   - POST `/api/notes/{id}/review` — Enregistrer révision (quality 0-5)
   - POST `/api/notes/{id}/postpone` — Reporter révision
   - POST `/api/notes/{id}/trigger` — Déclencher révision immédiate

3. ✅ **Bug corrigé** : Ordre des routes FastAPI
   - Les routes statiques `/reviews/*` doivent être définies AVANT `/{note_id}`
   - Sinon FastAPI matche "reviews" comme un note_id

4. ✅ **26 tests unitaires** (`tests/unit/test_notes_review_api.py`)
   - TestReviewModels (4 tests)
   - TestNotesReviewService (11 tests)
   - TestNotesReviewEndpoints (11 tests)

**Tests** : 1692 passed, 53 skipped (0 failures)

---

### Session 2026-01-05 (Suite 11) — Note Enrichment System Complet

**Focus** : Implémentation complète du système de révision espacée SM-2 pour les notes

**Contexte** :
- Document d'architecture créé en session précédente (`docs/plans/note-enrichment-system.md`)
- Système "absolument primordial" — le cœur cognitif de Scapin
- Algorithme SM-2 (SuperMemo) avec paramètres personnalisés

**Accomplissements** :

1. ✅ **7 modules Passepartout créés** (~2200 lignes)
   - `note_types.py` — Enum NoteType, ImportanceLevel, ReviewConfig
   - `note_metadata.py` — SQLite storage, EnrichmentRecord, NoteMetadata
   - `note_scheduler.py` — SM-2 algorithm, SchedulingResult
   - `note_reviewer.py` — ReviewAction, ReviewContext, NoteReviewer
   - `note_enricher.py` — EnrichmentSource, EnrichmentPipeline
   - `note_merger.py` — Three-way merge, MergeStrategy
   - `background_worker.py` — 24/7 worker avec max 50 reviews/jour

2. ✅ **75 tests unitaires**
   - test_note_types.py — 22 tests
   - test_note_metadata.py — 18 tests
   - test_note_scheduler.py — 18 tests
   - test_note_merger.py — 17 tests

3. ✅ **Corrections Ruff**
   - Imports inutilisés supprimés
   - Arguments unused préfixés avec `_`
   - Simplification conditions imbriquées

**Décisions clés implémentées** :
- **SM-2 Formula** : `EF' = EF + (0.1 - (5 - Q) × (0.08 + (5 - Q) × 0.02))`
- **Intervalles** : I(1)=2h, I(2)=12h, I(n)=I(n-1)×EF
- **Auto-apply threshold** : 0.90 (confiance)
- **Max daily reviews** : 50
- **Session duration** : 5 minutes max
- **User wins conflicts** : Smart merge avec priorité utilisateur
- **Type-specific intervals** : PROJET=2h, PERSONNE=2h, SOUVENIR=skip

**Fichiers créés** :
```
src/passepartout/
├── note_types.py          (~200 lignes)
├── note_metadata.py       (~500 lignes)
├── note_scheduler.py      (~250 lignes)
├── note_reviewer.py       (~600 lignes)
├── note_enricher.py       (~400 lignes)
├── note_merger.py         (~350 lignes)
└── background_worker.py   (~300 lignes)

tests/unit/
├── test_note_types.py     (22 tests)
├── test_note_metadata.py  (18 tests)
├── test_note_scheduler.py (18 tests)
└── test_note_merger.py    (17 tests)
```

**Commits** :
- `6f7f0ee` — feat(passepartout): implement complete Note Enrichment System with SM-2

**Tests** : 1666 passed, 53 skipped (0 failures)

---

### Session 2026-01-05 (Suite 10) — Roadmap v3.1 Notes au Centre

**Focus** : Révision complète de la roadmap pour prioriser les Notes et la qualité d'analyse

**Contexte** :
- Analyse comparative ROADMAP.md vs DESIGN_PHILOSOPHY.md vs GAPS_TRACKING.md
- 116 items identifiés (63 MVP, 53 Nice-to-have)
- Roadmap Q2-Q4 2026 obsolète (nous sommes en janvier 2026)

**Décisions clés** :

1. **Notes au centre de l'architecture**
   - Chaque email enrichit les notes (entités extraites, proposed_notes)
   - Chaque analyse est enrichie par le contexte des notes (Passepartout)
   - Boucle bidirectionnelle Email ↔ Notes = cœur du système

2. **Réorganisation en Sprints thématiques** (vs phases numérotées)
   - Sprint 1 : Notes & Fondation Contexte (19 items)
   - Sprint 2 : Qualité d'Analyse (14 items)
   - Sprint 3 : Workflow & Actions (16 items)
   - Sprint 4 : Temps Réel & UX (14 items)
   - Sprint 5 : Qualité & Release (6 items)

3. **Priorisation Notes dans Sprint 1** (vs UI Components seuls)
   - Git Versioning backend + 4 endpoints API
   - Éditeur Markdown complet
   - Search API (clé pour retrouver le contexte)
   - POST /api/notes/folders

4. **Promotion d'items Nice-to-have → MVP**
   - Extraction entités automatique
   - extracted_entities dans EmailProcessingResult
   - proposed_tasks et proposed_notes
   - Bouton "Discuter de cette note"

**Fichiers modifiés** :
- `docs/GAPS_TRACKING.md` — Créé (116 items, 63 MVP, 53 Nice-to-have)
- `ROADMAP.md` — Réécrit complet (v3.1 Notes au centre)

**Commits** :
- `5ac3fed` — docs: add comprehensive gap tracking document
- `c017ddd` — docs(roadmap): v3.1 - Notes & Analyse au centre

**Calendrier révisé** :
- Sprint 1 : Janvier S2-S3
- Sprint 2 : Janvier S4 - Février S5
- Sprint 3 : Février S6-S7
- Sprint 4 : Février S8 - Mars S9
- Sprint 5 : Mars S10-S11
- **Target v1.0 RC** : Mi-mars 2026

---

### Session 2026-01-05 (Suite 9) — Flux Email Complet avec Actions IMAP

**Focus** : Compléter le workflow de revue email avec exécution des actions IMAP et destinations IA

**Accomplissements** :

1. ✅ **Exécution actions IMAP sur approbation** (`queue_service.py`)
   - `approve_item()` exécute maintenant l'action IMAP (archive/delete/task)
   - `_execute_email_action()` gère les différents types d'actions
   - Auto-création des dossiers de destination via `_ensure_folder_exists()`

2. ✅ **Destinations IA utilisées** (flux complet)
   - Ajout `destination` à `ApproveRequest` model
   - Passage de la destination du frontend → API → IMAP
   - Dossiers créés automatiquement (ex: `Archive/Famille/Gazette_Arlette`)

3. ✅ **Flagging IMAP anti-reimport** (`processor.py`, `imap_client.py`)
   - Emails flagués (`\\Flagged`) quand mis en queue
   - `unflagged_only=True` par défaut pour éviter reimport
   - `_unflag_email()` sur reject pour permettre retraitement

4. ✅ **Limite 20 items par batch** (tous canaux)
   - `DEFAULT_PROCESSING_LIMIT = 20` dans processor, teams_processor, calendar_processor
   - Traitement oldest-first (plus anciens en premier)
   - Documentation dans CLAUDE.md section "Règles de Traitement"

5. ✅ **Vue enrichie Level 3** (`flux/+page.svelte`)
   - Toggle "Enrichir" / "Vue simple"
   - `reasoning_detailed` affiché quand disponible
   - Métadonnées inline en mode enrichi

**Fichiers modifiés** :
- `src/jeeves/api/services/queue_service.py` — Actions IMAP
- `src/trivelin/processor.py` — Flagging + limite 20
- `src/integrations/email/imap_client.py` — add_flag/remove_flag
- `web/src/routes/flux/+page.svelte` — UI enrichie
- `CLAUDE.md` — Règles de traitement

**Commit** : `3d31dd6` — feat(queue): complete email processing flow with IMAP actions and destinations

---

### Session 2026-01-05 (Suite 8) — Connexion Settings à l'API Config

**Focus** : Connecter la page Réglages au endpoint `/api/config` pour afficher les statuts réels des intégrations

**Accomplissements** :

1. ✅ **Fix endpoint `/api/config`** (`src/jeeves/api/routers/system.py`)
   - Bug corrigé : `config.ai.model` n'existait pas → valeur par défaut "claude-3-5-haiku"
   - Ajout modèle `IntegrationStatus` avec id, name, icon, status, last_sync
   - Construction dynamique des statuts d'intégration depuis la configuration réelle

2. ✅ **Nouveau store config** (`web/src/lib/stores/config.svelte.ts`)
   - Store Svelte 5 avec `$state` et `$derived`
   - Fonction `fetchConfig()` avec gestion d'erreurs
   - Getters réactifs : `integrations`, `emailAccounts`, `teamsEnabled`, etc.

3. ✅ **Client API étendu** (`web/src/lib/api/client.ts`)
   - Ajout types `IntegrationStatus` et `SystemConfig`
   - Ajout fonction `getConfig(): Promise<SystemConfig>`
   - Export des nouveaux types dans `index.ts`

4. ✅ **Page Settings connectée** (`web/src/routes/settings/+page.svelte`)
   - Remplacement données mockées par `configStore.integrations`
   - Ajout état de chargement (spinner)
   - Ajout affichage erreur si API indisponible
   - Fix `lastSync` → `last_sync` (convention snake_case API)

5. ✅ **Fix page principale** (`web/src/routes/+page.svelte`)
   - Distinction entre 'mock' (serveur offline), 'api' (données réelles), 'api-empty' (aucun item)
   - Message approprié selon la source des données

**Statuts intégrations affichés** :
| Intégration | Statut | Condition |
|-------------|--------|-----------|
| Courrier (IMAP) | connected | Compte email configuré |
| Microsoft Teams | disconnected | `teams.enabled = false` |
| Agenda | disconnected | `calendar.enabled = false` |
| OmniFocus | disconnected | Non implémenté |

**Commit** :
- `f52c231` — feat(web): connect Settings page to /api/config endpoint

---

### Session 2026-01-04 (Suite 7) — Intégration QueueStorage & Tests E2E API

**Focus** : Connexion du QueueStorage au processor et tests end-to-end du workflow email

**Accomplissements** :

1. ✅ **Intégration QueueStorage** (`src/trivelin/processor.py`)
   - Import et initialisation de `get_queue_storage()`
   - Appel `queue_storage.save_item()` lors du queuing pour revue manuelle
   - Emails maintenant persistés dans `data/queue/`

2. ✅ **Corrections API**
   - `src/jeeves/api/routers/queue.py` : Conversion ID email int → str
   - `src/jeeves/api/services/email_service.py` : Destination fallback pour delete action

3. ✅ **Tests mocks mis à jour** (`tests/unit/test_email_processor.py`)
   - Ajout `@patch('src.trivelin.processor.get_queue_storage')` sur 11 tests

4. ✅ **Workflow E2E testé avec succès**
   - `POST /api/email/process` → 2 emails analysés et queued
   - `GET /api/queue` → Liste des items en attente
   - `POST /api/queue/{id}/approve` → Approbation avec timestamp
   - `POST /api/email/execute` → Exécution actions IMAP (delete → Trash, archive → Archive/2025/Work)
   - `GET /api/queue/stats` → Statistiques par status/account

5. ✅ **Configuration iCloud Mail fonctionnelle**
   - Connexion IMAP imap.mail.me.com:993
   - Création automatique des dossiers (Trash, Archive/2025/Work)

**Commits** :
- `7d7b321` — feat(trivelin): integrate QueueStorage into email processor
- `be9cf29` — fix(api): convert email ID to string in queue router
- `4d5cafd` — fix(api): use destination param for delete action with fallback

**Tests** : 1488 passed, 53 skipped

---

### Session 2026-01-04 (Suite 6) — Phase 1.6 Journaling Complet COMPLET

**Focus** : Journaling multi-source avec calibration Sganarelle

**Accomplissements** :

1. ✅ **Modèles multi-source** (`src/jeeves/journal/models.py`)
   - TeamsSummary, CalendarSummary, OmniFocusSummary
   - Extension JournalEntry avec tous les champs multi-source

2. ✅ **Providers multi-source** (`src/jeeves/journal/providers/`)
   - TeamsHistoryProvider, CalendarHistoryProvider, OmniFocusHistoryProvider
   - MultiSourceProvider agrégateur

3. ✅ **Revues hebdomadaires/mensuelles** (`src/jeeves/journal/reviews.py`)
   - WeeklyReview avec détection patterns et score productivité
   - MonthlyReview avec tendances et progression objectifs

4. ✅ **Calibration Sganarelle étendue** (`src/jeeves/journal/feedback.py`)
   - SourceCalibration par source (email, teams, calendar)
   - CalibrationAnalysis avec recommandations seuils
   - Méthodes record_correct/incorrect_decision, analyze_calibration

5. ✅ **API Journal** (`src/jeeves/api/routers/journal.py`)
   - GET /api/journal/{date}, /list, /weekly/{week}, /monthly/{month}
   - POST /answer, /correction, /complete, /export

6. ✅ **Frontend Journal** (`web/src/routes/journal/+page.svelte`)
   - Tabs multi-sources (Email, Teams, Calendar, OmniFocus)
   - Questions interactives et corrections inline
   - Fix Badge variants → custom styled spans

7. ✅ **Tests** (+38 nouveaux)
   - test_journal_models.py : 56 tests (multi-source)
   - test_journal_feedback.py : 26 tests (calibration)

**Corrections** :
- Fix `{@const}` invalid placement Svelte
- Fix Badge variant type errors ("warning", "success")
- Fix WeeklyReviewResult field name (patterns_processed)
- Fix calibrate_by_source return type assertion

**Tests** : 1414 tests (1414 backend + 8 frontend), svelte-check 0 errors

---

### Session 2026-01-04 (Suite 5) — Phase 0.9 PWA Mobile COMPLET

**Focus** : Progressive Web App avec Service Worker, Notifications, Deeplinks

**Accomplissements** :

1. ✅ **Service Worker v0.9.0** (`web/static/sw.js`)
   - Caching intelligent : network-first pour API, cache-first pour static
   - Stale-while-revalidate pour mises à jour en arrière-plan
   - Background sync support
   - Push notification handlers avec urgence

2. ✅ **Push Notifications** (`web/src/lib/stores/notifications.svelte.ts`)
   - Demande de permission utilisateur
   - Notifications via Service Worker
   - Écoute des événements WebSocket pour triggering
   - Intégration dans Settings

3. ✅ **Icônes PWA** (`web/static/icons/`)
   - icon-192.png, icon-512.png (gradient bleu-violet avec "S")
   - apple-touch-icon.png (180x180)
   - favicon-16.png, favicon-32.png, favicon.ico

4. ✅ **Manifest étendu** (`web/static/manifest.json`)
   - 4 shortcuts (Briefing, Courrier, Notes, Journal)
   - share_target pour recevoir du contenu partagé
   - protocol_handlers pour `web+scapin://`
   - launch_handler pour navigation existante

5. ✅ **Deeplinks** (`web/src/routes/share/`, `web/src/routes/handle/`)
   - Page /share pour recevoir contenu partagé
   - Page /handle pour routing protocole web+scapin://
   - Navigation intelligente vers sections pertinentes

**Tests** : 1385+ tests (1376 backend + 8 frontend), svelte-check 0 errors

---

### Session 2026-01-04 (Suite 4) — Corrections et Validation Phase 0.8

**Focus** : Corrections bugs briefing + WebSocket proxy, validation complète

**Corrections** :

1. **Fix briefing parameter names** (`generator.py`)
   - Problème : `DefaultBriefingDataProvider` utilisait `_limit`, `_include_in_progress`, `_days`
   - Ces noms avec underscore cassaient les appels avec keyword arguments
   - Solution : Renommage vers `limit`, `include_in_progress`, `days` + `# noqa: ARG002`
   - Commit : `6d1d060`

2. **Fix WebSocket proxy Vite** (`vite.config.ts`)
   - Problème : Le proxy Vite ne transmettait que `/api`, pas `/ws`
   - Solution : Ajout proxy `/ws` → `ws://localhost:8000` avec `ws: true`
   - Commit : `5d4a935`

3. **Installation websockets** (uvicorn)
   - Problème : Uvicorn retournait "No supported WebSocket library detected"
   - Solution : `pip install websockets` (inclus dans `uvicorn[standard]`)

**Validation** :
- ✅ Tests complets : 1377 passed, 53 skipped
- ✅ Ruff : 0 warnings sur `src/`
- ✅ Svelte-check : 0 errors, 0 warnings
- ✅ WebSocket connecté et authentifié (logs backend)
- ✅ UX : Dashboard fonctionnel après login PIN

**Flow complet testé** :
```
Login (PIN 1234) → JWT Token → Dashboard → WebSocket connecté
```

---

### Session 2026-01-04 (Suite 3) — Phase 0.8 Auth JWT + WebSockets COMPLET

**Focus** : Finalisation Phase 0.8 avec authentification JWT et WebSockets temps réel

**Accomplissements** :

**Backend Auth (JWT)** :
1. ✅ `src/core/config_manager.py` — Ajout AuthConfig
2. ✅ `src/jeeves/api/auth/__init__.py` — Module auth
3. ✅ `src/jeeves/api/auth/jwt_handler.py` — Création/vérification tokens JWT (python-jose)
4. ✅ `src/jeeves/api/auth/password.py` — Hash bcrypt PIN (passlib remplacé par bcrypt direct pour compatibilité Python 3.13)
5. ✅ `src/jeeves/api/routers/auth.py` — Endpoints POST /api/auth/login, GET /api/auth/check
6. ✅ `src/jeeves/api/deps.py` — Dependency get_current_user avec HTTPBearer
7. ✅ 23 tests unitaires (jwt_handler, auth_router)

**Backend WebSockets** :
1. ✅ `src/jeeves/api/websocket/manager.py` — ConnectionManager avec EventBus bridge
2. ✅ `src/jeeves/api/websocket/router.py` — Endpoint WS /ws/live?token=xxx
3. ✅ 11 tests unitaires (websocket_manager)

**Frontend Auth** :
1. ✅ `web/src/lib/api/client.ts` — Token storage, Bearer header, login/logout/checkAuth
2. ✅ `web/src/lib/stores/auth.svelte.ts` — Auth store Svelte 5 runes
3. ✅ `web/src/routes/login/+page.svelte` — Page login avec keypad PIN mobile
4. ✅ `web/src/routes/+layout.svelte` — Auth guard, redirect vers /login

**Frontend WebSockets** :
1. ✅ `web/src/lib/stores/websocket.svelte.ts` — WS store avec auto-reconnect
2. ✅ Intégration dans layout — Connect après auth

**Configuration** :
```bash
AUTH__ENABLED=true
AUTH__JWT_SECRET_KEY=change-this-to-32-chars-minimum
AUTH__JWT_EXPIRE_MINUTES=10080  # 7 jours
AUTH__PIN_HASH=$2b$12$...  # bcrypt hash du PIN
```

**Tests** : 34 nouveaux tests, 1376 total (1 skip pré-existant)

**Commits** : Phase 0.8 complète

---

### Session 2026-01-04 — Phase 0.8 Interface Web Complète

**Focus** : Implémentation complète de l'interface web SvelteKit

**Accomplissements** :
1. ✅ Setup projet SvelteKit + TailwindCSS v4
2. ✅ Design system complet (Button, Card, Badge, Input, PullToRefresh, SwipeableCard, CommandPalette)
3. ✅ Layout responsive (Sidebar collapsible, MobileNav, ChatPanel avec suggestions contextuelles)
4. ✅ 7 pages fonctionnelles : Briefing, Flux, Notes, Discussions, Journal, Stats, Settings
5. ✅ Recherche globale unifiée (Cmd+K / Ctrl+K) avec navigation clavier
6. ✅ Page Notes avec arbre de dossiers et notes épinglées
7. ✅ Bouton sync Apple Notes avec état de chargement
8. ✅ Gestes mobiles : pull-to-refresh, swipe cards
9. ✅ Indicateurs de statut (dots colorés, animations)
10. ✅ Build production sans erreurs

**Architecture web** :
```
web/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── ui/          # Button, Card, Badge, CommandPalette...
│   │   │   └── layout/      # Sidebar, MobileNav, ChatPanel
│   │   ├── stores/          # UI state (showCommandPalette)
│   │   ├── types/           # TypeScript interfaces
│   │   └── utils/           # formatters
│   └── routes/              # Pages SvelteKit
├── static/                  # Assets statiques
└── package.json
```

**Technologies** :
- SvelteKit 2.x avec Svelte 5 ($state, $derived, $effect, $props)
- TailwindCSS v4 (CSS-first, variables CSS)
- TypeScript strict mode

---

### Session 2026-01-04 (Suite) — Phase 0.8 Connexion API + PWA

**Focus** : Connexion frontend-backend, PWA, configuration environnement

**Accomplissements** :
1. ✅ **Design Liquid Glass** (Apple WWDC 2025) - Implémenté 3 niveaux
   - CSS foundations: glass layers, blur, spring animations
   - Components: Card, Button, Sidebar, MobileNav avec variants glass
   - Polish: ambient gradient, glow shadows
2. ✅ **PWA Setup** - manifest.json, service worker, icône SVG
3. ✅ **Client API** - `$lib/api/client.ts` typé, gestion d'erreurs
4. ✅ **Store Briefing** - `$lib/stores/briefing.svelte.ts` avec Svelte 5 runes
5. ✅ **Routes dynamiques** - `/flux/[id]`, `/notes/[...path]`
6. ✅ **Proxy Vite** - `/api/*` → backend FastAPI (port 8000)
7. ✅ **Configuration environnement** :
   - `.env.example` avec documentation complète
   - `.env` pour développement
   - `config/defaults.yaml` avec valeurs par défaut
8. ✅ **Tests** - 8 tests unitaires pour client API (vitest)
9. ✅ **Deeplinks** - Ajouté au plan Phase 0.9 (ROADMAP.md)

**Fichiers créés/modifiés** :
```
web/
├── src/lib/api/
│   ├── client.ts              # Client API typé
│   ├── index.ts               # Exports
│   └── __tests__/client.test.ts  # 8 tests
├── src/lib/stores/
│   └── briefing.svelte.ts     # Store avec Svelte 5 runes
├── src/routes/
│   ├── flux/[id]/+page.svelte # Détail email/message
│   └── notes/[...path]/+page.svelte # Détail note
├── static/
│   ├── manifest.json          # PWA manifest
│   ├── sw.js                  # Service worker
│   └── icons/icon.svg         # Icône app
└── vite.config.ts             # Proxy API

scapin/
├── .env.example               # Documentation variables
├── .env                       # Config développement
└── config/defaults.yaml       # Valeurs par défaut
```

**Architecture connexion** :
```
Frontend (Vite:5173) ──proxy──> Backend (FastAPI:8000)
        │                              │
        └── /api/* ────────────────────┘
```

**Tests** : 8 tests client API passent (vitest)

---

### Session 2026-01-04 (Suite 2) — Tests E2E et Accessibilité

**Focus** : Validation complète du stack, tests PWA mobile, corrections accessibilité

**Accomplissements** :
1. ✅ **Tests complets** - 1351 tests passent (8 web + 1343 backend)
2. ✅ **Démarrage serveurs** - Backend (8000) + Frontend (5173) fonctionnels
3. ✅ **Test API live** :
   - `GET /api/health` → "healthy", version 0.7.0
   - `GET /api/briefing/morning` → Données vides (config dev)
   - Proxy Vite fonctionne correctement
4. ✅ **PWA mobile** - Exposé sur réseau (`--host`), testable sur iPhone
5. ✅ **Corrections accessibilité** (CommandPalette.svelte) :
   - Backdrop : `role="button"` + `aria-label` + `onkeydown`
   - Modal : `role="dialog"` + `aria-modal` + `tabindex="-1"`
   - HTML : `lang="fr"` + favicon SVG + theme-color

**Fichiers modifiés** :
- `web/src/lib/components/ui/CommandPalette.svelte` — ARIA roles
- `web/src/app.html` — lang, favicon, theme-color

**Commits** :
- `ace3273` — feat(web): connect API client, add PWA support
- `5e7b027` — fix(a11y): add ARIA roles and labels to CommandPalette

**Tests PWA iOS** :
```
http://192.168.101.120:5173
Safari → Partage → Sur l'écran d'accueil → Ajouter
```

---

### Session 2026-01-03 (Suite 6) — Refactoring PKM → Scapin

**Focus** : Suppression de toutes les références à "PKM" dans le codebase

**Accomplissements** :
1. ✅ Renommage `PKMLogger` → `ScapinLogger` dans `src/monitoring/logger.py`
2. ✅ Renommage `PKMConfig` → `ScapinConfig` dans `src/core/config_manager.py`
3. ✅ Renommage `PKMError` → `ScapinError` dans `src/core/exceptions.py`
4. ✅ Mise à jour de tous les imports (35 fichiers modifiés)
5. ✅ Mise à jour des chemins de dossiers (`_PKM` → `_Scapin`)
6. ✅ Suppression du répertoire `src/pkm_system.egg-info/`
7. ✅ Mise à jour de `docs/api/README.md`
8. ✅ Mise à jour de `ROADMAP.md` avec la progression correcte
9. ✅ Tous les tests passent (1288 unit, 65 integration)
10. ✅ Ruff 0 warnings

**Fichiers principaux modifiés** :
- `src/monitoring/logger.py` — Classe ScapinLogger, logger names "scapin.*"
- `src/core/config_manager.py` — Classe ScapinConfig, chemins _Scapin
- `src/core/exceptions.py` — Classe ScapinError
- `tests/unit/test_logger.py` — Assertions mises à jour pour "scapin"

**Commits** :
- `951561d` — refactor: rename PKM to Scapin across entire codebase

---

### Session 2026-01-03 (Suite 5) — Revue de Code Approfondie

**Focus** : Revue de code complète des phases 1.0-1.4 et 0.7

**Résultats** :
- ✅ **Ruff** : 0 warnings
- ✅ **Tests** : 1288 unit tests passent, 44 skippés
- ✅ **Phases révisées** : 1.0, 1.1, 1.2, 1.3, 1.4, 0.7

**Corrections appliquées** :
1. ✅ `responses.py:27` — `datetime.now()` → `datetime.now(timezone.utc)`
2. ✅ `briefing_service.py` — Suppression code mort (isinstance check jamais faux)
3. ✅ `briefing_service.py` — Suppression import inutilisé `PerceivedEvent`

**Fichiers révisés (tous propres)** :
- Phase 1.0 : `cognitive_pipeline.py`, `action_factory.py`
- Phase 1.1 : `journal/models.py`, `generator.py`, `interactive.py`, `feedback.py`
- Phase 1.2 : `teams_client.py`, `teams_normalizer.py`, `teams_processor.py`, `teams.py`
- Phase 1.3 : `calendar_models.py`, `calendar_normalizer.py`, `calendar_processor.py`, `calendar.py`
- Phase 1.4 : `briefing/models.py`, `generator.py`, `display.py`
- Phase 0.7 : `api/app.py`, `deps.py`, `responses.py`, `system.py`, `briefing.py`

**Conclusion** : Code production-ready avec utilisation cohérente de `now_utc()`, bonne gestion d'erreurs, séparation des responsabilités, et documentation complète.

---

### Session 2026-01-03 (Suite 4) — Phase 0.7 API MVP Complété

**Focus** : API REST FastAPI pour exposer les fonctionnalités Scapin

**Accomplissements** :
1. ✅ `src/jeeves/api/` — Structure complète du module API
2. ✅ `src/jeeves/api/app.py` — FastAPI app factory avec CORS, exception handling (~100 lignes)
3. ✅ `src/jeeves/api/models/responses.py` — Modèles Pydantic génériques APIResponse, BriefingResponse, etc. (~180 lignes)
4. ✅ `src/jeeves/api/models/common.py` — PaginationParams, ErrorDetail (~30 lignes)
5. ✅ `src/jeeves/api/deps.py` — Dependency injection avec lru_cache (~25 lignes)
6. ✅ `src/jeeves/api/routers/system.py` — Endpoints health, stats, config (~200 lignes)
7. ✅ `src/jeeves/api/routers/briefing.py` — Endpoints morning, meeting (~140 lignes)
8. ✅ `src/jeeves/api/services/briefing_service.py` — Service async wrapper (~80 lignes)
9. ✅ Commande CLI `scapin serve` ajoutée (~40 lignes)
10. ✅ `pyproject.toml` — Dépendances FastAPI, uvicorn, python-jose
11. ✅ 20 tests unitaires (system, briefing endpoints)
12. ✅ Tous les tests passent (1396 tests, +20)
13. ✅ Ruff 0 warnings
14. ✅ Documentation mise à jour

**Architecture API** :
```
Client HTTP → FastAPI App
              ↓
         Routers (system, briefing)
              ↓
         Services (async wrappers)
              ↓
         Existing: Generators, Processors
              ↓
         Response Models → JSON
```

**Endpoints** :
- `GET /` — API info
- `GET /api/health` — Health check avec composants
- `GET /api/stats` — Statistiques
- `GET /api/config` — Configuration (secrets masqués)
- `GET /api/briefing/morning` — Briefing matinal
- `GET /api/briefing/meeting/{id}` — Briefing pré-réunion

**Commande** : `scapin serve [--host 0.0.0.0] [--port 8000] [--reload]`

---

### Session 2026-01-03 (Suite 3) — Phase 1.4 Complétée

**Focus** : Système de Briefing intelligent (morning + pre-meeting)

**Accomplissements** :
1. ✅ `src/core/config_manager.py` — Ajout BriefingConfig
2. ✅ `src/jeeves/briefing/models.py` — BriefingItem, MorningBriefing, AttendeeContext, PreMeetingBriefing (~400 lignes)
3. ✅ `src/jeeves/briefing/generator.py` — BriefingGenerator avec BriefingDataProvider protocol (~450 lignes)
4. ✅ `src/jeeves/briefing/display.py` — BriefingDisplay Rich multi-couches (~400 lignes)
5. ✅ `src/jeeves/briefing/__init__.py` — Exports module
6. ✅ Commande CLI `scapin briefing` ajoutée (~80 lignes)
7. ✅ 58 tests unitaires (models, generator, display)
8. ✅ Tous les tests passent (1308 tests, +58)
9. ✅ Ruff 0 warnings
10. ✅ Documentation mise à jour

**Architecture briefing** :
```
Sources (Email/Teams/Calendar) → PerceivedEvent normalisé
          ↓
BriefingGenerator.generate_morning_briefing()
          ↓
MorningBriefing { urgent_items, calendar_today, emails_pending, teams_unread }
          ↓
BriefingDisplay.render_morning_briefing() → Rich multi-couches
```

**Commande** : `scapin briefing --morning` ou `scapin briefing --meeting <event_id>`

---

### Session 2026-01-03 (Suite 2) — Revue Code Calendar

**Focus** : Revue approfondie du code Calendar avant Phase 1.4

**Corrections apportées** :
1. ✅ `cli.py:588-598` — **BUG FIX** : Affichage heure utilisait `occurred_at` au lieu de `metadata["start"]`
2. ✅ `graph_client.py` — Ajout méthodes `patch()` et `delete()` manquantes
3. ✅ `calendar_client.py` — `update_event()` et `delete_event()` maintenant fonctionnels
4. ✅ `calendar_client.py` — DocString corrigé avec `datetime.now(timezone.utc)`

**Qualité code** : Tous les fichiers Calendar révisés et validés production-ready

**Tests** : 1250 passent, Ruff 0 warnings sur fichiers modifiés

---

### Session 2026-01-03 (Suite) — Phase 1.3 Complétée

**Focus** : Intégration Microsoft Calendar via Graph API

**Accomplissements** :
1. ✅ `src/core/config_manager.py` — Ajout scopes Calendar + CalendarConfig
2. ✅ `src/integrations/microsoft/calendar_models.py` — CalendarEvent, CalendarAttendee (~400 lignes)
3. ✅ `src/integrations/microsoft/calendar_client.py` — Client Calendar API async (~400 lignes)
4. ✅ `src/integrations/microsoft/calendar_normalizer.py` — Normalisation → PerceivedEvent (~400 lignes)
5. ✅ `src/trivelin/calendar_processor.py` — Orchestrateur traitement Calendar (~400 lignes)
6. ✅ `src/figaro/actions/calendar.py` — Actions create/respond/task/block (~580 lignes)
7. ✅ Commande CLI `scapin calendar` ajoutée (~160 lignes)
8. ✅ 92 tests unitaires (models, normalizer, actions)
9. ✅ Tous les tests passent (1250 tests, +92)
10. ✅ Ruff 0 warnings
11. ✅ Documentation mise à jour

**Décisions techniques clés** :
- `occurred_at` pour événements calendrier = moment de notification (pas start)
- Urgence basée sur proximité temporelle (heures jusqu'à l'événement)
- Réutilisation 100% de GraphClient et MicrosoftAuthenticator

**Configuration requise** :
```bash
CALENDAR__ENABLED=true
CALENDAR__POLL_INTERVAL_SECONDS=300
CALENDAR__DAYS_AHEAD=7
# Réutilise les credentials Teams
```

**Commande** : `scapin calendar [--poll] [--briefing] [--hours] [--limit]`

---

### Session 2026-01-03 — Revue & Corrections Phase 1.2

**Focus** : Revue approfondie du code Teams avant Phase 1.3

**Corrections apportées** :
1. ✅ `models.py` — `datetime.now()` → `datetime.now(timezone.utc)` (2 occurrences)
2. ✅ `models.py` — Décodage HTML via `html.unescape()` au lieu de remplacements manuels
3. ✅ `graph_client.py` — Réutilisation du `httpx.AsyncClient` (performance)
4. ✅ `graph_client.py` — Ajout context manager (`__aenter__`/`__aexit__`)
5. ✅ `teams_normalizer.py` — Import `re` déplacé en haut du fichier
6. ✅ `teams_processor.py` — Implémentation complète de `_process_with_pipeline()`

**Amélioration performance GraphClient** :
- Avant : Nouveau `AsyncClient` créé à chaque requête HTTP
- Après : Client réutilisé via `_get_client()`, fermé proprement avec `close()`

**Tests** : 1158 passent (+1), Ruff 0 warnings

---

### Session 2026-01-02 (Suite 3) — Phase 1.2 Complétée

**Focus** : Intégration Microsoft Teams via Graph API

**Accomplissements** :
1. ✅ `src/integrations/microsoft/auth.py` — MSAL OAuth avec device code flow (~160 lignes)
2. ✅ `src/integrations/microsoft/graph_client.py` — Client Graph API async (~200 lignes)
3. ✅ `src/integrations/microsoft/models.py` — TeamsMessage, TeamsChat, TeamsSender (~220 lignes)
4. ✅ `src/integrations/microsoft/teams_client.py` — Client Teams haut niveau (~160 lignes)
5. ✅ `src/integrations/microsoft/teams_normalizer.py` — Normalisation → PerceivedEvent (~240 lignes)
6. ✅ `src/trivelin/teams_processor.py` — Orchestrateur traitement Teams (~260 lignes)
7. ✅ `src/figaro/actions/teams.py` — Actions reply/flag/create_task (~330 lignes)
8. ✅ Commande CLI `scapin teams` ajoutée (~120 lignes)
9. ✅ 116 tests unitaires (models, normalizer, client, actions)
10. ✅ Tous les tests passent (1158 tests, +116)
11. ✅ Ruff 0 warnings sur les nouveaux fichiers
12. ✅ Documentation mise à jour

**Configuration requise** :
```bash
TEAMS__ENABLED=true
TEAMS__ACCOUNT__CLIENT_ID=your-azure-app-client-id
TEAMS__ACCOUNT__TENANT_ID=your-azure-tenant-id
```

**Commande** : `scapin teams [--poll] [--interactive] [--limit] [--since]`

---

### Session 2026-01-02 (Suite 2) — Phase 1.1 Complétée

**Focus** : Journaling quotidien avec boucle de feedback Sganarelle

**Accomplissements** :
1. ✅ `src/jeeves/journal/models.py` — JournalEntry, JournalQuestion, Correction (~350 lignes)
2. ✅ `src/jeeves/journal/generator.py` — JournalGenerator avec provider protocol (~400 lignes)
3. ✅ `src/jeeves/journal/interactive.py` — Mode questionary interactif (~300 lignes)
4. ✅ `src/jeeves/journal/feedback.py` — Intégration Sganarelle UserFeedback (~250 lignes)
5. ✅ Commande CLI `scapin journal` ajoutée (~80 lignes)
6. ✅ 56 tests unitaires (models, generator, feedback)
7. ✅ Tous les tests passent (1034 tests, +56)
8. ✅ Ruff 0 warnings
9. ✅ Documentation mise à jour (ROADMAP.md, CLAUDE.md)

**Workflow journaling** :
```
scapin journal → JournalGenerator.generate(date)
              → JournalEntry (draft avec questions)
              → JournalInteractive.run() (questionary)
              → process_corrections() → Sganarelle.learn()
```

**Commande** : `scapin journal [--date YYYY-MM-DD] [--interactive] [--output FILE] [--format markdown|json]`

---

### Session 2026-01-02 (Suite) — Phase 1.0 Complétée

**Focus** : Connexion du pipeline cognitif complet

**Accomplissements** :
1. ✅ `ProcessingConfig` ajouté à `config_manager.py` (opt-in, OFF par défaut)
2. ✅ `CognitivePipeline` créé dans `src/trivelin/cognitive_pipeline.py` (~200 lignes)
3. ✅ `ActionFactory` créé dans `src/trivelin/action_factory.py` (~80 lignes)
4. ✅ Intégration dans `processor.py` avec fallback au mode legacy
5. ✅ 15 tests unitaires dans `test_cognitive_pipeline.py`
6. ✅ Tous les tests passent (978 tests, +11)
7. ✅ Ruff 0 warnings
8. ✅ Documentation mise à jour (ROADMAP.md, CLAUDE.md)

**Flux cognitif complet** :
```
Email → EmailNormalizer → ReasoningEngine (Sancho)
      → PlanningEngine (Planchet) → ActionOrchestrator (Figaro)
      → LearningEngine (Sganarelle)
```

**Activation** : `PROCESSING__ENABLE_COGNITIVE_REASONING=true`

---

### Session 2026-01-02 (Nuit) — Phase 0.6 Complétée

**Focus** : Exécution du refactoring valet

**Accomplissements** :
1. ✅ Migré `src/ai/` → `src/sancho/` (router, model_selector, templates, providers)
2. ✅ Migré `src/cli/` → `src/jeeves/` (cli, display_manager, menu, review_mode)
3. ✅ Migré `src/core/email_processor.py` → `src/trivelin/processor.py`
4. ✅ Mis à jour tous les imports (38 fichiers)
5. ✅ Tous les tests passent (967 tests)
6. ✅ Ruff 0 warnings
7. ✅ Commit poussé sur GitHub

**Structure finale des valets** :
```
src/
├── sancho/          # AI + Reasoning (~2650 lignes)
├── jeeves/          # CLI Interface (~2500 lignes)
├── trivelin/        # Event Perception (~740 lignes)
├── passepartout/    # Knowledge Base (~2000 lignes)
├── planchet/        # Planning (~400 lignes)
├── figaro/          # Execution (~770 lignes)
└── sganarelle/      # Learning (~4100 lignes)
```

---

### Session 2026-01-02 (Soir) — Plan v2.0 Complet

**Focus** : Refonte complète du plan de développement

**Accomplissements** :
1. ✅ Analysé les dépendances réelles entre phases
2. ✅ Identifié les gaps dans les spécifications existantes
3. ✅ **Restructuré entièrement le plan en 4 couches** :
   - **Couche 0** : Fondation (Phase 0.6 - Refactoring Valet)
   - **Couche 1** : Email Excellence MVP (Phases 1.0-1.1)
   - **Couche 2** : Multi-Source (Phases 1.2-1.4)
   - **Couche 3** : Intelligence Proactive (Phase 1.5)
   - **Couche 4** : Amélioration Continue (Phase 1.6)
4. ✅ **Créé spécifications fonctionnelles détaillées** pour chaque phase :
   - User Stories en format Gherkin
   - Modèles de données (dataclasses Python)
   - Diagrammes d'architecture
   - Tables de livrables avec estimations
   - Critères de succès mesurables
5. ✅ Ajouté graphe de dépendances visuel
6. ✅ Mappé les Quick Wins de DESIGN_PHILOSOPHY aux phases
7. ✅ Calendrier révisé Q1-Q4 2026

**Décisions clés** :
- Journaling divisé : Phase 1.1 (email-only MVP) + Phase 1.6 (complet multi-source)
- Teams avant Calendrier (réutilise Graph API)
- Briefings après Calendrier (nécessite les événements)
- Couches techniques (API/Web/PWA) après valeur fonctionnelle

### Session 2026-01-02 (Après-midi)

**Focus** : Révision initiale du plan de développement

**Accomplissements** :
1. ✅ Analysé état réel vs ROADMAP — Découvert Phase 0.5 à 95% (pas 20%)
2. ✅ Mis à jour ROADMAP.md avec l'état réel des modules valets
3. ✅ Tests : 967 passed (912 unit + 55 integration)

**Changement majeur** : Le plan passe d'une approche "couches techniques" (API → Web → Mobile) à une approche "valeur fonctionnelle" (Journaling → Teams → Briefings).

### Session 2026-01-02 (Matin)

**Focus** : Documentation philosophique + Corrections tests

**Accomplissements** :
1. ✅ Créé **DESIGN_PHILOSOPHY.md** — Document fondateur complet
2. ✅ Corrigé suite tests (867 → 967 tests)
3. ✅ Corrigé deadlock logger (RLock)
4. ✅ Modernisé annotations types

---

## 🚀 Commandes Rapides

```bash
# Activer venv
source .venv/bin/activate

# Tests
.venv/bin/pytest tests/ -v

# Linting
.venv/bin/ruff check src/ --fix

# Traiter emails (preview)
python scapin.py process --preview

# Révision interactive
python scapin.py review

# Démarrer API server
python scapin.py serve --reload
# → http://localhost:8000/docs
```

---

## 🤝 Travailler avec Claude Code

### Méthodologie de Développement

**Workflow structuré pour chaque session de codage :**

#### Phase 1 : Planification
Au début de chaque session, définir un découpage clair :
- Identifier les morceaux distincts à implémenter
- Prioriser par dépendances et valeur
- Créer une todo list avec les items

#### Phase 2 : Cycle par Morceau
Pour **chaque morceau** du découpage :

| Étape | Action | Objectif |
|-------|--------|----------|
| **1. Code** | Implémentation de haute qualité | Code propre, typé, documenté |
| **2. Analyse** | Revue critique du code produit | Identifier améliorations possibles |
| **3. Amélioration** | Refactoring et optimisations | Code production-ready |
| **4. Tests** | Écrire/mettre à jour les tests | Couverture complète |
| **5. Correction** | Corriger les problèmes détectés | 0 erreurs, 0 warnings |
| **6. Revue finale** | Seconde analyse qualité | Derniers ajustements |
| **7. UX** | Vérifier avec screenshots | Valider rendu visuel |
| **8. Documentation** | Documenter les changements | Traçabilité complète |
| **9. Commit** | Commit atomique | Changement isolé et décrit |

#### Phase 3 : Consolidation
Une fois **tous les morceaux** traités :
- Passe générale sur la qualité du code
- Exécution complète des tests
- Vérification UX globale
- Revue de la documentation
- Commit final et push

```
Session Start
     ↓
[Découpage en morceaux]
     ↓
┌─────────────────────────────────┐
│  Pour chaque morceau :          │
│  Code → Analyse → Amélioration  │
│  → Tests → Corrections          │
│  → Revue → UX → Doc → Commit    │
└─────────────────────────────────┘
     ↓
[Passe générale qualité]
     ↓
Commit final + Push
```

### Chargement du Contexte

**Toujours commencer par** :
1. Lire ce fichier (CLAUDE.md) — État actuel
2. Consulter **DESIGN_PHILOSOPHY.md** — Le *pourquoi*
3. Consulter ARCHITECTURE.md — Le *comment*
4. Vérifier ROADMAP.md — Le *quand*

### Standards de Qualité

**Exigence : Code parfait, chaque commit production-ready.**

| Critère | Standard | Note |
|---------|----------|------|
| **Couverture tests** | 95% | Unit + Integration + Performance |
| **Type hints** | 100% | Y compris fonctions internes |
| **Docstrings** | Complètes | Classes, méthodes, modules |
| **Ruff/Linting** | 0 warning | Code parfait, pas de compromis |
| **Thread-safety** | Vérifiée | Surtout singletons et caches |

**Ruff (Linting)** :
```bash
# Vérifier le code
.venv/bin/ruff check src/

# Auto-fix les erreurs simples
.venv/bin/ruff check src/ --fix

# Règles principales activées (voir pyproject.toml) :
# - E/W : Erreurs de style PEP8
# - F : Erreurs PyFlakes (imports inutilisés, variables non définies)
# - I : Import sorting (isort)
# - UP : Modernisation Python (type hints PEP 585)
# - B : Bug patterns (flake8-bugbear)
# - SIM : Simplifications de code
# - ARG : Arguments inutilisés
```

Conventions ruff :
- Arguments intentionnellement inutilisés : préfixer avec `_` (ex: `_frame`)
- Exceptions chaînées : `raise Exception(...) from e` ou `from None`
- Importer pour type checking : `from typing import TYPE_CHECKING`
- Simplifier conditions : retourner directement au lieu de `if x: return True; return False`

**Tests** :
- Tests unitaires pour chaque module
- Tests d'intégration pour les flux critiques
- Tests de performance pour valider les fondations (temps de réponse, mémoire)
- TDD encouragé mais pas obligatoire — tests et code peuvent être écrits en parallèle

**Commits** :
- Chaque commit doit être production-ready
- Pas de dette technique acceptée
- Code exploratoire → branche séparée, puis nettoyage avant merge

### Principes de Conception (rappel)

Toujours respecter les principes de DESIGN_PHILOSOPHY.md :

1. **Information en couches** (Niveau 1/2/3)
2. **Apprentissage progressif** (seuils appris, pas de règles rigides)
3. **Proactivité maximale** (anticiper > attendre)
4. **Qualité > Vitesse** (10-20s pour bonne décision)
5. **Construction propre** (pas de dette technique)

### Checklist Fin de Session

- [ ] Tous les tests passent
- [ ] Vérifications qualité passent
- [ ] Documentation mise à jour
- [ ] Commits poussés
- [ ] Notes de session enregistrées

---

## 🎯 Objectifs Prochaine Session

### Sprint 1 : Finir (1 item restant)

**Statut** : 95% complété (18/19 items)

**Complété** :
- ✅ Notes Git Versioning (5 endpoints)
- ✅ Éditeur Markdown complet
- ✅ Search API (2 endpoints)
- ✅ UI Components (6/6) : Modal, Tabs, Toast, ConfidenceBar, Skeleton, VirtualList
- ✅ Stats API (2 endpoints)
- ✅ Note Enrichment System (SM-2)
- ✅ API Notes Review (8 endpoints)
- ✅ UI Notes Review
- ✅ POST /api/notes/folders + GET /api/notes/folders
- ✅ Infinite Scroll + Virtualisation (@tanstack/svelte-virtual)
- ✅ Bouton briefing pré-réunion (PreMeetingModal.svelte)
- ✅ GET /api/status (status temps réel)

**Restant Sprint 1** :

| Priorité | Item | Description |
|----------|------|-------------|
| 🟠 | Calendar conflict detection | Alerte conflits calendrier |

### Référence

Voir [GAPS_TRACKING.md](docs/GAPS_TRACKING.md) pour la liste complète (45 MVP restants sur 63).

---

## 📚 Index Documentation Complet

| Document | Description | Priorité |
|----------|-------------|----------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | Principes philosophiques, fondements théoriques | 🔴 Critique |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Architecture technique, spécifications valets | 🟠 Haute |
| **[ROADMAP.md](ROADMAP.md)** | Plan développement par sprints | 🟡 Moyenne |
| **[GAPS_TRACKING.md](docs/GAPS_TRACKING.md)** | Suivi des écarts specs vs implémentation | 🟡 Moyenne |
| **[README.md](README.md)** | Vue d'ensemble projet | 🟢 Intro |
| **[BREAKING_CHANGES.md](BREAKING_CHANGES.md)** | Changements cassants, migrations | 📋 Référence |
| **[MIGRATION.md](MIGRATION.md)** | Migration PKM → Scapin | 📋 Référence |

---

**Dernière mise à jour** : 6 janvier 2026 par Claude
**Prochaine révision** : Début prochaine session
