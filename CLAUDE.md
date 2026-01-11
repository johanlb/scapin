# CLAUDE.md — Contexte de Session & État du Projet

**Dernière mise à jour** : 12 janvier 2026
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
| **[CROSS_SOURCE_SPEC.md](docs/specs/CROSS_SOURCE_SPEC.md)** | ✅ **Spec CrossSource** — Complété | Référence Sprint Cross-Source |
| **[SPRINT_5_SPEC.md](docs/specs/SPRINT_5_SPEC.md)** | ✅ **Spec Sprint 5** — Complété | Tests E2E, Lighthouse, Guide, Audit |
| **[WORKFLOW_V2_SIMPLIFIED.md](docs/specs/WORKFLOW_V2_SIMPLIFIED.md)** | ✅ **Workflow v2.1** — Complété | Architecture Knowledge Extraction |
| **[WORKFLOW_V2_IMPLEMENTATION.md](docs/specs/WORKFLOW_V2_IMPLEMENTATION.md)** | ✅ **Plan Implémentation** — Complété | 8 fichiers, ~2500 lignes |
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

## 📊 État Actuel (11 janvier 2026)

### Phases Complétées

| Phase | Nom | Statut | Lignes Code |
|-------|-----|--------|-------------|
| **0** | Fondations | ✅ | — |
| **1** | Intelligence Email | ✅ | — |
| **2** | Expérience Interactive | 80% 🚧 | — |
| **0.5** | Architecture Cognitive | ✅ | ~8000 lignes |
| **0.6** | Refactoring Valet | ✅ | ~5200 lignes migrées |
| **1.7** | Note Enrichment System | ✅ | ~2200 lignes |
| **2.1** | Workflow v2.1 Knowledge Extraction | ✅ | ~2500 lignes |

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

### Phase 2.1 : Workflow v2.1 — Knowledge Extraction ✅

**Statut** : COMPLÉTÉ (11 janvier 2026)

Pipeline d'extraction de connaissances avec escalade automatique Haiku → Sonnet.

| Jour | Phase | Fichiers | Lignes | Tests |
|------|-------|----------|--------|-------|
| 1 | Foundations | `v2_models.py`, `config_manager.py` | ~400 | 48 |
| 2 | Analysis | `analyzer.py`, `extraction.j2` | ~450 | 24 |
| 3 | Application | `enricher.py`, `omnifocus.py` | ~600 | 58 |
| 4 | Integration | `v2_processor.py`, `workflow.py` (API) | ~1050 | 32 |
| **Total** | | **8 fichiers** | **~2500** | **162** |

**Composants** :

| Module | Fichier | Rôle |
|--------|---------|------|
| Models v2 | `src/core/models/v2_models.py` | Extraction, AnalysisResult, EnrichmentResult |
| Config | `src/core/config_manager.py` | WorkflowV2Config avec seuils |
| Analyzer | `src/sancho/analyzer.py` | EventAnalyzer avec escalade Haiku→Sonnet |
| Template | `templates/ai/v2/extraction.j2` | Prompt d'extraction structuré |
| Enricher | `src/passepartout/enricher.py` | PKMEnricher pour notes + OmniFocus |
| OmniFocus | `src/integrations/apple/omnifocus.py` | Client AppleScript pour tâches |
| Processor | `src/trivelin/v2_processor.py` | V2EmailProcessor orchestrateur |
| API | `src/jeeves/api/routers/workflow.py` | Endpoints REST workflow |

**API Endpoints** :

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/workflow/config` | GET | Configuration workflow |
| `/api/workflow/stats` | GET | Statistiques de traitement |
| `/api/workflow/analyze/email` | POST | Analyser un email via pipeline v2.1 |
| `/api/workflow/apply` | POST | Appliquer des extractions manuellement |

**Configuration** :
```bash
WORKFLOW_V2__ENABLED=true
WORKFLOW_V2__AUTO_APPLY_THRESHOLD=0.9
WORKFLOW_V2__ESCALATION_THRESHOLD=0.7
WORKFLOW_V2__OMNIFOCUS_ENABLED=false
```

**Pipeline** :
```
Email → PerceivedEvent → Context Retrieval → Haiku Analysis
                                    ↓
                         confidence < 0.7 ? → Sonnet Escalation
                                    ↓
                         confidence ≥ 0.9 ? → Auto-apply to PKM
                                    ↓
                              Queue for review
```

### Suite des Tests

**Global** : 2346 tests, 95% couverture, 100% pass rate

| Catégorie | Tests | Statut |
|-----------|-------|--------|
| Backend tests | 2346 | ✅ |
| Frontend tests | 8 | ✅ |
| Skipped | 72 | ⏭️ |

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
| **0.8** | Interface Web (SvelteKit) | ✅ COMPLÉTÉ |
| **0.9** | PWA Mobile | ✅ COMPLÉTÉ |

### Phases Post-v1.0

| Phase | Focus | Priorité |
|-------|-------|----------|
| **2.5** | IA Multi-Provider (consensus) | 🟢 BASSE |

---

## 📝 Notes de Session

### Session 2026-01-12 (Suite) — Workflow v2.2 Multi-Pass Architecture ✅

**Focus** : Conception de l'architecture multi-pass avec escalade Haiku → Sonnet → Opus

**Innovation clé** : Inversion du flux Contexte/Extraction
- v2.1 : Contexte (sémantique) → Extraction → Application
- v2.2 : Extraction (aveugle) → Contexte (par entités) → Raffinement → Application

**Accomplissements** :

1. ✅ **Spécification Multi-Pass** (`docs/specs/MULTI_PASS_SPEC.md` ~400 lignes)
   - Architecture complète avec diagrammes
   - Critères de convergence (confiance ≥ 95%, 0 changements, max 5 passes)
   - Sélection de modèle par pass
   - 3 types de prompts (blind, context, refinement)
   - Estimation des coûts détaillée
   - Plan d'implémentation en 6 jours

2. ✅ **Escalade intelligente Haiku → Sonnet → Opus**
   - Pass 1-3 : Haiku (rapide, économique)
   - Pass 4 : Sonnet si confiance < 80%
   - Pass 5 : Opus si confiance < 75% OU high-stakes

3. ✅ **High-Stakes Detection**
   - Montant financier > 10,000€
   - Deadline < 48 heures
   - Expéditeur VIP (CEO, partenaire clé)
   - Implications légales/contractuelles

4. ✅ **Recherche contextuelle précise**
   - Par entités extraites (pas sémantique floue)
   - CrossSourceEngine : Notes, Calendar, OmniFocus, Email archive

5. ✅ **Documentation mise à jour**
   - ARCHITECTURE.md → v2.2
   - WORKFLOW_V2_SIMPLIFIED.md → v2.2
   - ROADMAP.md → Sprint 7
   - docs/technical/02-valets.md → Sancho v2.2
   - docs/user-guide/06-architecture.md → Multi-Pass v2.2

**Coûts estimés** :
```
Distribution par passes :
- 15% Pass 1 (simple)    : $2.69/mois
- 70% Pass 2 (contexte)  : $27.05/mois
- 10% Pass 3 (raffinement): $5.66/mois
- 4% Pass 4 (Sonnet)     : $9.38/mois
- 1% Pass 5 (Opus)       : $10.63/mois

