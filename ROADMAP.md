# Scapin — Feuille de Route Produit

**Dernière mise à jour** : 17 janvier 2026
**Version** : 1.0.0-alpha.25
**Phase actuelle** : ✅ Release Candidate 1 | ✅ Sprint 7 (Multi-Pass v2.2) COMPLÉTÉ (11/11)
**Tag** : [v1.0.0-rc.1](https://github.com/johanlb/scapin/releases/tag/v1.0.0-rc.1)

---

## Résumé Exécutif

### Statut Global

**État** : ✅ v1.0.0-rc.1 RELEASED

| Métrique | Valeur |
|----------|--------|
| **Tests** | 2346+ backend + 660 E2E, 95% couverture, 100% pass rate |
| **Qualité Code** | 10/10 (Ruff 0 warnings, svelte-check 0 errors) |
| **Phases complétées** | Toutes (Sprints 1-5 + Cross-Source + Workflow v2.1) |
| **Bugs ouverts** | 0 |
| **Prochaine étape** | Phase 2.5 (Nice-to-have) |
| **Dépôt** | https://github.com/johanlb/scapin |

### Vision

> **"Prendre soin de Johan mieux que Johan lui-même."**

Transformer un processeur d'emails en **assistant personnel intelligent** avec :
- **Architecture valet** — Inspirée du valet rusé de Molière
- **Raisonnement cognitif** — Multi-passes itératif avec contexte des notes
- **Boucle Notes ↔ Email** — Analyse enrichie par le contexte, notes enrichies par l'analyse
- **Interfaces modernes** — Web + Mobile PWA

**Document fondateur** : [DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)

---

## Documentation de Référence

| Document | Rôle | Contenu |
|----------|------|---------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | Fondateur | Pourquoi — Principes, théorie, vision |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Technique | Comment — Spécifications, composants |
| **[GAPS_TRACKING.md](docs/GAPS_TRACKING.md)** | Suivi | Écarts specs vs implémentation |
| **[ROADMAP.md](ROADMAP.md)** | Opérationnel | Quand — Phases, priorités, calendrier |
| **[CLAUDE.md](CLAUDE.md)** | Session | État actuel pour Claude Code |

### Principes Directeurs

1. **Notes au centre** — Chaque email enrichit et est enrichi par les notes
2. **Qualité sur vitesse** — 10-20s pour la BONNE décision
3. **Proactivité maximale** — Anticiper, suggérer, challenger
4. **Information en couches** — Niveau 1 (30s) / Niveau 2 (2min) / Niveau 3 (complet)
5. **Construction propre** — Lent mais bien construit dès le début

---

## Phases Complétées

### Infrastructure (100%)

| Phase | Nom | Tests | Statut |
|-------|-----|-------|--------|
| 0 | Fondations | 115 | ✅ |
| 1 | Traitement Email | 62 | ✅ |
| 1.5 | Événements & Display | 44 | ✅ |
| 1.6 | Monitoring Santé | 31 | ✅ |
| 1.7 | Sélecteur Modèle IA | 25 | ✅ |
| 2 | Menu Interactif | 108 | 80% |
| 0.5 | Architecture Cognitive | 200+ | ✅ |

### Valeur Fonctionnelle (100%)

| Phase | Nom | Tests | Statut |
|-------|-----|-------|--------|
| 0.6 | Refactoring Valet | — | ✅ |
| 1.0 | Trivelin Email — Pipeline Cognitif | 15 | ✅ |
| 1.1 | Journaling & Feedback Loop | 56 | ✅ |
| 1.2 | Intégration Teams | 116 | ✅ |
| 1.3 | Intégration Calendrier | 92 | ✅ |
| 1.4 | Système de Briefing | 58 | ✅ |
| 1.6 | Journaling Complet Multi-Source | 38 | ✅ |
| 1.7 | Note Enrichment System (SM-2) | 75 | ✅ |

### Interfaces (100%)

| Phase | Nom | Tests | Statut |
|-------|-----|-------|--------|
| 0.7 | API Jeeves MVP | 20 | ✅ |
| 0.8 | Interface Web (SvelteKit) | 8 | ✅ |
| 0.9 | PWA Mobile | — | ✅ |

**Total tests** : 2346+ | **Couverture** : 95% | **Pass rate** : 100%

---

## Plan de Développement v3.1 — Notes & Analyse au Centre

> **Principe directeur** : Les notes sont au cœur de la boucle cognitive.
> Chaque email enrichit et est enrichi par le contexte des notes.

```
┌─────────────────────────────────────────────────────────────────┐
│              SPRINT 1 : NOTES & FONDATION CONTEXTE               │
│  Git Versioning + Éditeur MD + Composants UI + Search            │
│  → Base solide pour enrichir et exploiter les notes              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              SPRINT 2 : QUALITÉ D'ANALYSE                        │
│  Extraction entités + proposed_notes + Discussions               │
│  → Boucle Email ↔ Notes bidirectionnelle                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              SPRINT 3 : WORKFLOW & ACTIONS                       │
│  Events API + Undo/Snooze + Drafts                               │
│  → Actions sur emails avec contexte riche                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌═════════════════════════════════════════════════════════════════┐
║     🔥 SPRINT CROSS-SOURCE : INTELLIGENCE MULTI-SOURCES 🔥      ║
║  Emails archivés + Calendar + Teams + WhatsApp + Files + Web    ║
║  → Cerveau étendu : recherche dans TOUTES les sources           ║
║  → Hook NoteReviewer + ReasoningEngine + Discussions            ║
╚═════════════════════════════════════════════════════════════════╝
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              SPRINT 4 : TEMPS RÉEL & UX                          │
│  WebSocket + Notifications + UX avancée                          │
│  → Expérience fluide et réactive                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              SPRINT 5 : QUALITÉ & RELEASE                        │
│  E2E Tests + Lighthouse + Documentation                          │
│  → v1.0 Release Candidate                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 3.0 : NICE-TO-HAVE                            │
│  Multi-Provider IA, LinkedIn, Apple Shortcuts                    │
│  → Après MVP stable                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sprint 1 : Notes & Fondation Contexte

**Statut** : ✅ Complété (19/19 — 100%)
**Objectif** : Notes robustes et exploitables pour enrichir l'analyse
**Items** : 19 MVP

### Livrables

| Catégorie | Item | Priorité | Statut |
|-----------|------|----------|--------|
| **Notes Git Versioning** | Backend historique des versions | MVP | ✅ |
| | API: GET /notes/{id}/versions | MVP | ✅ |
| | API: GET /notes/{id}/versions/{v} | MVP | ✅ |
| | API: GET /notes/{id}/diff?v1=X&v2=Y | MVP | ✅ |
| | API: POST /notes/{id}/restore/{v} | MVP | ✅ |
| **Notes UI** | Éditeur Markdown complet | MVP | ✅ |
| **Notes API** | POST /api/notes/folders | MVP | ✅ |
| **Search** | GET /api/search (multi-types) | MVP | ✅ |
| **UI Components** | Modal.svelte | MVP | ✅ |
| | Tabs.svelte | MVP | ✅ |
| | Toast.svelte | MVP | ✅ |
| | ConfidenceBar.svelte | MVP | ✅ |
| | Skeleton.svelte | MVP | ✅ |
| | Infinite Scroll + Virtualisation | MVP | ✅ |
| **Stats** | GET /api/stats/overview | MVP | ✅ |
| | GET /api/stats/by-source | MVP | ✅ |
| **Calendar** | Bouton briefing pré-réunion | MVP | ✅ |
| | Détection et alerte conflits | MVP | ✅ |
| **API** | GET /api/status | MVP | ✅ |

### Architecture Notes Git Versioning

```
Passepartout (existant)
├── note_manager.py        # CRUD notes Markdown
├── git_versioning.py      # NOUVEAU: wrapper Git pour historique
└── version_service.py     # NOUVEAU: service API versions

API Endpoints
├── GET  /api/notes/{id}/versions      → Liste des commits
├── GET  /api/notes/{id}/versions/{v}  → Contenu à version v
├── GET  /api/notes/{id}/diff          → Diff entre 2 versions
└── POST /api/notes/{id}/restore/{v}   → Restaurer version v
```

### Valeur Délivrée

- **Rétentions tertiaires riches** (Stiegler) : Historique complet des notes
- **Search** : Retrouver le contexte pertinent pour l'analyse
- **Stats** : Mesurer la qualité de l'analyse
- **UI Components** : Bloqueurs pour UX de qualité

---

## Sprint 2 : Qualité d'Analyse

**Statut** : ✅ Complété (13/13 — 100%)
**Objectif** : Boucle Email ↔ Notes bidirectionnelle complète
**Items** : 13 MVP (13 complétés)
**Dépendance** : Sprint 1 ✅

### Livrables

| Catégorie | Item | Priorité | Statut |
|-----------|------|----------|--------|
| **Extraction Entités** | Extraction auto (personnes, dates, projets) | MVP | ✅ |
| | extracted_entities dans EmailProcessingResult | MVP | ✅ |
| | Proposition ajout entités à PKM (UI) | MVP | ✅ |
| **Données Enrichies** | proposed_tasks dans EmailProcessingResult | MVP | ✅ |
| | proposed_notes dans EmailProcessingResult | MVP | ✅ |
| **Contexte Notes** | ContextEngine connecté au CognitivePipeline (#40) | MVP | ✅ |
| **Discussions** | CRUD /api/discussions | MVP | ✅ |
| | Messages et suggestions contextuelles | MVP | ✅ |
| **Chat** | POST /api/discussions/quick (quick chat) | MVP | ✅ |
| **UX Intelligence** | Page Discussions multi-sessions | MVP | ✅ |
| | Mode traitement focus pleine page | MVP | ✅ |
| **Teams** | Filtrage par mentions directes | MVP | ✅ |
| **Notes** | UI: Bouton "Discuter de cette note" | MVP | ✅ |

### Complétés cette session (7 janvier 2026)

- ✅ **Mode traitement focus pleine page** — `/flux/focus` full-screen processing
  - `web/src/routes/flux/focus/+page.svelte` — Page focus complète (~465 lignes)
  - Bouton "Mode Focus" sur la page Flux (visible si items pending)
  - Interface épurée : progress, timer, keyboard shortcuts
  - Confirmation avant de quitter (Esc)
  - Session stats (items traités, durée)
- ✅ **Filtrage par mentions directes (Teams)** — API `?mentions_only=true`
  - `TeamsClient.get_current_user_id()` — Récupère l'ID de l'utilisateur courant
  - `TeamsClient.get_recent_messages(mentions_only=True)` — Filtre les messages
  - `GET /api/teams/messages?mentions_only=true` — Nouvel endpoint API
  - `listRecentTeamsMessages()` — Fonction frontend
- ✅ **Bouton "Discuter de cette note"** — Chat contextuel depuis la page note
  - `web/src/lib/stores/note-chat.svelte.ts` — Store pour contexte note-chat (~430 lignes)
  - ChatPanel.svelte amélioré avec mode dual (général / note-spécifique)
  - Suggestions contextuelles par type de note (personne, projet, concept, etc.)
  - Persistance conversation via localStorage
- ✅ **ContextEngine connecté** (`processor.py`, `cognitive_pipeline.py`, `reasoning_engine.py`)
- ✅ **Config context enrichment** (`config_manager.py`) — enable_context_enrichment, context_top_k, context_min_relevance
- ✅ **UI context_used** (`flux/+page.svelte`) — Affichage notes utilisées pour l'analyse
- ✅ **Tests Passepartout réactivés** — 3 tests réactivés (skip markers retirés)
- ✅ **Discussions API** — CRUD complet avec AI et suggestions contextuelles
  - `src/integrations/storage/discussion_storage.py` — JSON storage thread-safe
  - `src/jeeves/api/services/discussion_service.py` — Service async avec AI
  - `src/jeeves/api/routers/discussions.py` — 7 endpoints REST
  - 32 tests unitaires

### Complétés session précédente (6 janvier 2026)

- ✅ **EntityExtractor** (`src/core/extractors/entity_extractor.py`) — 37 tests
- ✅ **Entity models** (`src/core/entities.py`) — EntityType, Entity, ProposedNote, ProposedTask
- ✅ **EmailAnalysis enrichi** — entities, proposed_notes, proposed_tasks, context_used
- ✅ **API responses** — EntityResponse, ProposedNoteResponse, ProposedTaskResponse
- ✅ **Frontend UI entités** — Badges colorés, sections notes/tasks proposées

### Flux Email → Notes

```
Email entrant
    ↓
Trivelin (perception)
    ↓
Sancho (raisonnement) ←── Passepartout (contexte notes)
    ↓
EmailProcessingResult
├── extracted_entities: [Person, Date, Project, ...]
├── proposed_tasks: [Task suggestions for OmniFocus]
└── proposed_notes: [Note updates/creations suggested]
    ↓
UI: Propositions à valider
    ↓
Passepartout: Mise à jour notes
    ↓
Sganarelle: Apprentissage du feedback
```

### Valeur Délivrée

- **Extended Mind** : Entités extraites → fiches enrichies automatiquement
- **Enrichissement fiches** : proposed_notes → suggestions de création/mise à jour
- **Sparring partner** : Discussions contextuelles sur les notes

---

## Sprint 3 : Workflow & Actions

**Statut** : ✅ COMPLÉTÉ (18/18 — 100%)
**Objectif** : Actions sur emails avec contexte riche disponible
**Items** : 18 MVP (18 complétés)
**Dépendance** : Sprint 2 ✅

### Livrables

| Catégorie | Item | Priorité | Statut |
|-----------|------|----------|--------|
| **Events API** | GET /api/events/snoozed | MVP | ✅ |
| | POST /api/events/{id}/undo | MVP | ✅ |
| | POST /api/events/{id}/snooze | MVP | ✅ |
| | DELETE /api/events/{id}/snooze | MVP | ✅ |
| **Undo/Snooze Backend** | Historique actions pour rollback | MVP | ✅ |
| | Snooze: rappel automatique à expiration | MVP | ✅ |
| **Email Drafts** | PrepareEmailReplyAction (backend) | MVP | ✅ |
| | DraftReply dataclass | MVP | ✅ |
| | API brouillons: récupérer/modifier | MVP | ✅ |
| | UI: Affichage et édition brouillons | MVP | ✅ |
| **Email UI** | Vue détail (corps HTML/texte) | MVP | ✅ |
| | Bouton Snooze | MVP | ✅ |
| | Bouton Undo après approbation | MVP | ✅ |
| **Teams** | POST /api/teams/chats/{id}/read | MVP | ✅ |
| | POST /api/teams/chats/{id}/unread | MVP | ✅ |
| | UI: Vue détail message (thread complet) | MVP | ✅ |
| **Calendar CRUD** | POST /api/calendar/events | MVP | ✅ |
| | PUT /api/calendar/events/{id} | MVP | ✅ |
| | DELETE /api/calendar/events/{id} | MVP | ✅ |

### Décisions Techniques (8 janvier 2026)

| Item | Décision | Détails |
|------|----------|---------|
| Email HTML | DOMPurify sanitization | Intégré visuellement, nettoie les scripts |
| Snooze durées | 30min, 2h, Demain, Semaine prochaine | Options prédéfinies + custom picker |
| Calendar CRUD | Complet | Récurrence, rappels, lieu, participants |
| Undo durée | 5 minutes | Toast persistant avec countdown |
| Teams Read | Read + Unread | Flexibilité complète |
| UI Snooze/Undo | Toast après action | Snooze dans menu actions de chaque item |
| Teams Detail | Thread complet | Affiche replies et reactions |
| Calendar Tag | Catégorie 'Scapin' | Events identifiables dans Outlook |

### Complétés cette session (8 janvier 2026)

- ✅ **UI Brouillons Email** — Liste et édition complète
  - `web/src/routes/drafts/+page.svelte` — Page liste avec filtres (~335 lignes)
  - `web/src/routes/drafts/[id]/+page.svelte` — Page édition (~434 lignes)
  - 10 fonctions API client (list, get, create, update, send, discard, delete...)
  - Navigation sidebar ajoutée
- ✅ **Code Review & Security Fixes**
  - XSS fix: `{@html}` remplacé par iframe sandboxée dans flux/[id]
  - Memory leaks: setTimeout cleanup dans onDestroy (flux/+page)
  - Race conditions: Guards ajoutés dans teams reply handlers
  - iframe sandbox: `allow-same-origin` retiré (trop permissif)

### Complétés session précédente (7 janvier 2026)

- ✅ **Events API complète** — 4 endpoints Snooze/Undo
  - `src/jeeves/api/routers/events.py` — Router avec 4 endpoints (~200 lignes)
  - `src/jeeves/api/services/events_service.py` — Service async (~250 lignes)
  - `src/jeeves/api/models/events.py` — Models Pydantic
  - 24 tests unitaires
- ✅ **Storage infrastructure** — 3 nouveaux modules JSON storage
  - `src/integrations/storage/action_history.py` — Historique actions pour rollback (~200 lignes)
  - `src/integrations/storage/snooze_storage.py` — Persistance snooze + worker rappel (~300 lignes)
  - `src/integrations/storage/draft_storage.py` — Gestion brouillons email (~400 lignes)
- ✅ **Drafts API complète** — 10 endpoints
  - `src/jeeves/api/routers/drafts.py` — Router avec CRUD + generate (~320 lignes)
  - `src/jeeves/api/services/drafts_service.py` — Service async (~250 lignes)
  - `src/jeeves/api/models/drafts.py` — Models Pydantic (~100 lignes)
  - `src/figaro/actions/email.py` — PrepareEmailReplyAction mise à jour
  - 28 tests unitaires

### Architecture Drafts

```python
@dataclass
class DraftReply:
    """Brouillon de réponse préparé par Scapin"""
    email_id: str
    subject: str
    body: str
    tone: str  # formal, casual, friendly
    confidence: float
    context_used: list[str]  # IDs des notes utilisées pour le contexte
    alternatives: list[str]  # Autres formulations possibles

class PrepareEmailReplyAction(BaseAction):
    """Action Figaro pour générer un brouillon de réponse"""
    async def execute(self, email: PerceivedEvent) -> DraftReply:
        # 1. Récupérer contexte (notes sur l'expéditeur, le sujet)
        # 2. Générer brouillon avec Sancho
        # 3. Retourner DraftReply
```

### Valeur Délivrée

- **Brouillons prêts** : Quick Win #1 de DESIGN_PHILOSOPHY
- **Inbox Zero assisté** : Workflow complet avec undo/snooze
- **Contexte riche** : Brouillons générés avec le contexte des notes

### Bonus : Apple Notes Sync (Nice-to-have) ✅

Implémenté en parallèle du Sprint 3 :

- **Client AppleScript** : `src/integrations/apple/notes_client.py` (~450 lignes)
  - Lecture dossiers et notes
  - Création/modification/suppression de notes
  - Conversion HTML → Markdown
- **Service de synchronisation** : `src/integrations/apple/notes_sync.py` (~600 lignes)
  - Sync bidirectionnelle (Apple ↔ Scapin)
  - Résolution de conflits (NEWER_WINS)
  - Mapping persistant entre notes
- **Modèles** : `src/integrations/apple/notes_models.py` (~185 lignes)
  - AppleNote, AppleFolder, SyncResult, SyncMapping
- **API** : `POST /api/notes/sync` implémenté
- **Test** : 227 notes synchronisées avec succès

---

## Sprint Cross-Source : Intelligence Multi-Sources ✅ COMPLÉTÉ

**Statut** : ✅ COMPLÉTÉ — **12/12 items — 100%**
**Objectif** : Recherche intelligente cross-sources pour enrichissement et analyse
**Items** : 12 MVP (12 complétés)
**Dépendance** : Sprint 3
**Spécification** : [CROSS_SOURCE_SPEC.md](docs/specs/CROSS_SOURCE_SPEC.md)
**Tests** : 112 tests (100% pass)

> **Session 8 janvier 2026 (Final)** : Sprint Cross-Source complété !
> - Tous les adaptateurs enregistrés dans `create_cross_source_engine` factory
> - Email, WhatsApp, Files, Web adapters connectés
> - CrossSourceEngine passé à BackgroundWorker → NoteReviewer
> - Fix bug API: `sources` → `preferred_sources`

> **Session 8 janvier 2026 (Suite)** : NoteReviewer hook implémenté avec 12 nouveaux tests.
> CrossSourceEngine interroge calendar, teams, email pour enrichir le contexte de révision.
> `_load_context` appelle `_query_cross_source` et stocke les résultats dans `related_entities`.

> **Session 8 janvier 2026** : Calendar et Teams Adapters complétés avec 29 nouveaux tests.
> CrossSourceEngine intégré dans ReasoningEngine pour context enrichment.
> POST /api/search/cross-source endpoint implémenté avec 14 nouveaux tests.

> **Vision** : Permettre à Scapin d'interroger TOUTES les sources d'information disponibles
> pour enrichir les notes et améliorer l'analyse. Le Cross-Source est le cerveau étendu.

### Architecture Cross-Source

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CrossSourceEngine                               │
│                                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │   Emails    │ │  Calendar   │ │    Teams    │ │  WhatsApp   │   │
│  │  (archivés) │ │  (events)   │ │ (messages)  │ │ (history)   │   │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │
│         │               │               │               │           │
│  ┌──────┴───────────────┴───────────────┴───────────────┴──────┐   │
│  │                     Unified Search Index                      │   │
│  │          (entités, dates, personnes, projets)                │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌─────────────┐ ┌─────────┴─────────┐ ┌─────────────┐              │
│  │   Files     │ │   AI Internet     │ │    Notes    │              │
│  │  (local)    │ │   (web search)    │ │ (Passepartout)             │
│  └─────────────┘ └───────────────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │           Utilisateurs                   │
        │                                          │
        │  1. NoteReviewer (révision automatique) │
        │  2. ReasoningEngine (analyse emails)    │
        │  3. DiscussionService (chat contextuel) │
        │  4. BriefingGenerator (briefings)       │
        └─────────────────────────────────────────┘
```

### Livrables

| Catégorie | Item | Priorité | Statut |
|-----------|------|----------|--------|
| **Core Engine** | CrossSourceEngine service | MVP | ✅ |
| | Unified search interface (models, cache, config) | MVP | ✅ |
| | Query routing intelligent | MVP | ✅ |
| **Sources Existantes** | Adapter: Emails archivés (IMAP search) | MVP | ✅ |
| | Adapter: Calendrier Microsoft (Graph API) | MVP | ✅ |
| | Adapter: Calendrier iCloud (CalDAV API) | MVP | ✅ |
| | Adapter: Teams (historique messages) | MVP | ✅ |
| **Nouvelles Sources** | Adapter: WhatsApp (historique SQLite) | MVP | ✅ |
| | Adapter: Fichiers locaux (ripgrep) | MVP | ✅ |
| | Adapter: Web/Internet (Tavily API) | MVP | ✅ |
| **Intégration Pipeline** | Hook dans ReasoningEngine (Pass 2+) | MVP | ✅ |
| | Hook dans NoteReviewer | MVP | ✅ |
| | API: POST /api/search/cross-source | MVP | ✅ |

### Cas d'Usage

#### 1. Révision de Note (NoteReviewer)

```
Note "Marie Dupont" (type: PERSONNE) → Révision due
    ↓
CrossSourceEngine.search(entity="Marie Dupont", types=["email", "calendar", "teams", "whatsapp"])
    ↓
Résultats:
  - 3 emails échangés cette semaine
  - 1 réunion prévue demain
  - 2 messages Teams non lus
  - 1 conversation WhatsApp récente
    ↓
NoteReviewer: Propositions d'enrichissement
  - Ajouter "Réunion projet X prévue le 10/01"
  - Mettre à jour "Dernier contact: 08/01/2026"
```

#### 2. Analyse Email (ReasoningEngine)

```
Email de "Client Important" → Analyse Pass 1
    ↓
Confiance < 80% + sujet complexe
    ↓
CrossSourceEngine.search(
    query="Client Important projet Y budget",
    types=["notes", "email_archive", "files", "web"]
)
    ↓
Contexte enrichi:
  - Note "Client Important" avec historique
  - Emails précédents sur le projet Y
  - Fichier devis_projet_Y.pdf
  - Recherche web: actualités du client
    ↓
Pass 2 avec contexte complet → Confiance 95%
```

#### 3. Chat Contextuel (Discussions)

```
User: "Qu'est-ce qu'on avait dit avec Pierre sur le budget ?"
    ↓
CrossSourceEngine.search(
    query="Pierre budget",
    types=["email", "teams", "whatsapp", "notes", "calendar"]
)
    ↓
Scapin: "D'après mes recherches:
  - Email du 15/12: Pierre proposait 50k€
  - Teams le 20/12: Discussion ajustement à 45k€
  - Note 'Projet Alpha': Budget validé 47k€
  - WhatsApp 02/01: Pierre confirme le GO"
```

### Sources Détaillées

| Source | Accès | Données Recherchées |
|--------|-------|---------------------|
| **Emails archivés** | IMAP SEARCH | Sujet, corps, expéditeur, dates |
| **Calendrier** | Graph API | Événements, participants, notes |
| **Teams** | Graph API | Messages, mentions, fichiers partagés |
| **WhatsApp** | MCP Server | Messages texte, dates, contacts |
| **Fichiers locaux** | Filesystem + ripgrep | Contenu texte, PDF, Office |
| **Web/Internet** | AI Search (Perplexity/Tavily) | Actualités, contexte externe |
| **Notes** | Passepartout (existant) | Contenu, entités, wikilinks |

### Configuration

```yaml
# config/cross_source.yaml
cross_source:
  enabled: true

  sources:
    email_archive:
      enabled: true
      max_results: 20
      search_body: true
      date_range_days: 365

    calendar:
      enabled: true
      past_days: 90
      future_days: 30

    teams:
      enabled: true
      max_messages: 50

    whatsapp:
      enabled: true  # Requires MCP server
      mcp_server: "whatsapp-mcp"

    files:
      enabled: true
      paths:
        - "~/Documents"
        - "~/Downloads"
      extensions: [".pdf", ".docx", ".txt", ".md"]
      max_file_size_mb: 10

    web_search:
      enabled: true
      provider: "tavily"  # or "perplexity"
      api_key: ${WEB_SEARCH_API_KEY}
      max_results: 5

  # Quand déclencher la recherche cross-source
  triggers:
    note_review: true
    analysis_low_confidence: true  # < 80%
    explicit_request: true  # User demande plus d'infos
```

### Valeur Délivrée

- **Extended Mind complet** : Accès à TOUTE l'information disponible
- **Révisions enrichies** : Notes mises à jour avec contexte multi-sources
- **Analyse profonde** : Emails analysés avec tout le contexte nécessaire
- **Proactivité** : Scapin trouve l'information avant qu'on la demande

---

## Sprint 4 : Temps Réel & UX

**Statut** : ✅ COMPLÉTÉ (18/18 — 100%)
**Objectif** : Expérience fluide et réactive
**Items** : 18 MVP (18 complétés)
**Dépendance** : Sprint 3 ✅

### Livrables

| Catégorie | Item | Priorité | Statut |
|-----------|------|----------|--------|
| **WebSocket** | /ws/events - événements temps réel | MVP | ✅ |
| | /ws/discussions/{id} - chat temps réel | MVP | ✅ |
| | /ws/status - status Scapin | MVP | ✅ |
| | /ws/notifications - push | MVP | ✅ |
| **Notifications** | CRUD /api/notifications | MVP | ✅ |
| | Centre de Notifications (panneau latéral) | MVP | ✅ |
| **Valets Dashboard** | UI: Statut workers (running/idle/error) | MVP | ✅ |
| | UI: Activité NoteReviewer en cours | MVP | ✅ |
| | UI: Timeline dernières actions | MVP | ✅ |
| | API: GET /api/valets/status | MVP | ✅ |
| **UX Avancée** | Raccourcis clavier (J/K/A/R/S/E) | MVP | ✅ |
| | Quick Actions contextuelles Briefing | MVP | ✅ |
| | Mode Focus (filtre priorité) | MVP | ✅ |
| **UX Mobile** | Swipe gestures + long press | MVP | ✅ |
| **Settings** | Page Settings complète (tout configurable) | MVP | ✅ |
| **Stats** | Page Stats avec tendances 7/30j | MVP | ✅ |
| **Legacy** | Menu Interactif CLI complet | MVP | ✅ |

### Complétés (9 janvier 2026)

**Backend WebSocket** (`src/jeeves/api/websocket/`):
- `router_v2.py` — 4 endpoints WebSocket avec rate limiting
- `channels.py` — ChannelManager avec EventBus bridge (~14K lignes)
- Auth via premier message JSON

**Backend Notifications** (`src/jeeves/api/routers/notifications.py`):
- 9 endpoints CRUD complets
- `notification_service.py` — Service avec cleanup automatique (7 jours)
- Index composite SQLite pour performance

**Backend Valets** (`src/jeeves/api/routers/valets.py`):
- 4 endpoints: dashboard, metrics, valet details, activities
- Modèles complets: ValetStatus, ValetType, ValetActivity

**Frontend** (`web/src/`):
- `NotificationsPanel.svelte` — Centre de notifications (~14KB)
- `valets/+page.svelte` — Dashboard valets (~9KB)
- `flux/focus/+page.svelte` — Mode Focus (~21KB)
- `settings/+page.svelte` — Settings complets (~23KB)
- `stats/+page.svelte` — Stats avec LineChart tendances (~14KB)
- `KeyboardShortcutsHelp.svelte` — Aide raccourcis
- `QuickActionsMenu.svelte` — Actions contextuelles
- `LongPressMenu.svelte` — Menu long press mobile
- `SwipeableCard.svelte` — Gestures swipe
- `keyboard-shortcuts.ts` — Gestionnaire raccourcis

### Décisions Techniques (9 janvier 2026)

| Composant | Décision | Détails |
|-----------|----------|---------|
| **WebSocket Events** | Tout diffuser | Emails, Teams, calendar, queue, notes reviews, processing status |
| **WS Reconnexion** | Exponential backoff | 1s → 2s → 4s → 8s → ... → 30s max |
| **Notifications** | In-app + persistées | Centre de notifications, stockées en base, marquables comme lues |
| **Notif UI** | Panel latéral droit | Slide-in depuis la droite (comme ChatPanel) |
| **Notif Rétention** | 7 jours | Purge automatique après 7 jours |
| **Notif Groupement** | Chronologique | Liste simple triée par date, pas de groupement |
| **Valets Dashboard** | Simple | Statut par valet, tâche en cours, dernières actions |
| **Stats Pipeline** | Temps + Volume + Tendances | Métriques + graphiques évolution 7/30 jours |
| **Raccourcis clavier** | Navigation + Actions | J/K navigation, A approuver, R rejeter, S snooze, E éditer, Cmd+K recherche |
| **Swipe mobile** | Swipe + long press | Swipe pour actions rapides, long press pour menu contextuel |
| **Mode Focus** | Notifs + Filter priorité | Masque tout sauf items haute priorité/urgence |
| **Quick Actions** | Contextuelles | Actions différentes selon l'état (inbox vide/pleine, notes dues/à jour) |
| **Settings** | Tout configurable | Connexions, IA, Processing, Valets, Développeur (logs, debug) |
| **Menu CLI** | Finir maintenant | Compléter le menu interactif dans ce sprint |

### Ordre d'Implémentation (COMPLÉTÉ ✅)

```
1. WebSocket Infrastructure ✅
   ├── Backend: 4 endpoints WS (/ws/events, discussions, status, notifications)
   ├── Frontend: Store WebSocket avec exponential backoff
   └── Intégration: EventBus → WebSocket broadcast

2. Notifications ✅
   ├── Backend: CRUD API + Storage SQLite
   ├── Frontend: Panel latéral + Badge compteur
   └── Intégration: WebSocket → Notifications

3. Valets Dashboard ✅
   ├── Backend: GET /api/valets/status
   ├── Frontend: Page/Widget dashboard valets
   └── Intégration: WebSocket status updates

4. UX Avancée ✅
   ├── Raccourcis clavier globaux
   ├── Quick Actions contextuelles
   └── Mode Focus

5. UX Mobile ✅
   └── Swipe gestures + long press menu

6. Settings ✅
   └── Page complète avec tous les onglets

7. Stats ✅
   └── Page avec graphiques tendances

8. CLI ✅
   └── Menu interactif complet (684 lignes)
```

### Valets Dashboard (Design)

```
┌─────────────────────────────────────────────────────────────────┐
│                    L'Équipe Scapin                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Trivelin │  │  Sancho  │  │Passepartout│ │ Planchet │        │
│  │   IDLE   │  │   BUSY   │  │  REVIEW   │  │   IDLE   │        │
│  │          │  │ Email #42│  │ Note #17  │  │          │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐  │
│  │  Figaro  │  │Sganarelle│  │ Background Worker            │  │
│  │   EXEC   │  │  LEARN   │  │ ████████░░ 8/50 reviews/jour │  │
│  │ Archive  │  │ Pattern  │  │ Session: 2:34/5:00           │  │
│  └──────────┘  └──────────┘  └──────────────────────────────┘  │
│                                                                  │
│  Dernière activité:                                              │
│  • 14:23 Sancho: Email analysé → Archive/Travail (conf: 92%)   │
│  • 14:21 Passepartout: Note "Marie Dupont" révisée (q=4)       │
│  • 14:20 Figaro: Email #41 archivé                              │
└─────────────────────────────────────────────────────────────────┘
```

### Raccourcis Clavier

| Raccourci | Action | Contexte |
|-----------|--------|----------|
| `J` / `K` | Item suivant / précédent | Listes (Flux, Notes, etc.) |
| `A` | Approuver | Item sélectionné dans Flux |
| `R` | Rejeter | Item sélectionné dans Flux |
| `S` | Snooze | Item sélectionné dans Flux |
| `E` | Éditer | Item sélectionné |
| `Enter` | Ouvrir détail | Item sélectionné |
| `Escape` | Fermer / Retour | Modal, panel, détail |
| `Cmd+K` | Recherche globale | Global |
| `Cmd+N` | Nouvelle note | Global |
| `Cmd+F` | Mode Focus toggle | Global |
| `?` | Aide raccourcis | Global |

### Swipe Gestures Mobile

| Geste | Action |
|-------|--------|
| Swipe gauche | Rejeter / Archiver |
| Swipe droite | Approuver / Valider |
| Long press | Menu contextuel (snooze, éditer, détails...) |

### Quick Actions Contextuelles

| État | Actions affichées |
|------|-------------------|
| Inbox non vide | "Traiter le courrier" (primary) |
| Inbox vide | "Tout est traité ✓" (disabled) |
| Notes dues > 0 | "Réviser X notes" |
| Notes à jour | "Notes à jour ✓" |
| Mode Focus OFF | "Activer Focus" |
| Mode Focus ON | "Désactiver Focus" |

### Valeur Délivrée

- **Proactivité maximale** : Notifications temps réel via WebSocket
- **Expérience fluide** : Raccourcis clavier, feedback instantané
- **Mobile-first** : Gestures complets, responsive
- **Transparence** : Dashboard valets, on voit Scapin travailler

---

## Sprint 5 : Qualité & Release

**Statut** : ✅ COMPLÉTÉ — 6/6 items (100%)
**Objectif** : v1.0 Release Candidate
**Items** : 6 MVP complétés
**Dépendance** : Sprint 4 ✅
**Spécification** : [SPRINT_5_SPEC.md](docs/specs/SPRINT_5_SPEC.md)

### Décisions Validées (9 janvier 2026)

| Aspect | Décision |
|--------|----------|
| **Tests E2E** | ✅ 132 tests × 5 browsers = 660 tests |
| **Backend E2E** | Backend réel local (pas de mock) |
| **Lighthouse** | ✅ A11y 98%, BP 96%, SEO 100%, Perf 86-95% |
| **Guide Format** | Markdown dans /docs + Page /help in-app |
| **Guide Langue** | Français uniquement |
| **Guide Contenu** | Complet + Architecture (valets, flux de données) |
| **Quick Capture** | Reporté post-v1.0 |
| **Audit Sécurité** | OWASP Top 10 complet, pip-audit, npm audit |

### Livrables

| Catégorie | Item | Priorité | Statut |
|-----------|------|----------|--------|
| **Tests E2E** | Playwright setup + 10 pages + flows | MVP | ✅ 660 tests |
| **Performance** | Lighthouse audit (A11y 98%, BP 96%, SEO 100%, Perf 86-95%) | MVP | ✅ |
| **Documentation** | Guide utilisateur complet (7 sections, ~1500 lignes) | MVP | ✅ |
| **Documentation** | Page /help in-app | MVP | ✅ |
| **Sécurité** | Audit OWASP + dépendances | MVP | ✅ |
| **Cleanup** | Revue code finale | MVP | ✅ |

### Ordre d'Exécution

```
1. Tests E2E Playwright
   ├── Setup (config, fixtures, auth)
   ├── Pages (login, briefing, flux, notes, journal, discussions, stats, settings, valets)
   ├── Features (search, keyboard, notifications, responsive)
   └── Flows (email-workflow, note-enrichment, session-complete)

2. Lighthouse > 90
   ├── Audit initial (baseline)
   ├── Optimisations
   └── Audit final (validation)

3. Guide Utilisateur
   ├── docs/user-guide/ (7 sections)
   └── Page /help in-app

4. Audit Sécurité
   ├── OWASP Top 10 checklist
   └── pip-audit + npm audit + bandit
```

### Pages E2E à Couvrir

| Page | Route | Priorité |
|------|-------|----------|
| Login | `/login` | Critique |
| Briefing | `/` | Critique |
| Flux | `/flux` | Critique |
| Flux Focus | `/flux/focus` | Haute |
| Flux Détail | `/flux/[id]` | Haute |
| Notes | `/notes` | Haute |
| Note Détail | `/notes/[...path]` | Haute |
| Notes Review | `/notes/review` | Haute |
| Brouillons | `/drafts` | Moyenne |
| Journal | `/journal` | Moyenne |
| Discussions | `/discussions` | Moyenne |
| Stats | `/stats` | Moyenne |
| Settings | `/settings` | Moyenne |
| Valets | `/valets` | Moyenne |

### Critères de Release v1.0 RC

- [x] Tests E2E passent (desktop + mobile, 3 navigateurs) — 660 tests ✅
- [x] Lighthouse audité (A11y 98%, BP 96%, SEO 100%, Perf 86-95%) ✅
- [x] Guide utilisateur complet (7 sections + /help in-app) ✅
- [x] Zéro bug critique connu ✅
- [x] Audit sécurité validé (0 CRITICAL/HIGH non résolu) ✅
- [x] 86 items MVP complétés (100%) ✅

---

## Sprint 7 : Workflow v2.2 — Multi-Pass Extraction 🌟

**Statut** : ✅ COMPLÉTÉ — 11/11 items (100%)
**Objectif** : Améliorer la qualité d'extraction via analyse multi-passes et escalade intelligente
**Spécification** : [MULTI_PASS_SPEC.md](docs/specs/MULTI_PASS_SPEC.md) ⭐ NEW
**Workflow** : [WORKFLOW_V2_SIMPLIFIED.md](docs/specs/WORKFLOW_V2_SIMPLIFIED.md) (v2.2)

### Vision v2.2

> **Innovation clé** : Inversion du flux Contexte/Extraction

Le workflow v2.1 cherchait le contexte AVANT l'extraction (recherche sémantique floue).
Le workflow v2.2 inverse ce flux : extraction d'abord (aveugle), puis recherche de contexte
par **entités extraites** (précis), puis raffinement itératif jusqu'à confiance 95%.

### Architecture Multi-Pass

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW V2.2 MULTI-PASS                              │
├─────────────────────────────────────────────────────────────────────────┤
│  PERCEPTION: Email → PerceivedEvent                              [LOCAL] │
│                                   ↓                                      │
│  PASS 1: Extraction AVEUGLE (sans contexte)                      [HAIKU] │
│    → Entités + action suggérée | Confiance: 60-80%                      │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 95%? │──→ APPLICATION (15% des emails)              │
│            └──────┬──────┘                                              │
│                   ↓                                                      │
│  RECHERCHE CONTEXTUELLE: Par entités → Notes, Calendar, OmniFocus       │
│                                   ↓                                      │
│  PASS 2-3: Raffinement avec contexte                             [HAIKU] │
│    → "Marc" → "Marc Dupont (CFO)" | Confiance: 80-95%                   │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 90%? │──→ APPLICATION (70% des emails)              │
│            └──────┬──────┘                                              │
│                   ↓ (conf < 80%)                                         │
│  PASS 4: Escalade Sonnet | Confiance: 85-95%                   [SONNET]  │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 90%? │──→ APPLICATION (10% des emails)              │
│            └──────┬──────┘                                              │
│                   ↓ (conf < 75% OU high-stakes)                          │
│  PASS 5: Escalade Opus (expert) | Confiance: 90-99%              [OPUS]  │
│    → Montant > 10k€, deadline < 48h, VIP sender                         │
│                                   ↓                                      │
│  APPLICATION: PKM, OmniFocus, Calendar, Actions                          │
│                                                                          │
│  DISTRIBUTION: 15% P1 | 70% P2 | 10% P3 | 4% P4 | 1% P5                 │
│  COÛT: ~$0.0043/événement | ~$59/mois (13,800 emails)                   │
│  CONFIANCE MOYENNE: 92%+ (vs 75% en v2.1)                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Livrables Sprint 7

| Catégorie | Item | Fichier | Statut |
|-----------|------|---------|--------|
| **Spécification** | Architecture Multi-Pass + ADRs | `docs/specs/MULTI_PASS_SPEC.md` | ✅ |
| **Convergence** | Logique arrêt, seuils, escalade | `src/sancho/convergence.py` | ✅ |
| **Contexte** | ContextSearcher wrapper | `src/sancho/context_searcher.py` | ✅ |
| **Templates** | Structure Jinja2 + TemplateRenderer | `templates/ai/v2/` + `src/sancho/template_renderer.py` | ✅ |
| **Templates** | Pass 1 blind extraction | `templates/ai/v2/pass1_blind_extraction.j2` | ✅ |
| **Templates** | Pass 2 contextual refinement | `templates/ai/v2/pass2_contextual_refinement.j2` | ✅ |
| **Templates** | Pass 4 deep reasoning | `templates/ai/v2/pass4_deep_reasoning.j2` | ✅ |
| **Analyse** | MultiPassAnalyzer | `src/sancho/multi_pass_analyzer.py` | ✅ |
| **Intégration** | V2EmailProcessor + MultiPassAnalyzer | `src/trivelin/v2_processor.py` | ✅ |
| **Tests** | Tests unitaires Sprint 7 (82 tests) | `tests/unit/test_convergence.py`, `test_context_searcher.py`, `test_template_renderer.py` | ✅ |
| **Tests** | Tests intégration Sprint 7 (20 tests) | `tests/integration/test_multi_pass.py` | ✅ |

### Décisions de Conception v2.2

| Question | Décision |
|----------|----------|
| Ordre des passes | Extraction → Contexte → Raffinement (inversé vs v2.1) |
| Critère convergence | Confiance ≥ 95% OU 0 changements OU max 5 passes |
| Escalade Sonnet | Confiance < 80% après pass 3 |
| Escalade Opus | Confiance < 75% OU high-stakes détecté |
| High-stakes | Montant > 10k€, deadline < 48h, VIP sender |
| Recherche contexte | Par entités extraites (précis, pas sémantique) |
| Coopération modèles | Haiku rapide → Sonnet profond → Opus expert |

### Types d'Information Extraits (14 types)

| Type | Exemple | Destination |
|------|---------|-------------|
| **Fait** | "Marie est promue directrice" | Note personne |
| **Décision** | "Budget approuvé: 50K€" | Note projet + OmniFocus |
| **Engagement** | "Marc livrera lundi" | Note personne + OmniFocus |
| **Deadline** | "Rapport pour vendredi" | OmniFocus |
| **Événement** | "Réunion Q2 le 15 janvier" | Calendar + Note |
| **Relation** | "Marc rejoint Projet Alpha" | Note personne + projet |
| **Coordonnées** | "Nouveau tel: 06..." | Note personne |
| **Montant** | "Contrat de 50k€/an" | Note entreprise |
| **Référence** | "Voir doc technique v2" | Note concept |
| **Demande** | "Peux-tu m'envoyer le rapport ?" | OmniFocus |
| **Citation** | "Le CEO a dit : on double le budget" | Note personne |
| **Objectif** | "Objectif Q1 : 100k utilisateurs" | Note projet |
| **Compétence** | "Marie maîtrise React" | Note personne |
| **Préférence** | "Marc préfère les réunions le matin" | Note personne |

### Plan d'Implémentation v2.2

| Jour | Focus | Fichiers | Lignes |
|------|-------|----------|--------|
| 1 | Modèles & Config | PassResult, ConvergenceCriteria | ~200 |
| 2 | MultiPassAnalyzer | Boucle itérative, convergence | ~400 |
| 3 | Templates | 3 prompts Jinja2 | ~300 |
| 4 | EntityContextSearcher | Recherche par entités | ~250 |
| 5 | ModelEscalator | High-stakes, escalade | ~200 |
| 6 | Intégration & Tests | CognitivePipeline, tests | ~300 |

**Total** : ~1,650 lignes en ~6 jours

### Coûts Estimés v2.2

```
460 événements/jour × 30 jours = 13,800 événements/mois

Distribution par passes :
- 15% (2,070) convergent en Pass 1 : 2,070 × $0.0013 = $2.69
- 70% (9,660) convergent en Pass 2 : 9,660 × $0.0028 = $27.05
- 10% (1,380) convergent en Pass 3 : 1,380 × $0.0041 = $5.66
-  4% (552) escaladent à Sonnet   : 552 × $0.017 = $9.38
-  1% (138) escaladent à Opus     : 138 × $0.077 = $10.63

TOTAL : ~$55.41/mois (vs $38/mois v2.1)
Qualité : 92%+ confiance moyenne (vs 75% v2.1)
ROI : +55% coût pour +23% qualité
```

### Métriques de Succès v2.2

| Métrique | v2.1 | v2.2 Objectif |
|----------|------|---------------|
| Confiance moyenne | 75% | 92%+ |
| Passes moyens | 1.1 | 1.95 |
| Coût/mois | $38 | $59 |
| Extractions précises | 70% | 90%+ |
| High-stakes bien traités | N/A | 99%+ |
| Temps moyen/email | 1.5s | 2.5s |

---

## Phase 3.0 : Nice-to-Have (53 items)

Après MVP stable, par ordre de valeur :

### Cognitif (3 items)

| Item | Description | Statut |
|------|-------------|--------|
| Multi-Provider Consensus | Pass 4 avec vote multi-IA (Claude + GPT-4 + Mistral) | ⬜ |
| Révision espacée | **SM-2 implémenté** (7 modules Passepartout) | ✅ |
| Continuity Detector amélioré | Meilleure détection des threads | ⬜ |

### Intégrations (6 items)

| Item | Description |
|------|-------------|
| LinkedIn messagerie | Lecture messages directs (priorité basse) |
| WhatsApp | Question ouverte (API limitée) |
| Apple Shortcuts | Bidirectionnel (v1.1) |
| OneDrive/SharePoint | Lecture (v1.2) |
| Transcriptions réunion | Input processing (v1.0) |
| Planner | Lecture contexte équipe |

### Notes Avancées (5 items)

| Item | Description | Statut |
|------|-------------|--------|
| Apple Notes Sync | Synchronisation bidirectionnelle | ✅ Complété |
| Entity Manager | Gestion des entités extraites | ⬜ |
| Relationship Manager | Graphe NetworkX des relations | ⬜ |
| Templates notes | CRUD /api/templates | ⬜ |
| Quick Capture | Cmd+Shift+N | ⬜ |

### UX Avancée (7 items)

| Item | Description |
|------|-------------|
| Prévisualisation liens | Hover [[]] |
| Bulk Actions | Sélection multiple + actions |
| Filtres sauvegardés | CRUD /api/filters |
| Activity Log | Timeline UI |
| Tags personnalisés | Colorés |
| Vue calendrier | Mensuelle/hebdomadaire |
| Support channels Teams | Pas juste chats 1:1 |

### Futures (6 items)

| Item | Description |
|------|-------------|
| Prédictions Scapin | "Demain tu auras probablement 8 emails" |
| Résumé Audio Briefing | TTS |
| Mode vocal | Dialogues audio |
| Stats avancées | Confiance, tokens, learning patterns |
| Rapports | CRUD + export PDF/MD |
| Valets Pipeline | GET /api/valets (métriques) |

---

## Calendrier

### Janvier 2026

| Semaine | Sprint | Focus |
|---------|--------|-------|
| S2 (6-12) | Sprint 1 | Notes Git Versioning + UI Components |
| S3 (13-19) | Sprint 1 | Search + Stats + Calendar |

### Février 2026

| Semaine | Sprint | Focus |
|---------|--------|-------|
| S4 (20-26 jan) | Sprint 2 | Extraction entités + proposed_notes |
| S5 (27 jan - 2 fév) | Sprint 2 | Discussions + Chat rapide |
| S6 (3-9) | Sprint 3 | Events API + Undo/Snooze |
| S7 (10-16) | Sprint 3 | Email Drafts |

### Mars 2026

| Semaine | Sprint | Focus |
|---------|--------|-------|
| S8 (17-23 fév) | Sprint 4 | WebSocket + Notifications |
| S9 (24 fév - 2 mars) | Sprint 4 | UX Avancée |
| S10 (3-9) | Sprint 5 | Tests E2E + Lighthouse |
| S11 (10-16) | Sprint 5 | Documentation + Release |

**Livrable** : v1.0 Release Candidate mi-mars 2026

---

## Progression

### Vue d'Ensemble

```
=== COMPLÉTÉ ===
Infrastructure:    ████████████████████ 100% ✅
Valeur Fonct.:     ████████████████████ 100% ✅
Interfaces:        ████████████████████ 100% ✅

=== MVP v1.0 COMPLÉTÉ ===
Sprint 1 (Notes):  ████████████████████ 100% ✅ (19/19)
Sprint 2 (Analyse):████████████████████ 100% ✅ (13/13)
Sprint 3 (Actions):████████████████████ 100% ✅ (18/18)
Cross-Source 🔥:   ████████████████████ 100% ✅ (12/12)
Sprint 4 (UX):     ████████████████████ 100% ✅ (18/18)
Sprint 5 (Release):████████████████████ 100% ✅ (6/6)

=== POST-MVP ===
Sprint 6 (v2.1):   ░░░░░░░░░░░░░░░░░░░░   0% 🚧 (0/6 — EN COURS)

=== NICE-TO-HAVE ===
Phase 3.0:         ░░░░░░░░░░░░░░░░░░░░   0% 📋

Global MVP:        █████████████████████ 94% (81 MVP complétés sur 86)
                   → 5 items restants (Lighthouse, Doc, Sécurité)
```

### Items par Sprint

| Sprint | Items MVP | Complétés | Statut |
|--------|-----------|-----------|--------|
| Sprint 1 | 19 | 19 | ✅ 100% |
| Sprint 2 | 13 | 13 | ✅ 100% |
| Sprint 3 | 18 | 18 | ✅ 100% |
| **Cross-Source** 🔥 | **12** | **12** | ✅ **100%** |
| Sprint 4 | 18 | 18 | ✅ 100% |
| Sprint 5 | 6 | 6 | ✅ 100% |
| **Total MVP** | **86** | **86** | ✅ **100%** |
| **Sprint 6 (v2.1)** 🌟 | **6** | **0** | 🚧 **0%** |
| Phase 3.0 | 53 | 3 | 📋 Après v2.1 |

---

## Métriques de Succès

### MVP (Sprints 1-5)

| Objectif | Indicateur | Cible |
|----------|------------|-------|
| Notes robustes | Git versioning fonctionnel | 100% |
| Analyse enrichie | Entités extraites par email | > 80% |
| Brouillons prêts | Drafts générés pour emails "action needed" | 100% |
| Temps gagné | Réduction temps traitement inbox | > 50% |
| Qualité code | Ruff 0 warnings | ✅ |
| Tests | Couverture | > 90% |
| Performance | Lighthouse score | > 80 |

### Long Terme

| Objectif | Indicateur |
|----------|------------|
| Charge mentale réduite | Temps gagné par semaine |
| Graphe connaissances | 1000+ notes interconnectées |
| Autonomie Scapin | Taux d'approbation > 95% |
| Zéro perte données | Backup Git automatique |

---

## Principes de Développement

### Qualité Code

1. **Tests d'abord** : Cible 90%+ couverture
2. **Qualité 10/10** : Ruff 0 warnings
3. **Type hints** : 100% des fonctions
4. **Docstrings** : Toutes les classes et méthodes publiques

### Architecture

1. **Notes au centre** : Tout enrichit et utilise les notes
2. **API-First** : Toute fonctionnalité exposée via API
3. **Événementiel** : EventBus pour découplage
4. **Valets spécialisés** : Chaque module a sa responsabilité

### Stack Technique

- **Backend** : Python 3.11+, FastAPI, Pydantic
- **Frontend** : SvelteKit, TailwindCSS v4, TypeScript
- **IA** : Claude (Anthropic) — Multi-provider en Phase 3.0
- **Stockage** : SQLite, Markdown+Git, FAISS
- **Tests** : pytest, Playwright (E2E)

---

## Historique des Versions

- **v1.0.0-alpha.25** (2026-01-17) : Task Checkbox Toggle for OmniFocus Proposals
  - **Checkboxes interactives** : Les tâches OmniFocus proposées peuvent être cochées/décochées
  - **Nouveau champ** : `manually_approved: boolean | null` dans `ProposedTask`
  - **Logique tri-état** : `null` = auto (≥90% confiance), `true` = forcé, `false` = rejeté
  - **Store queue** : Nouvelles fonctions `toggleNoteApproval()` et `toggleTaskApproval()`
  - **Fichiers modifiés** :
    - `web/src/lib/api/client.ts` — Interface TypeScript mise à jour
    - `web/src/lib/stores/queue.svelte.ts` — Fonctions de toggle ajoutées
    - `web/src/routes/flux/+page.svelte` — Handlers de checkbox connectés
  - **Commit** : `f35658e`

- **v1.0.0-alpha.24** (2026-01-17) : Alias Matching in ContextEngine (Phase 2)
  - **Matching par aliases** : ContextEngine utilise maintenant les aliases pour trouver les notes
  - **Approche en 2 phases** :
    1. Matching exact par alias (haute précision) via `find_note_by_alias()`
    2. Recherche sémantique vectorielle (couverture large) - comportement existant
  - **Exemple** : "Marc" dans un email → trouve "Marc Dupont" si alias défini
  - **Déduplication** : Évite les doublons entre alias et sémantique
  - **Metadata enrichi** : Nouveau champ `match_type`: `alias_exact` ou `semantic`
  - **Logging amélioré** : Compteurs alias_matches vs semantic_matches
  - **Tests** : 26 tests ContextEngine (+2 nouveaux pour alias)
  - **Commit** : `28b0212`

- **v1.0.0-alpha.23** (2026-01-17) : Enriched Frontmatter Schema (Phase 1)
  - **Schéma frontmatter enrichi** : Dataclasses typées pour meilleure compréhension IA
  - **5 nouveaux enums** : Relation, RelationshipStrength, ProjectStatus, EntityType, Category
  - **Dataclasses par type** :
    - PersonneFrontmatter : relation, organization, email, phone, projects, last_contact
    - ProjetFrontmatter : status, stakeholders, budget_range, target_date
    - EntiteFrontmatter : entity_type, contacts, website, country
    - ReunionFrontmatter : participants, agenda, decisions, action_items
    - ActifFrontmatter : asset_type, location, acquisition_date, current_status
  - **Helper classes** : PendingUpdate, Stakeholder, LinkedSource, Contact
  - **FrontmatterParser** : YAML → dataclasses typées avec détection automatique du type
  - **Index d'aliases** : Recherche rapide par alias (ex: "Marc" → "Marc Dupont")
  - **Nouvelles méthodes NoteManager** :
    - `get_typed_frontmatter()`, `get_note_with_typed_frontmatter()`
    - `find_note_by_alias()`, `get_aliases_index()`, `get_all_aliases()`
    - `get_persons_with_relation()`
  - **Fichiers créés** :
    - `docs/specs/FRONTMATTER_ENRICHED_SPEC.md` (~400 lignes)
    - `src/passepartout/frontmatter_schema.py` (~555 lignes)
    - `src/passepartout/frontmatter_parser.py` (~454 lignes)
    - `tests/unit/test_frontmatter_parser.py` (23 tests)
  - **Tests** : 49 tests (26 NoteManager + 23 FrontmatterParser)
  - **Commit** : `e2ec6ea`

- **v1.0.0-alpha.22** (2026-01-12) : Atomic Transaction Logic for Email + Enrichments
  - **Refonte architecturale** : Actions email + enrichissements traités comme unité atomique
  - **Classification Required/Optional** : Extractions critiques vs optionnelles
    - Deadlines toujours requis
    - Haute importance : décisions, engagements, demandes, montants, faits, événements
    - Moyenne importance : engagements, demandes
  - **Confiance globale** : `min(action_conf, min(required_extraction_confs))`
  - **Exécution atomique** : Enrichissements requis d'abord, puis action email, puis optionnels
  - **Action downgrade** : Archive → Flag si enrichissements requis ont faible confiance
  - **UI "Requis" badge** : Indication visuelle des enrichissements critiques
  - **Fichiers modifiés** :
    - `src/sancho/multi_pass_analyzer.py` — `_should_be_required()`, `to_dict()` enrichi
    - `src/jeeves/api/services/queue_service.py` — `_execute_enrichments()`, `approve_item()` atomique
    - `src/jeeves/api/models/queue.py` — `required`, `importance` fields
    - `src/jeeves/api/routers/queue.py` — Parsing nouveaux champs
    - `web/src/routes/flux/+page.svelte` — Badge "Requis"
    - `web/src/routes/flux/[id]/+page.svelte` — Badge "Requis"
    - `web/src/lib/api/client.ts` — Types TypeScript mis à jour
  - **Tests** : 44 tests convergence + queue API passent
  - **Commit** : `7ca48b0`

- **v1.0.0-alpha.21** (2026-01-12) : Workflow v2.2 Multi-Pass Architecture Design
  - **Innovation majeure** : Inversion du flux Contexte/Extraction
  - **Architecture Multi-Pass** : 1-5 passes avec convergence par confiance (95%+)
  - **Escalade intelligente** : Haiku → Sonnet → Opus selon complexité
  - **High-Stakes Detection** : Escalade automatique Opus si montant > 10k€, deadline < 48h, VIP
  - **Recherche contextuelle précise** : Par entités extraites (vs sémantique floue)
  - **Coût estimé** : ~$59/mois (vs $38/mois v2.1) pour +23% qualité
  - **Confiance moyenne** : 92%+ (vs 75% v2.1)
  - **Distribution passes** : 15% P1 | 70% P2 | 10% P3 | 4% P4 | 1% P5
  - **Spécification complète** : `docs/specs/MULTI_PASS_SPEC.md` (~400 lignes)
  - **Documentation mise à jour** : ARCHITECTURE.md v2.2, WORKFLOW_V2_SIMPLIFIED.md v2.2

- **v1.0.0-alpha.20** (2026-01-12) : Workflow v2.1.2 Enhanced Extraction
  - **5 nouveaux champs** : `timezone`, `duration`, `has_attachments`, `priority`, `project`
  - **Fuseaux horaires** : Support HF (France), HM (Madagascar), Maurice, UTC avec conversion automatique
  - **Durée événements** : Configurable (défaut 60 min), intégration Calendar
  - **OmniFocus amélioré** : `priority` et `project` explicites pour les tâches
  - **Règles note_cible enrichies** :
    - Matrice type d'extraction → note_cible recommandée
    - Résolution d'ambiguïtés (noms partiels, nouveaux contacts, info multi-cible)
    - Utilisation optimisée du contexte fourni
  - **Règles draft_reply détaillées** : Langue adaptée, registre, format
  - **Gestion threads email** : Re:, Fwd:, contenu cité
  - **15 exemples** dans le template (3 nouveaux : timezones, ambiguïté, anglais)
  - **Tests** : 72 tests enricher+analyzer (17 nouveaux)
  - **Commit** : `026e1ca`

- **v1.0.0-alpha.19** (2026-01-11) : Workflow v2.1 Knowledge Extraction Design
  - **Simplification radicale** : 6 phases → 4 phases, ML local → API only
  - **Architecture API-First** : Haiku par défaut, escalade Sonnet si incertain
  - **Coût optimisé** : ~$36/mois au lieu de ~$100/mois
  - **Documentation complète** : WORKFLOW_V2_SIMPLIFIED.md, WORKFLOW_V2_IMPLEMENTATION.md
  - **8 décisions de conception** validées (structure notes, création, OmniFocus, etc.)
  - **Plan d'implémentation** : 6 fichiers, ~880 lignes, ~4 jours
  - **Commits** : `1dc58d3`, `931de4d`
  - **Prochaine étape** : Implémentation Sprint 6

- **v1.0.0-alpha.18** (2026-01-09) : UI Notes Apple-like & Revue SM-2
  - **UI Notes 3 colonnes** : Style Apple Notes (dossiers | liste | contenu)
  - **Dossiers virtuels** : "Toutes les notes" et "Supprimées récemment"
  - **Métadonnées SM-2** : Prochaine revue, facteur facilité, intervalle, importance
  - **Actions notes** : Déclencher revue (🔄), ouvrir nouvelle fenêtre (↗️)
  - **Indicateur revue due** : Point orange sur les notes dans la liste
  - **Sync Apple Notes** : Progression, date dernière sync
  - **Performance** : Singleton cache NotesService (chargement instantané vs 1+ min)
  - **Tri dossiers** : Alphabétique insensible à la casse
  - **Bug fix** : Page /valets (type TokenData)
  - **MVP Progress** : 94% (81/86 items)

- **v1.0.0-alpha.17** (2026-01-09) : Test Suite Verification
  - Tests: 2148+ passed, 50 skipped, 0 failed
  - Verified: test_undo_api.py (8 tests), test_search_api.py (59 tests), test_passepartout_integration.py (7 tests)
  - pytest-asyncio configuration confirmed working (asyncio_mode=strict)
  - **MVP Progress** : 93% (80/86 items)

- **v1.0.0-alpha.16** (2026-01-09) : Sprint 4 COMPLÉTÉ (18/18 — 100%)
  - **WebSocket** : 4 endpoints (/ws/events, /ws/status, /ws/notifications, /ws/discussions/{id})
  - **Notifications** : 9 endpoints CRUD + NotificationsPanel.svelte (Centre de Notifications)
  - **Valets Dashboard** : 4 endpoints API + valets/+page.svelte (Surveillance agents)
  - **UX Avancée** : Raccourcis clavier, Quick Actions, Mode Focus (flux/focus)
  - **UX Mobile** : SwipeableCard, LongPressMenu
  - **Settings** : Page complète (~23KB) avec Apparence, IA, Processing, Notifications
  - **Stats** : LineChart avec tendances 7/30j, LTTB downsampling
  - **CLI** : Menu interactif complet (684 lignes, 18 fonctions)
  - **Infrastructure** : Rate limiting, EventBus bridge, Lock contention fix, Index composite
  - Tests: 2148 passed, 50 skipped, 0 failed
  - **MVP Progress** : 93% (80/86 items)

- **v1.0.0-alpha.15** (2026-01-06) : Security Hardening
  - Deep analysis before Sprint 2 (4 parallel agents: security, architecture, quality, performance)
  - Security: jwt_secret_key required, production auth warning, CORS configurable, sanitized exceptions
  - WebSocket auth via first message (not query param)
  - Login rate limiting (5 attempts/5min with exponential backoff)
  - New utilities: error_handling.py, constants.py, rate_limiter.py
  - Performance: composite index on note_metadata
  - Tests: 1697 passed, svelte-check 0 errors, ruff 0 warnings
  - **Sprint 1: 100% COMPLÉTÉ** (19/19)

- **v1.0.0-alpha.14** (2026-01-06) : Test Dependency Fix
  - Fix: Properly mock get_notes_service dependency in endpoint tests
  - Fix: Use AsyncMock for async service methods
  - Remove unused imports (ruff compliance)
  - Tests : 1736 passed, 53 skipped (0 failures)
  - Sprint 1 : 95% (18/19)

- **v1.0.0-alpha.13** (2026-01-06) : GET /api/status Endpoint
  - ✅ GET /api/status - Status temps réel système
  - ✅ SystemStatusResponse avec état, composants, session stats
  - ✅ StatusService pour agrégation des données
  - ✅ 14 tests unitaires (models, service, endpoint)
  - Sprint 1 : 95% (18/19) — Plus qu'un item !

- **v1.0.0-alpha.12** (2026-01-06) : Code Quality Review
  - Fix CRITIQUE: AbortSignal passé à getPreMeetingBriefing() (abort fonctionne maintenant)
  - Fix VirtualList: Correction stale closure dans IntersectionObserver callback
  - Fix VirtualList: Guard isLoadingMore contre appels multiples rapides
  - Fix PreMeetingModal: Reset état à la fermeture du modal
  - Ajout data-testid pour les tests
  - Sprint 1 : 89% (17/19) — Qualité améliorée

- **v1.0.0-alpha.11** (2026-01-06) : Pre-Meeting Briefing Button
  - ✅ PreMeetingModal.svelte - Modal affichant le briefing complet
  - ✅ Bouton briefing sur les événements calendrier (dashboard)
  - ✅ Affichage : participants, agenda, points de discussion, emails/notes liés
  - ✅ États loading/error avec retry
  - Sprint 1 : 89% (17/19)
  - Total : 1722+ tests

- **v1.0.0-alpha.10** (2026-01-06) : Notes Folders API
  - ✅ POST /api/notes/folders - Création de dossiers
  - ✅ GET /api/notes/folders - Liste des dossiers
  - ✅ NoteManager.create_folder() avec sécurité path traversal
  - ✅ NoteManager.list_folders() avec fix macOS symlink
  - ✅ 18 tests unitaires
  - Sprint 1 : 79% (15/19)
  - Total : 1721+ tests

- **v1.0.0-alpha.9** (2026-01-06) : Stats API
  - ✅ GET /api/stats/overview - Vue globale agrégée
  - ✅ GET /api/stats/by-source - Détails par source
  - ✅ Frontend stats page connectée à l'API
  - ✅ 12 tests backend + 4 tests frontend
  - Total : 1692+ tests

- **v1.0.0-alpha.8** (2026-01-05) : Note Enrichment System
  - ✅ SM-2 Spaced Repetition complet (7 modules Passepartout)
  - ✅ 75 nouveaux tests (total 1666+)
  - Architecture : note_types, note_metadata, note_scheduler, note_reviewer, note_enricher, note_merger, background_worker

- **v1.0.0-alpha.7** (2026-01-05) : Roadmap v3.1 — Notes au centre
  - Réorganisation en Sprints thématiques
  - Priorisation Notes & Qualité d'analyse
  - Création GAPS_TRACKING.md (116 items)

- **v1.0.0-alpha.6** (2026-01-04) : Phase 1.6 + PWA
  - ✅ Journaling multi-source complet
  - ✅ PWA avec Service Worker
  - ✅ Auth JWT + WebSockets

- **v1.0.0-alpha.5** (2026-01-03) : Phases 1.2-1.4 + 0.7
  - ✅ Intégration Teams, Calendar, Briefing
  - ✅ API Jeeves MVP

- **v1.0.0-alpha.4** (2026-01-02) : Phases 0.6-1.1
  - ✅ Refactoring Valet
  - ✅ Pipeline Cognitif
  - ✅ Journaling & Feedback

---

## Ressources

- **Dépôt** : https://github.com/johanlb/scapin
- **Documentation** :
  - [DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md) — Principes fondateurs
  - [ARCHITECTURE.md](ARCHITECTURE.md) — Spécifications techniques
  - [GAPS_TRACKING.md](docs/GAPS_TRACKING.md) — Suivi des écarts
  - [CLAUDE.md](CLAUDE.md) — Contexte de session

---

**Statut** : MVP COMPLET ✅ — Sprint 6 (Workflow v2.1) EN COURS 🚧
**Qualité** : 10/10 Production Ready Core (Security Hardened)
**Tests** : 2148+ backend + 660 E2E tests, 95% couverture, 100% pass rate
**Lighthouse** : A11y 98%, Best Practices 96%, SEO 100%, Performance 86-95%
**Documentation** : Guide utilisateur 7 sections + Specs Workflow v2.1
**Prochaine étape** : Implémentation Workflow v2.1 (~4 jours)
