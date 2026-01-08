# Scapin — Feuille de Route Produit

**Dernière mise à jour** : 8 janvier 2026
**Version** : 1.0.0-alpha (suite de PKM v3.1.0)
**Phase actuelle** : Sprint 3 EN COURS 🚧 — Workflow & Actions (10/18 items — 56%)
**Prochaine priorité** : Sprint 4 — Temps Réel & UX

---

## Résumé Exécutif

### Statut Global

**État** : MVP en cours — 32 items MVP restants sur 86 (Cross-Source 100% complété)

| Métrique | Valeur |
|----------|--------|
| **Tests** | 2192 tests, 95% couverture, 100% pass rate |
| **Qualité Code** | 10/10 (Ruff 0 warnings, svelte-check 0 errors) |
| **Phases complétées** | 0.5 à 1.6 + 0.7 à 0.9 + Sprint 1 + Sprint 2 + Sprint 3 (partiel) |
| **Gaps MVP restants** | 44 items ([GAPS_TRACKING.md](docs/GAPS_TRACKING.md)) |
| **Prochaine priorité** | 🔥 **Sprint 3** — Workflow & Actions (8 items restants) |
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

**Total tests** : 1697 | **Couverture** : 95% | **Pass rate** : 100%

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

**Statut** : 🚧 En cours (10/18 — 56%)
**Objectif** : Actions sur emails avec contexte riche disponible
**Items** : 18 MVP (10 complétés)
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
| **Email UI** | Vue détail (corps HTML/texte) | MVP | ⬜ |
| | Bouton Snooze | MVP | ⬜ |
| | Bouton Undo après approbation | MVP | ⬜ |
| **Teams** | POST /api/teams/chats/{id}/read | MVP | ⬜ |
| | POST /api/teams/chats/{id}/unread | MVP | ⬜ |
| | UI: Vue détail message (thread complet) | MVP | ⬜ |
| **Calendar CRUD** | POST /api/calendar/events | MVP | ⬜ |
| | PUT /api/calendar/events/{id} | MVP | ⬜ |
| | DELETE /api/calendar/events/{id} | MVP | ⬜ |

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

**Statut** : 📋 Planifié
**Objectif** : Expérience fluide et réactive
**Items** : 18 MVP
**Dépendance** : Sprint Cross-Source

### Livrables

| Catégorie | Item | Priorité |
|-----------|------|----------|
| **WebSocket** | /ws/events - événements temps réel | MVP |
| | /ws/discussions/{id} - chat temps réel | MVP |
| | /ws/status - status Scapin | MVP |
| | /ws/notifications - push | MVP |
| **Notifications** | CRUD /api/notifications | MVP |
| | Centre de Notifications (panneau) | MVP |
| **Valets Dashboard** 🆕 | UI: Statut workers (running/idle/paused) | MVP |
| | UI: Activité NoteReviewer en cours | MVP |
| | UI: Visualisation travail d'équipe valets | MVP |
| | API: GET /api/valets/status | MVP |
| **UX Avancée** | Raccourcis clavier complets | MVP |
| | Quick Actions dans Briefing | MVP |
| | Mode Focus / Do Not Disturb | MVP |
| | Snooze événements avec rappel | MVP |
| **UX Mobile** | Swipe gestures complet | MVP |
| **Settings** | Onglets Comptes/Intégrations/IA | MVP |
| **Stats** | Page Stats avec Pipeline valets | MVP |
| **Legacy** | Finir Menu Interactif CLI (20%) | MVP |

### Valets Dashboard (Nouveau)