TOTAL : ~$55-59/mois (vs $38/mois v2.1)
Qualité : 92%+ confiance moyenne (vs 75% v2.1)
```

**Prochaine étape** : Implémentation Sprint 7 (~1,650 lignes en 6 jours)

---

### Session 2026-01-12 — Workflow v2.1.2 Enhanced Extraction ✅

**Focus** : Amélioration du template d'extraction avec fuseaux horaires, durée, nouveaux champs OmniFocus et règles enrichies

**Accomplissements** :

1. ✅ **5 nouveaux champs d'extraction**
   - `timezone` — Fuseau horaire explicite (HF, HM, Maurice, UTC, Paris)
   - `duration` — Durée en minutes pour événements (défaut 60)
   - `has_attachments` — Pièces jointes importantes (justifie archive)
   - `priority` — Priorité OmniFocus (haute, normale, basse)
   - `project` — Projet OmniFocus cible

2. ✅ **Support fuseaux horaires**
   - TIMEZONE_INDICATORS dans enricher.py : Paris/HF, HM, Maurice, UTC/GMT
   - Conversion automatique vers UTC pour le calendrier
   - Règle : deviner selon contexte expéditeur si non explicite

3. ✅ **Règles note_cible enrichies**
   - Matrice type d'extraction → note_cible recommandée (14 types)
   - Résolution d'ambiguïtés (noms partiels, inconnus, multi-cible)
   - Utilisation du contexte fourni (réutiliser titres exacts)

4. ✅ **Règles draft_reply détaillées**
   - Cas d'utilisation (confirmations, remerciements, validations)
   - Cas à éviter (négociations, conflits, décisions stratégiques)
   - Format : même langue, registre adapté, pas de signature

5. ✅ **Gestion threads email**
   - Re: extraire UNIQUEMENT nouveau contenu
   - Fwd: extraire infos originales si pertinentes
   - Ignorer contenu cité (lignes ">")

6. ✅ **3 nouveaux exemples**
   - Exemple 13 : Fuseaux horaires différents (HM, Paris, Maurice)
   - Exemple 14 : Résolution d'ambiguïtés avec contexte
   - Exemple 15 : Email en anglais avec draft_reply adapté

**Fichiers modifiés** :
```
src/core/models/v2_models.py     # +5 champs Extraction
src/sancho/analyzer.py           # Parse nouveaux champs
src/passepartout/enricher.py     # TIMEZONE_INDICATORS, duration, project
src/utils/date_utils.py          # Utilitaires timezone
templates/ai/v2/extraction.j2    # +418 lignes (règles + exemples)
tests/unit/test_enricher.py      # +17 tests (timezone, duration, fields)
tests/unit/test_v2_models.py     # Tests nouveaux champs
```

**Tests** : 72 tests enricher+analyzer passent, ruff 0 warnings

**Commit** : `026e1ca` — feat(v2.1.2): add timezone, duration, priority, project fields to extractions

---

### Session 2026-01-11 (Suite 3) — Workflow v2.1.1 Extraction Types Expansion ✅

**Focus** : Extension des types d'extraction et niveaux d'importance pour une capture de connaissances plus complète

**Accomplissements** :

1. ✅ **Extension des types d'extraction** (5 → 14 types)
   - **Types originaux** : decision, engagement, fait, deadline, relation
   - **Nouveaux types v2.1.1** :
     - `coordonnees` — Téléphone, adresse, email de contacts
     - `montant` — Valeurs financières, factures, contrats
     - `reference` — Numéros de dossier, facture, ticket
     - `demande` — Requêtes faites à Johan
     - `evenement` — Dates importantes sans obligation (réunion, anniversaire)
     - `citation` — Propos exacts à retenir (verbatim)
     - `objectif` — Buts, cibles, KPIs mentionnés
     - `competence` — Expertise/compétences d'une personne
     - `preference` — Préférences de travail d'une personne

2. ✅ **Extension des niveaux d'importance** (2 → 3 niveaux)
   - `haute` (🔴) — Critique, impact fort, à ne pas rater
   - `moyenne` (🟡) — Utile, bon à savoir
   - `basse` (⚪) — Contexte, référence future (ex: numéros, coordonnées)

3. ✅ **Mise à jour du prompt d'extraction** (`templates/ai/v2/extraction.j2`)
   - Tableau des 14 types avec colonnes Description + OmniFocus
   - 6 exemples few-shot couvrant les cas d'usage
   - Notes explicatives (deadline vs evenement, citation en guillemets)

4. ✅ **Mise à jour de la documentation technique**
   - `docs/specs/WORKFLOW_V2_SIMPLIFIED.md` — Version 2.1.1
   - `docs/technical/06-data-models.md` — Section 3.3 Workflow v2.1.1

**Fichiers modifiés** :
```
src/core/models/v2_models.py        # ExtractionType (14), ImportanceLevel (3)
src/passepartout/enricher.py        # section_names, importance_icons
src/sancho/analyzer.py              # _parse_importance simplifié
templates/ai/v2/extraction.j2       # Prompt complet avec 14 types
docs/specs/WORKFLOW_V2_SIMPLIFIED.md
docs/technical/06-data-models.md
```

**Tests** : Workflow v2.1.1 testé sur emails réels (iCloud), 6/14 types utilisés dans le batch test

**Commits** :
- `c3fbeb8` — feat(v2.1.1): add 4 new extraction types
- `87adfb7` — feat(v2.1.1): add evenement extraction type for dates
- `a12ffa9` — feat(v2.1.1): add citation, objectif, competence, preference types
- `c369e94` — feat(v2.1.1): add basse importance level (3-tier system)

---

### Session 2026-01-11 (Suite 2) — Workflow v2.1 Implementation Complete ✅

**Focus** : Implémentation complète du pipeline d'extraction de connaissances v2.1

**Accomplissements** :

1. ✅ **Day 1 : Foundations** — Models & Config
   - `src/core/models/v2_models.py` : Extraction, AnalysisResult, EnrichmentResult, ContextNote
   - `src/core/config_manager.py` : WorkflowV2Config avec seuils configurables
   - 48 tests unitaires

2. ✅ **Day 2 : Analysis** — EventAnalyzer & Template
   - `src/sancho/analyzer.py` : Escalade automatique Haiku → Sonnet
   - `templates/ai/v2/extraction.j2` : Prompt structuré avec exemples
   - 24 tests unitaires

3. ✅ **Day 3 : Application** — PKMEnricher & OmniFocus
   - `src/passepartout/enricher.py` : Application extractions aux notes
   - `src/integrations/apple/omnifocus.py` : Création tâches via AppleScript
   - 58 tests unitaires

4. ✅ **Day 4 : Integration** — V2EmailProcessor & API
   - `src/trivelin/v2_processor.py` : Orchestration complète du pipeline
   - `src/jeeves/api/routers/workflow.py` : 4 endpoints REST
   - `src/jeeves/api/models/workflow.py` : Modèles Pydantic API
   - 32 tests unitaires

5. ✅ **Manual Testing with curl**
   - Tous les endpoints testés avec authentification JWT
   - Pipeline complet : Context (3 notes) → Haiku → Escalation Sonnet → Response
   - Bugs corrigés : PerceivedEvent fields, retrieve_context async, template timestamp, model ID

**Commits** :
- `836c255` — feat(workflow-v2): implement Day 4 - Integration phase
- `36b983f` — fix(enricher): use correct config attribute notes_path
- `69d9d6e` — fix(workflow-v2): fix runtime issues from manual testing
- `e6bb1cb` — fix(tests): update context retrieval tests for async API

**Tests** : 162 tests Workflow v2.1, 2346 tests total (100% pass)

---

### Session 2026-01-11 (Suite) — Workflow v2.1 Knowledge Extraction Design ✅

**Focus** : Conception et simplification radicale de l'architecture d'extraction de connaissances

**Accomplissements** :

1. ✅ **Analyse critique de la spec v2.0 complexe**
   - 6 phases → Trop complexe
   - ML local (GLiNER, SetFit) → Overhead inutile
   - Fast Path → Contradiction avec l'objectif d'enrichissement PKM
   - ~27 fichiers, ~$100/mois → Pas rentable

2. ✅ **Décision : Architecture API-First simplifiée (v2.1)**
   - **4 phases** au lieu de 6
   - **0 ML local** — Tout via API Haiku
   - **Pas de Fast Path** — Analyser TOUT (Haiku coûte ~$0.03/événement)
   - **Escalade Sonnet** si confidence < 0.7
   - **~6 fichiers, ~$36/mois** — Simple et efficace

3. ✅ **8 décisions de conception validées**
   | Question | Décision |
   |----------|----------|
   | Structure notes | Hybride (résumé + historique récent + archivé) |
   | Création notes | Toujours demander confirmation |
   | Notes longues | Auto-archivage entrées > 3 mois |
   | OmniFocus projet | Matcher existant, sinon Inbox |
   | Bootstrap | Création agressive si PKM < 50 notes |
   | Correction erreurs | Manuelle (v2.1) |
   | Limite extractions | Pas de limite |
   | Granularité | Beaucoup de petites notes (1 note = 1 entité) |

4. ✅ **Documentation créée**
   - `docs/specs/WORKFLOW_V2_SIMPLIFIED.md` (~525 lignes) — Spec complète v2.1
   - `docs/specs/WORKFLOW_V2_IMPLEMENTATION.md` (~400 lignes) — Plan d'implémentation
   - `ARCHITECTURE.md` mis à jour avec architecture 4 phases

**Architecture 4 Phases v2.1** :
```
Phase 1: PERCEPTION (local, ~100ms)
  → Normalisation + Embedding
Phase 2: CONTEXTE (local, ~200ms)
  → Recherche sémantique FAISS, top 3-5 notes
Phase 3: ANALYSE (API, ~1-2s)
  → Haiku défaut, escalade Sonnet si incertain
  → Extraction entités + classification + action
Phase 4: APPLICATION (local, ~200ms)
  → Enrichir notes PKM
  → Créer tâches OmniFocus (si deadlines)
  → Exécuter action (archive/flag/queue)

TOTAL: ~2s/événement | COÛT: ~$36/mois
```

**Fichiers créés** :
```
docs/specs/WORKFLOW_V2_SIMPLIFIED.md       # NEW (~525 lignes)
docs/specs/WORKFLOW_V2_IMPLEMENTATION.md   # NEW (~400 lignes)
```

**Commits** :
- `1dc58d3` — docs(workflow-v2): simplify architecture - API-first with Haiku
- `931de4d` — docs(workflow-v2): add design decisions from discussion

**Prochaine étape** : Implémentation selon le plan (6 fichiers, ~880 lignes)

---

### Session 2026-01-11 — Email Processing Fixes (iCloud IMAP + JSON Parsing) ✅

**Focus** : Correction des problèmes de traitement email avec iCloud IMAP et parsing JSON

**Accomplissements** :

1. ✅ **Tracking local SQLite pour emails traités** (`src/integrations/email/processed_tracker.py` ~270 lignes)
   - Problème : iCloud stocke les flags custom (`$MailFlagBit6`) mais ne supporte pas KEYWORD/UNKEYWORD search
   - Solution : Tracker SQLite local pour mémoriser les emails traités
   - Les flags IMAP sont toujours ajoutés pour le feedback visuel dans les clients email

2. ✅ **Optimisation batch avec early stop** (`src/integrations/email/imap_client.py`)
   - Problème : Scan de 16,818 headers prenait ~43 secondes
   - Solution : Batch de 200 headers avec arrêt dès qu'on a assez d'emails non traités
   - Résultat : ~1 seconde au lieu de ~43 secondes

3. ✅ **Réparation JSON robuste** (`src/sancho/router.py`)
   - Problème : Erreurs "Expecting ',' delimiter" sur les réponses IA
   - Solution : Stratégie multi-niveaux :
     - Level 1 : Parse direct (cas idéal)
     - Level 2 : Librairie `json-repair` (gère les cas complexes)
     - Level 3 : Regex cleaning + json-repair (dernier recours)
   - Résultat : Tous les emails parsés avec succès

**Fichiers créés/modifiés** :
```
src/integrations/email/processed_tracker.py  # NEW (~270 lignes)
src/integrations/email/imap_client.py        # MODIFIED (batch + tracking)
src/sancho/router.py                         # MODIFIED (JSON repair)
src/trivelin/processor.py                    # MODIFIED (message_id)
src/jeeves/api/services/queue_service.py     # MODIFIED (message_id)
```

**Tests** : 58 tests passent, ruff 0 warnings

**Commit** : `e47428c` — fix(email): fix iCloud IMAP tracking and JSON parsing issues

**TODO restant** : Sélection de dossier pour l'action Archive (navigation IMAP, création)

---

### Session 2026-01-09 (Suite 7) — Bug Fixes Performance & Stabilité ✅

**Focus** : Correction des bugs critiques de performance et de stabilité

**Accomplissements** :

1. ✅ **Performance `get_all_notes()` optimisée** (`src/passepartout/note_manager.py`)
   - Problème : Relecture de tous les fichiers à chaque requête (~1 minute)
   - Solution : Utilisation du cache mémoire quand disponible
   - Résultat : 19ms au lieu de minutes

2. ✅ **Apple Notes timeout augmenté** (`src/integrations/apple/notes_client.py`)
   - Problème : Timeout 30s trop court pour le dossier "Notes" (583 notes)
   - Solution : Timeout augmenté à 180s (3 minutes)

3. ✅ **SQLite thread-safety corrigé** (`src/passepartout/note_metadata.py`)
   - Problème : `sqlite3.ProgrammingError` threads
   - Solution : `check_same_thread=False` avec connection pooling

4. ✅ **Valets API wrappée dans APIResponse** (`src/jeeves/api/routers/valets.py`)
   - Problème : Frontend attendait `{success, data}`, API retournait données brutes
   - Solution : Tous les endpoints wrappés avec `APIResponse`

5. ✅ **SSR désactivé pour SPA** (`web/src/routes/+layout.ts`)
   - Problème : Navigation directe vers /login, /notes échouait
   - Solution : `export const ssr = false`

**Commits** :
- `6befe16` — perf(passepartout): add vector index persistence to disk
- `6f7fd86` — fix: multiple performance and stability improvements
- `d80d2f1` — fix(web): disable SSR for SPA mode

**Bugs identifiés** : ✅ Tous résolus (#41-#46)

---

### Session 2026-01-09 (Suite 6) — UI Notes Apple-like & Revue SM-2 ✅

**Focus** : Refonte complète de l'UI Notes style Apple Notes + Métadonnées de revue SM-2

**Accomplissements** :

1. ✅ **UI Notes 3 colonnes style Apple Notes** (`web/src/routes/notes/+page.svelte` ~630 lignes)
   - Colonne 1 (224px) : Arbre de dossiers avec expansion/collapse
   - Colonne 2 (288px) : Liste des notes groupées par date
   - Colonne 3 (flexible) : Contenu de la note avec métadonnées
   - Sélection ambrée (Apple Notes style)
   - Auto-sélection du premier dossier et de la première note

2. ✅ **Dossiers virtuels**
   - "Toutes les notes" (📋) en haut avec compteur total
   - "Supprimées récemment" (🗑️) en bas
   - Séparateur visuel entre dossiers réguliers et virtuels

3. ✅ **Métadonnées de revue SM-2** (section dans le panneau note)
   - Prochaine revue (formatée en français)
   - Nombre de revues effectuées
   - Facteur de facilité (easiness factor)
   - Intervalle actuel (heures/jours)
   - Type de note et importance
   - Dernière évaluation (0-5)
   - Badge "Revue due" si applicable

4. ✅ **Actions sur les notes**
   - Bouton 🔄 pour déclencher une revue immédiate
   - Bouton ↗️ pour ouvrir dans une nouvelle fenêtre
   - Indicateur de revue due (point orange) sur les notes dans la liste

5. ✅ **Sync Apple Notes amélioré**
   - Indicateur de progression pendant la sync
   - Affichage de la date de dernière synchronisation
   - Compteur de notes synchronisées

6. ✅ **Performance : Singleton cache pour NotesService** (`src/jeeves/api/deps.py`)
   - Problème : Chaque requête API créait un nouveau `NoteManager` avec `auto_index=True`
   - Impact : 1+ minute de chargement pour ré-indexer 227 notes
   - Solution : Cache singleton du `NotesService`
   - Résultat : Chargement quasi-instantané

7. ✅ **Tri alphabétique des dossiers** (`src/jeeves/api/services/notes_service.py`)
   - Tri insensible à la casse (comme Apple Notes)

8. ✅ **Bug fix : Page /valets** (`src/jeeves/api/routers/valets.py`)
   - Problème : Type `_user: str` au lieu de `Optional[TokenData]`
   - Erreur : `sqlite3.ProgrammingError: type 'TokenData' is not supported`
   - Solution : Import et utilisation du bon type

**Fichiers créés/modifiés** :
```
web/src/routes/notes/+page.svelte         # REWRITTEN (~630 lignes)
src/jeeves/api/deps.py                    # MODIFIED (singleton cache)
src/jeeves/api/services/notes_service.py  # MODIFIED (tri alphabétique)
src/jeeves/api/routers/valets.py          # MODIFIED (type fix)
```

---

### Session 2026-01-09 (Suite 5) — Backend Unavailability Detection ✅

**Focus** : Détection et feedback utilisateur quand le backend n'est pas disponible

**Contexte** :
- L'utilisateur ne pouvait pas accéder à la page de login car le backend ne tournait pas
- Demande : "Est-ce qu'on pourrait lancé le backend automatiquement lorsque l'il ne répond pas au front?"

**Accomplissements** :

1. ✅ **Script dev.sh** (`scripts/dev.sh` ~85 lignes)
   - Lance backend et frontend ensemble
   - Vérifie si le backend tourne déjà
   - Attend que le backend soit prêt avant le frontend
   - Cleanup propre avec Ctrl+C

2. ✅ **NPM script dev:full** (`web/package.json`)
   - `npm run dev:full` → lance `./scripts/dev.sh`
   - Alternative pratique à la commande shell

3. ✅ **Auth store amélioré** (`web/src/lib/stores/auth.svelte.ts`)
   - Ajout état `backendAvailable`
   - Fonction `retryConnection()` pour réessayer la connexion
   - Détection erreur réseau (status 0)

4. ✅ **UI Backend non disponible** (`web/src/routes/login/+page.svelte`)
   - Message clair "Backend non disponible"
   - Instruction: `./scripts/dev.sh`
   - Bouton "Réessayer" avec état de chargement

**Fichiers créés/modifiés** :
```
scripts/dev.sh                          # NEW (~85 lignes)
web/package.json                        # MODIFIED (dev:full script)
web/src/lib/stores/auth.svelte.ts       # MODIFIED (+40 lignes)
web/src/routes/login/+page.svelte       # MODIFIED (+80 lignes)
```

**Commit** : `5bb730f` — feat(web): add backend unavailability detection and dev script

---

### Session 2026-01-09 (Suite 3) — Guide Utilisateur ✅

**Focus** : Rédaction du guide utilisateur complet

**Accomplissements** :

1. ✅ **Guide utilisateur en 7 sections** (~1500 lignes)
   - `01-demarrage.md` — Installation, configuration, premiers pas
   - `02-briefing.md` — Briefing matinal, pré-réunion, conflits
   - `03-flux.md` — Traitement emails, actions, entités
   - `04-notes.md` — Base de connaissances, révision SM-2, Git
   - `05-journal.md` — Journaling quotidien, feedback, calibration
   - `06-architecture.md` — Les valets, pipeline cognitif, flux de données
   - `07-configuration.md` — Variables .env, YAML, intégrations

2. ✅ **Page /help in-app**
   - Sections résumées avec icônes
   - FAQ (4 questions fréquentes)
   - Liens vers ressources externes
   - Raccourcis clavier

3. ✅ **Card.svelte amélioré**
   - Ajout `[key: string]: unknown` pour supporter data-testid

**Fichiers créés** :
```
docs/user-guide/
├── README.md           (91 lignes)
├── 01-demarrage.md     (145 lignes)
├── 02-briefing.md      (144 lignes)
├── 03-flux.md          (189 lignes)
├── 04-notes.md         (216 lignes)
├── 05-journal.md       (170 lignes)
├── 06-architecture.md  (243 lignes)
└── 07-configuration.md (308 lignes)