```
┌─────────────────────────────────────────────────────────────────┐
│                    🎭 L'Équipe Scapin                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Trivelin │  │  Sancho  │  │Passepartout│ │ Planchet │        │
│  │  👁️ IDLE │  │ 🧠 BUSY  │  │ 📚 REVIEW │  │ 📋 IDLE │        │
│  │          │  │ Email #42│  │ Note #17  │  │          │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐  │
│  │  Figaro  │  │Sganarelle│  │ Background Worker            │  │
│  │ ⚡ EXEC  │  │ 📊 LEARN │  │ ████████░░ 8/50 reviews/jour │  │
│  │ Archive  │  │ Pattern  │  │ Session: 2:34/5:00           │  │
│  └──────────┘  └──────────┘  └──────────────────────────────┘  │
│                                                                  │
│  Dernière activité:                                              │
│  • 14:23 Sancho: Email analysé → Archive/Travail (conf: 92%)   │
│  • 14:21 Passepartout: Note "Marie Dupont" révisée (q=4)       │
│  • 14:20 Figaro: Email #41 archivé                              │
│  • 14:18 Sganarelle: Pattern détecté "emails Acme = Archive"   │
└─────────────────────────────────────────────────────────────────┘
```

**Fonctionnalités** :
- Statut en temps réel de chaque valet (idle, busy, error)
- Tâche en cours pour les valets actifs
- Progression du Background Worker (reviews/jour, temps session)
- Timeline des dernières actions
- Indicateurs visuels (couleurs, animations)

### Valeur Délivrée

- **Proactivité maximale** : Notifications temps réel
- **Expérience fluide** : WebSocket, raccourcis clavier
- **Mobile-first** : Gestures complets

---

## Sprint 5 : Qualité & Release

**Statut** : 📋 Planifié
**Objectif** : v1.0 Release Candidate
**Items** : 6 MVP
**Dépendance** : Sprint 4

### Livrables

| Catégorie | Item | Priorité |
|-----------|------|----------|
| **Tests** | Tests E2E Playwright | MVP |
| **Performance** | Lighthouse > 80 | MVP |
| **Documentation** | Guide utilisateur | MVP |
| **Notes** | API: POST /api/capture (quick capture) | Nice-to-have |
| | API: GET /api/capture/inbox | Nice-to-have |
| **Cleanup** | Revue code, optimisations | — |

### Critères de Release v1.0

- [ ] 100% des 63 items MVP complétés
- [ ] Tests E2E couvrant scénarios critiques
- [ ] Lighthouse score > 80
- [ ] Documentation utilisateur complète
- [ ] Zéro bug bloquant

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

=== MVP EN COURS ===
Sprint 1 (Notes):  ████████████████████ 100% ✅ (19/19)
Sprint 2 (Analyse):████████████████████ 100% ✅ (13/13)
Sprint 3 (Actions):███████████░░░░░░░░░  56% 🚧 (10/18)
Cross-Source 🔥:   ████████████████████  100% ✅ (12/12)
Sprint 4 (UX):     ░░░░░░░░░░░░░░░░░░░░   0% 📋
Sprint 5 (Release):░░░░░░░░░░░░░░░░░░░░   0% 📋

=== NICE-TO-HAVE ===
Phase 3.0:         ░░░░░░░░░░░░░░░░░░░░   0% 📋

Global MVP:        ██████████░░░░░░░░░░  42% (42 MVP complétés sur 86)
                   → 44 items restants
```

### Items par Sprint

| Sprint | Items MVP | Complétés | Statut |
|--------|-----------|-----------|--------|
| Sprint 1 | 19 | 19 | ✅ 100% |
| Sprint 2 | 13 | 13 | ✅ 100% |
| Sprint 3 | 18 | 10 | 🚧 56% |
| **Cross-Source** 🔥 | **12** | **12** | ✅ **100%** |
| Sprint 4 | 18 | 0 | 📋 Planifié |
| Sprint 5 | 6 | 0 | 📋 Planifié |
| **Total MVP** | **86** | **54** | 63% |
| Phase 3.0 | 53 | 3 | 📋 Après MVP |

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

**Statut** : Sprint 1 COMPLÉTÉ ✅ — Prêt pour Sprint 2
**Qualité** : 10/10 Production Ready Core (Security Hardened)
**Tests** : 1697 tests, 95% couverture, 100% pass
**Prochaine étape** : Sprint 2 — Qualité d'Analyse (extraction entités, proposed_notes, discussions)