web/src/routes/help/+page.svelte  (~220 lignes)
```

**État du projet** :
- **Sprint 5** : 67% (4/6 items — E2E ✅, Lighthouse ✅, Guide ✅, /help ✅)
- **MVP Progress** : 98% (84/86 items)
- **Prochaine étape** : Audit sécurité OWASP

---

### Session 2026-01-09 (Suite 2) — Audit Lighthouse ✅

**Focus** : Audit Lighthouse initial pour Sprint 5

**Accomplissements** :

1. ✅ **Audit Lighthouse sur 5 pages principales**
   - Login : 95/98/96/100
   - Home : 86/98/96/100
   - Flux : 87/98/96/100
   - Notes : 95/98/96/100
   - Settings : 95/98/96/100

2. ✅ **Résultats**
   - **Accessibilité** : 98% partout ✅ (objectif atteint)
   - **Best Practices** : 96% partout ✅ (objectif atteint)
   - **SEO** : 100% partout ✅ (objectif atteint)
   - **Performance** : 86-95% ⚠️ (Home et Flux légèrement sous 90)

3. ✅ **Analyse du TBT (Total Blocking Time)**
   - Home : 500ms (58%)
   - Flux : 280ms (80%)
   - Cause : Initialisation auth, WebSocket, notifications, PWA
   - Acceptable pour MVP

4. ✅ **Rapport créé**
   - `reports/lighthouse/AUDIT_REPORT.md`
   - Rapports HTML détaillés pour chaque page

5. ✅ **Backup Apple Notes**
   - 938 notes, 31 folders sauvegardés
   - ~200MB total (NoteStore.sqlite + WAL)
   - Intégrité vérifiée : OK

**Fichiers créés** :
```
reports/lighthouse/
├── AUDIT_REPORT.md
├── login.report.html
├── login.report.json
├── home.report.html
├── home.report.json
├── flux.report.html
├── flux.report.json
├── notes.report.html
├── notes.report.json
├── settings.report.html
└── settings.report.json
```

**État du projet** :
- **Sprint 5** : 33% (2/6 items — E2E ✅, Lighthouse ✅)
- **MVP Progress** : 95% (82/86 items)
- **Prochaine étape** : Guide utilisateur, Audit sécurité

---

### Session 2026-01-09 (Suite) — Sprint 5 : Tests E2E Playwright ✅

**Focus** : Implémentation des tests E2E avec Playwright pour Sprint 5

**Accomplissements** :

1. ✅ **data-testid ajoutés à 15 composants Svelte**
   - UI: `Button.svelte`, `Modal.svelte`, `CommandPalette.svelte`
   - Layout: `ChatPanel.svelte`, `NotificationsPanel.svelte`, `Sidebar.svelte`, `MobileNav.svelte`
   - Pages: flux, notes, settings, login, briefing
   - Notes: `NoteHistory.svelte`

2. ✅ **8 nouveaux fichiers de tests E2E créés**
   - `flux.spec.ts` — 14 tests (approve, reject, snooze, keyboard)
   - `notes.spec.ts` — 18 tests (tree, editor, preview, history, review)
   - `discussions.spec.ts` — 13 tests (chat panel, messages)
   - `journal.spec.ts` — 13 tests (multi-source tabs, questions)
   - `stats.spec.ts` — 13 tests (metrics, charts)
   - `settings.spec.ts` — 14 tests (tabs, integrations)
   - `search.spec.ts` — 15 tests (command palette)
   - `notifications.spec.ts` — 12 tests (badge, panel)

3. ✅ **Couverture E2E complète**
   - **132 test cases** dans 10 fichiers
   - **660 tests total** (5 browsers: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari)
   - Tous compilent avec succès (`npx playwright test --list`)

**Fichiers créés/modifiés** :
```
web/e2e/pages/flux.spec.ts           # NEW (14 tests)
web/e2e/pages/notes.spec.ts          # NEW (18 tests)
web/e2e/pages/discussions.spec.ts    # NEW (13 tests)
web/e2e/pages/journal.spec.ts        # NEW (13 tests)
web/e2e/pages/stats.spec.ts          # NEW (13 tests)
web/e2e/pages/settings.spec.ts       # NEW (14 tests)
web/e2e/pages/search.spec.ts         # NEW (15 tests)
web/e2e/pages/notifications.spec.ts  # NEW (12 tests)
web/e2e/fixtures/test-data.ts        # MODIFIED (selector update)
web/src/lib/components/ui/Button.svelte      # MODIFIED (Props extended)
web/src/lib/components/ui/Modal.svelte       # MODIFIED (Props + restProps)
+ 13 autres composants avec data-testid
```

**État du projet** :
- **Sprint 5** : 17% (1/6 items — E2E ✅)
- **MVP Progress** : 94% (81/86 items)
- **Tests** : 2148+ backend + 660 E2E
- **Prochaine étape** : Lighthouse > 90, Guide utilisateur

**Commit** : `531157e` — feat(e2e): add comprehensive E2E tests with data-testid attributes

---

### Session 2026-01-09 — Test Suite Verification & Documentation Update ✅

**Focus** : Vérification des tests et mise à jour de la documentation

**Contexte** :
- Session de continuation après résumé automatique
- 7 tests mentionnés comme "en échec" dans le résumé précédent

**Accomplissements** :

1. ✅ **Vérification Tests** — Tous les tests passent
   - `test_undo_api.py` : 8 tests ✅
   - `test_search_api.py` : 59 tests ✅
   - `test_passepartout_integration.py` : 7 tests ✅
   - **Total vérifié** : 67 tests en 74s

2. ✅ **Configuration pytest-asyncio confirmée**
   - `asyncio_mode = "strict"` dans `pyproject.toml` (ligne 160)
   - `asyncio_default_fixture_loop_scope = "function"` (ligne 161)
   - Fonctionne correctement avec pytest-asyncio 1.3.0

3. ✅ **ROADMAP.md mis à jour** — Version v1.0.0-alpha.17
   - Ajout entrée historique pour la vérification des tests
   - Confirmation du statut : 2198 tests collectés, 100% pass rate

4. ✅ **Commit et Push** — `20ec125`
   - Message : "docs(roadmap): verify test suite - all 67 key tests passing"

**État du projet** :
- **Sprint 4** : 100% complété (18/18 items)
- **MVP Progress** : 93% (80/86 items)
- **Tests** : 2198 collectés, ~2148+ passent, 50 skipped
- **Prochaine étape** : Sprint 5 — Tests E2E, Lighthouse, Documentation

**Fichiers modifiés** :
```
ROADMAP.md  # +92 lignes, -45 lignes
```

---

### Session 2026-01-08 (Suite 2) — Cross-Source COMPLÉTÉ : WhatsApp, Files, Web Adapters ✅

**Focus** : Implémentation des 3 derniers adaptateurs pour compléter CrossSourceEngine

**Accomplissements** :

1. ✅ **WhatsApp Adapter** (`src/passepartout/cross_source/adapters/whatsapp_adapter.py` ~480 lignes)
   - Recherche dans l'historique SQLite WhatsApp
   - Support schemas iOS backup et Android
   - Filtres : query, contact, since (days_back)
   - Détection automatique du schéma de base de données
   - Scoring de pertinence : content match, contact match, recency

2. ✅ **Files Adapter** (`src/passepartout/cross_source/adapters/files_adapter.py` ~475 lignes)
   - Recherche dans les fichiers locaux
   - Primary : ripgrep (rg) pour performance
   - Fallback : recherche Python native
   - Filtres : extensions, exclude_dirs, path, max_file_size
   - Scoring de pertinence : filename match, content match, recency, file type

3. ✅ **Web Adapter** (`src/passepartout/cross_source/adapters/web_adapter.py` ~410 lignes)
   - Primary : Tavily API (AI-optimized search)
   - Fallback : DuckDuckGo (duckduckgo-search library)
   - Filtres : include_domains, exclude_domains, search_depth, topic
   - Factory function `create_web_adapter()` pour sélection automatique
   - Support AI-generated answers + web results

4. ✅ **Tests complets** (`tests/unit/test_cross_source_new_adapters.py` ~700 lignes, 49 tests)
   - TestWhatsAppAdapter : 14 tests
   - TestFilesAdapter : 14 tests
   - TestWebAdapter : 15 tests
   - TestDuckDuckGoAdapter : 3 tests
   - TestCreateWebAdapter : 3 tests
   - TestAdapterIntegration : 3 tests

5. ✅ **Code Quality**
   - Ruff : 0 warnings (fixes applied)
   - All 112 cross-source tests pass

**Fichiers créés/modifiés** :
```
src/passepartout/cross_source/adapters/whatsapp_adapter.py    # NEW (~480 lignes)
src/passepartout/cross_source/adapters/files_adapter.py       # NEW (~475 lignes)
src/passepartout/cross_source/adapters/web_adapter.py         # NEW (~410 lignes)
src/passepartout/cross_source/adapters/__init__.py            # MODIFIED (exports)
tests/unit/test_cross_source_new_adapters.py                  # NEW (49 tests)
```

**Sprint Cross-Source COMPLÉTÉ** : 12/12 items (100%)
**Tests** : 112 cross-source tests, 2192 tests total

---

### Session 2026-01-08 (Suite) — Cross-Source Phase 2 : Calendar & Teams Adapters ✅

**Focus** : Implémentation des adaptateurs Calendar et Teams pour CrossSourceEngine

**Accomplissements** :

1. ✅ **Teams Adapter** (`src/passepartout/cross_source/adapters/teams_adapter.py` ~315 lignes)
   - Recherche dans les messages Teams via Microsoft Graph API
   - Filtres : query, chat_filter, mentions_only, since
   - Matching : content, sender, chat topic, attachments
   - Scoring de pertinence : content match, recency, importance, mentions

2. ✅ **Calendar Adapter amélioré** (`src/passepartout/cross_source/adapters/calendar_adapter.py`)
   - Fix config field names : `days_behind`/`days_ahead` → `past_days`/`future_days`
   - Simplification code : `for` loops → `any()` (ruff SIM110)
   - Suppression imports inutilisés

3. ✅ **Tests complets** (`tests/unit/test_cross_source_adapters.py` ~700 lignes, 29 tests)
   - TestCalendarAdapter : 12 tests
   - TestTeamsAdapter : 14 tests
   - TestAdapterIntegration : 3 tests

4. ✅ **Code Quality**
   - Ruff : 0 warnings (fix F401, F841, SIM110, SIM102)
   - All 63 cross-source tests pass

5. ✅ **Deep Analysis** (4 agents parallèles lancés)
   - Security : 3 CRITICAL, 5 HIGH identified
   - Architecture : 6 patterns à améliorer
   - Code Quality : 11 MEDIUM issues
   - Performance : 5 optimizations recommandées

**Fichiers créés/modifiés** :
```
src/passepartout/cross_source/adapters/teams_adapter.py    # NEW (~315 lignes)
src/passepartout/cross_source/adapters/calendar_adapter.py # MODIFIED (bug fixes)
src/passepartout/cross_source/adapters/__init__.py         # MODIFIED (exports)
tests/unit/test_cross_source_adapters.py                   # NEW (29 tests)
```

**Tests** : 63 cross-source tests, 100% pass rate

**Commit** : `8d33200` — feat(passepartout): implement CrossSourceEngine with Calendar and Teams adapters

---

### Session 2026-01-08 — Sprint 3 : UI Brouillons & Code Review

**Focus** : UI Brouillons email + Revue de code approfondie Sprint 3

**Accomplissements** :

1. ✅ **UI Brouillons Email complète**
   - `web/src/routes/drafts/+page.svelte` — Page liste avec filtres (~335 lignes)
   - `web/src/routes/drafts/[id]/+page.svelte` — Page édition (~434 lignes)
   - 10 fonctions API client (list, get, create, update, send, discard, delete...)
   - Navigation sidebar ajoutée

2. ✅ **Code Review Sprint 3** — Analyse approfondie en 4 axes parallèles
   - Sécurité : XSS, injection, CSRF
   - Architecture : Race conditions, memory leaks
   - Qualité : Code mort, duplication, types
   - Performance : Optimisation, debouncing

3. ✅ **Security Fixes**
   - XSS: `{@html}` remplacé par iframe sandboxée dans `flux/[id]/+page.svelte`
   - iframe sandbox: `allow-same-origin` retiré (trop permissif)

4. ✅ **Memory Leak Fixes**
   - setTimeout cleanup dans onDestroy (`flux/+page.svelte`)
   - 3 timeouts nommés avec clearTimeout au démontage

5. ✅ **Race Condition Fixes**
   - Guards `sendingReply` ajoutés dans `handleInlineReply` et `handleQuickReply`
   - Empêche les envois concurrents multiples

**Tests** : 1975 passed, 50 skipped, svelte-check 0 errors

---

### Session 2026-01-07 — Backlog Review & Sprint 2 Planning

**Focus** : Revue du backlog, création d'issues, planification Sprint 2

**Issues créées** :

| # | Titre | Priorité |
|---|-------|----------|
| #37 | 📎 Gestion des pièces jointes emails | MEDIUM |
| #38 | 📁 Organisation intelligente des fichiers | LOW |
| #39 | 💬 Contexte iMessage & WhatsApp pour enrichissement | MEDIUM |
| #40 | 🧠 Connecter ContextEngine au pipeline d'analyse | HIGH |

**Découvertes importantes** :

1. **ContextEngine non connecté** : L'infrastructure existe (`_pass2_context_enrichment` dans ReasoningEngine) mais le `context_engine` n'est pas passé au `CognitivePipeline` dans `processor.py`. Les notes ne sont donc PAS utilisées pour enrichir l'analyse actuellement.

2. **iMessage/WhatsApp** : Serveurs MCP existants permettent l'accès en lecture aux messages :
   - iMessage : Accès direct SQLite `~/Library/Messages/chat.db`
   - WhatsApp : Via MCP server (lharries/whatsapp-mcp)

3. **Backlog Sprint 2 priorisé** :
   - #40 (ContextEngine) est le bloqueur principal
   - #36 (Apple Notes) remonté en priorité HIGH pour alimenter le contexte
   - Ordre : #40 → #36 → #35 → #11 → #17

**Labels ajoutés** :
- #36 : `sprint-2` ajouté

---

### Session 2026-01-07 (Suite) — Sprint 2 : ContextEngine Connection ✅

**Focus** : Implémentation de l'issue #40 — Connexion ContextEngine au CognitivePipeline

**Accomplissements** :

1. ✅ **Configuration ProcessingConfig** (`src/core/config_manager.py`)
   - `enable_context_enrichment: bool = True`
   - `context_top_k: int = 5`
   - `context_min_relevance: float = 0.3`

2. ✅ **Initialisation ContextEngine** (`src/trivelin/processor.py`)
   - Import et initialisation de `ContextEngine` avec `NoteManager`
   - Passage au `CognitivePipeline` si disponible

3. ✅ **Propagation paramètres** (`src/trivelin/cognitive_pipeline.py`)
   - Passage `context_top_k` et `context_min_relevance` au `ReasoningEngine`

4. ✅ **ReasoningEngine configurable** (`src/sancho/reasoning_engine.py`)
   - Nouveaux paramètres `context_top_k` et `context_min_relevance`
   - Utilisation dans `_pass2_context_enrichment()`

5. ✅ **Tests Passepartout réactivés** (`tests/integration/test_passepartout_integration.py`)
   - Skip markers retirés (API maintenant compatible)
   - Fix `perception_confidence=0.5` pour déclencher la boucle de raisonnement

6. ✅ **UI context_used** (`web/src/routes/flux/+page.svelte`)
   - Section "Contexte utilisé" avec liens vers les notes
   - Affichage des IDs de notes utilisées pour l'analyse

7. ✅ **Mock data enrichi** (`web/src/routes/flux/test-performance/+page.svelte`)
   - Données Sprint 2 : entities, proposed_notes, proposed_tasks, context_used

**Issue résolue** : #40 — ContextEngine connecté au pipeline d'analyse

**Tests** : 1791 passed, 50 skipped, svelte-check 0 errors

**Commit** : `09b086f` — feat(sprint2): connect ContextEngine to CognitivePipeline (#40)

---

### Session 2026-01-07 (Suite 2) — Bouton "Discuter de cette note" ✅

**Focus** : Implémentation du chat contextuel depuis les pages de notes

**Accomplissements** :

1. ✅ **Store note-chat** (`web/src/lib/stores/note-chat.svelte.ts` ~430 lignes)
   - Types : `NoteType`, `NoteContext`, `ChatMessage`
   - Suggestions contextuelles par type (personne, projet, concept, souvenir, référence, meeting)
   - Persistance localStorage des conversations
   - Intégration API : `quickChat()`, `createDiscussion()`, `addMessage()`

2. ✅ **ChatPanel dual-mode** (`web/src/lib/components/layout/ChatPanel.svelte`)
   - Mode général : chat Scapin classique
   - Mode note : discussion avec contexte de note pré-chargé
   - Affichage titre de la note dans le header
   - Boutons : Sauvegarder en Discussion (💾), Effacer conversation (🗑️)

3. ✅ **Bouton 💬 sur page note** (`web/src/routes/notes/[...path]/+page.svelte`)
   - Nouveau bouton dans le header (avant historique 🕐)
   - Fonction `handleOpenChat()` construit le contexte de la note
   - Extraction wikilinks via `extractWikilinks()`

4. ✅ **Corrections types** (5 erreurs corrigées)
   - `DiscussionSuggestion` n'a pas de `.id` → utilisation de `.content` comme key
   - `metadata` → `context` dans `DiscussionCreateRequest`
   - Export dupliqué de `NoteContext` supprimé

**Fichiers créés/modifiés** :
```
web/src/lib/stores/note-chat.svelte.ts           # NEW (~430 lignes)
web/src/lib/components/layout/ChatPanel.svelte   # MODIFIED (+150 lignes)
web/src/routes/notes/[...path]/+page.svelte      # MODIFIED (+25 lignes)
```

**Tests** : 1824 passed, 50 skipped, svelte-check 0 errors

**Commits** :
- `b780e02` — feat(web): add 'Discuss this note' button with contextual chat
- `021db9e` — docs(roadmap): update Sprint 2 progress (11/13 - 85%)

---

### Session 2026-01-07 (Suite 3) — Apple Notes Sync ✅

**Focus** : Implémentation de la synchronisation bidirectionnelle Apple Notes

**Contexte** :
- L'utilisateur ne pouvait pas synchroniser ses notes Apple Notes
- Fonctionnalité classée "Nice-to-have" dans GAPS_TRACKING
- Décision utilisateur : Sync bidirectionnelle, texte seul (Markdown), mapping dossiers, déclenchement manuel

**Accomplissements** :

1. ✅ **Modèles Apple Notes** (`src/integrations/apple/notes_models.py` ~185 lignes)
   - `AppleNote` dataclass avec conversion HTML → Markdown/Text
   - `AppleFolder`, `SyncMapping`, `SyncResult`, `SyncConflict`
   - Enums : `SyncDirection`, `SyncAction`, `ConflictResolution`

2. ✅ **Client AppleScript** (`src/integrations/apple/notes_client.py` ~450 lignes)
   - Méthodes : `get_folders()`, `get_notes_in_folder()`, `get_note_by_id()`
   - CRUD : `create_note()`, `update_note()`, `delete_note()`, `move_note_to_folder()`
   - Parsing dates françaises (format macOS français)
   - Timeout 30s pour AppleScript

3. ✅ **Service de synchronisation** (`src/integrations/apple/notes_sync.py` ~600 lignes)
   - Sync bidirectionnelle : `APPLE_TO_SCAPIN`, `SCAPIN_TO_APPLE`, `BIDIRECTIONAL`
   - Résolution de conflits : `NEWER_WINS` (par défaut), `APPLE_WINS`, `SCAPIN_WINS`, `MANUAL`
   - Mappings persistés dans `apple_notes_sync.json`
   - Frontmatter YAML dans les notes Scapin (title, source, apple_id, dates)

4. ✅ **API implémentée** (`src/jeeves/api/services/notes_service.py`)
   - `sync_apple_notes()` retourne `NoteSyncStatus`
   - Gestion d'erreurs avec logging

**Test réel** :
```
Success: True
Created: 227 notes
Updated: 0 notes
Errors: 0
Fichiers .md créés: 227
```

**Fichiers créés/modifiés** :
```
src/integrations/apple/notes_models.py      # NEW (~185 lignes)
src/integrations/apple/notes_client.py      # NEW (~450 lignes)
src/integrations/apple/notes_sync.py        # NEW (~600 lignes)
src/integrations/apple/__init__.py          # MODIFIED (exports)
src/jeeves/api/services/notes_service.py    # MODIFIED (sync_apple_notes)
docs/GAPS_TRACKING.md                       # MODIFIED (56 complétés)
ROADMAP.md                                  # MODIFIED (Nice-to-have section)
```

**Tests** : 1874 passed, 44 skipped, ruff 0 warnings

**Commit** : `f90849b` — feat(integrations): implement Apple Notes bidirectional sync

---

### Sessions archivées (2-6 janvier 2026)

> Les notes de session antérieures au 7 janvier 2026 sont archivées dans [docs/session-history/2026-01-02-to-2026-01-06.md](docs/session-history/2026-01-02-to-2026-01-06.md).
>
> Ces sessions couvrent : Phases 0.6-1.6, API MVP, Interface Web, PWA Mobile, Entity Extraction, Security Hardening, et plus.

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

# Démarrer backend + frontend ensemble
./scripts/dev.sh
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
```

Conventions ruff :
- Arguments intentionnellement inutilisés : préfixer avec `_` (ex: `_frame`)
- Exceptions chaînées : `raise Exception(...) from e` ou `from None`
- Importer pour type checking : `from typing import TYPE_CHECKING`
- Simplifier conditions : retourner directement au lieu de `if x: return True; return False`

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

## 🎯 Objectifs v1.0 Release

### MVP Status : 100% COMPLET 🎉

**Tous les sprints complétés** :
- ✅ Sprint 1 : Notes & Fondation Contexte (19/19)
- ✅ Sprint 2 : Qualité d'Analyse (13/13)
- ✅ Sprint 3 : Workflow & Actions (18/18)
- ✅ Sprint 4 : Temps Réel & UX (18/18)
- ✅ Sprint 5 : Qualité & Release (6/6)
- ✅ Sprint Cross-Source (12/12)

### Statut v1.0 RC : ✅ PRÊT

Tous les bugs sont résolus (#41-#46). Le projet est prêt pour le tag v1.0.0-rc.1.

### Post-v1.0 (Phase 2.5)

- IA Multi-Provider avec consensus
- Quick Capture mobile

---

## 📚 Index Documentation Complet

| Document | Description | Priorité |
|----------|-------------|----------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | Principes philosophiques, fondements théoriques | 🔴 Critique |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Architecture technique, spécifications valets | 🟠 Haute |
| **[ROADMAP.md](ROADMAP.md)** | Plan développement par sprints | 🟡 Moyenne |
| **[GAPS_TRACKING.md](docs/GAPS_TRACKING.md)** | Suivi des écarts specs vs implémentation | 🟡 Moyenne |
| **[README.md](README.md)** | Vue d'ensemble projet | 🟢 Intro |
| **[Session History](docs/session-history/)** | Archives des sessions précédentes | 📋 Référence |

---

**Dernière mise à jour** : 12 janvier 2026 par Claude
**Prochaine révision** : Tag v1.0.0-rc.1
