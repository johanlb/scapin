# Scapin — Feuille de Route Produit

**Dernière mise à jour** : 6 janvier 2026
**Version** : 1.0.0-alpha (suite de PKM v3.1.0)
**Phase actuelle** : Sprint 1 COMPLÉTÉ ✅ — Transition vers Sprint 2

---

## Résumé Exécutif

### Statut Global

**État** : MVP en cours — 44 items MVP restants sur 63 (116 total identifiés)

| Métrique | Valeur |
|----------|--------|
| **Tests** | 1697 tests, 95% couverture, 100% pass rate |
| **Qualité Code** | 10/10 (Ruff 0 warnings) |
| **Phases complétées** | 0.5 à 1.6 + 0.7 à 0.9 + Sprint 1 |
| **Gaps MVP restants** | 44 items ([GAPS_TRACKING.md](docs/GAPS_TRACKING.md)) |
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
│  Multi-Provider IA, LinkedIn, Apple Shortcuts, Révision espacée │
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

**Statut** : 📋 Planifié
**Objectif** : Boucle Email ↔ Notes bidirectionnelle complète
**Items** : 14 MVP
**Dépendance** : Sprint 1

### Livrables

| Catégorie | Item | Priorité |
|-----------|------|----------|
| **Extraction Entités** | Extraction auto (personnes, dates, projets) | MVP |
| | extracted_entities dans EmailProcessingResult | MVP |
| | Proposition ajout entités à PKM | MVP |
| **Données Enrichies** | proposed_tasks dans EmailProcessingResult | MVP |
| | proposed_notes dans EmailProcessingResult | MVP |
| **Discussions** | CRUD /api/discussions | MVP |
| | Messages et suggestions contextuelles | MVP |
| **Chat** | POST /api/chat/quick | MVP |
| **UX Intelligence** | Page Discussions multi-sessions | MVP |
| | Mode traitement focus pleine page | MVP |
| **Teams** | Filtrage par mentions directes | MVP |
| | Déduplication email/Teams | MVP |
| **Notes** | UI: Bouton "Discuter de cette note" | MVP |
| **API** | GET/POST /api/focus | MVP |

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

**Statut** : 📋 Planifié
**Objectif** : Actions sur emails avec contexte riche disponible
**Items** : 16 MVP
**Dépendance** : Sprint 2

### Livrables

| Catégorie | Item | Priorité |
|-----------|------|----------|
| **Events API** | GET /api/events/snoozed | MVP |
| | POST /api/events/{id}/undo | MVP |
| | POST /api/events/{id}/snooze | MVP |
| | DELETE /api/events/{id}/snooze | MVP |
| **Undo/Snooze Backend** | Historique actions pour rollback | MVP |
| | Snooze: rappel automatique à expiration | MVP |
| **Email Drafts** | PrepareEmailReplyAction (backend) | MVP |
| | DraftReply dataclass | MVP |
| | API brouillons: récupérer/modifier | MVP |
| | UI: Affichage et édition brouillons | MVP |
| **Email UI** | Vue détail (corps HTML/texte) | MVP |
| | Bouton Snooze | MVP |
| | Bouton Undo après approbation | MVP |
| **Teams** | POST /api/teams/chats/{id}/read | MVP |
| | UI: Vue détail message | MVP |
| **Calendar CRUD** | POST /api/calendar/events | MVP |
| | PUT /api/calendar/events/{id} | MVP |
| | DELETE /api/calendar/events/{id} | MVP |

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

---

## Sprint 4 : Temps Réel & UX

**Statut** : 📋 Planifié
**Objectif** : Expérience fluide et réactive
**Items** : 14 MVP
**Dépendance** : Sprint 3

### Livrables

| Catégorie | Item | Priorité |
|-----------|------|----------|
| **WebSocket** | /ws/events - événements temps réel | MVP |
| | /ws/discussions/{id} - chat temps réel | MVP |
| | /ws/status - status Scapin | MVP |
| | /ws/notifications - push | MVP |
| **Notifications** | CRUD /api/notifications | MVP |
| | Centre de Notifications (panneau) | MVP |
| **UX Avancée** | Raccourcis clavier complets | MVP |
| | Quick Actions dans Briefing | MVP |
| | Mode Focus / Do Not Disturb | MVP |
| | Snooze événements avec rappel | MVP |
| **UX Mobile** | Swipe gestures complet | MVP |
| **Settings** | Onglets Comptes/Intégrations/IA | MVP |
| **Stats** | Page Stats avec Pipeline valets | MVP |
| **Legacy** | Finir Menu Interactif CLI (20%) | MVP |

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

| Item | Description |
|------|-------------|
| Apple Notes Sync | Synchronisation bidirectionnelle |
| Entity Manager | Gestion des entités extraites |
| Relationship Manager | Graphe NetworkX des relations |
| Templates notes | CRUD /api/templates |
| Quick Capture | Cmd+Shift+N |

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
Sprint 2 (Analyse):░░░░░░░░░░░░░░░░░░░░   0% 📋
Sprint 3 (Actions):░░░░░░░░░░░░░░░░░░░░   0% 📋
Sprint 4 (UX):     ░░░░░░░░░░░░░░░░░░░░   0% 📋
Sprint 5 (Release):░░░░░░░░░░░░░░░░░░░░   0% 📋

=== NICE-TO-HAVE ===
Phase 3.0:         ░░░░░░░░░░░░░░░░░░░░   0% 📋

Global MVP:        ██████░░░░░░░░░░░░░░  30% (19 MVP complétés sur 63)
                   → 44 items restants
```

### Items par Sprint

| Sprint | Items MVP | Complétés | Statut |
|--------|-----------|-----------|--------|
| Sprint 1 | 19 | 19 | ✅ 100% |
| Sprint 2 | 14 | 0 | 📋 Planifié |
| Sprint 3 | 16 | 0 | 📋 Planifié |
| Sprint 4 | 14 | 0 | 📋 Planifié |
| Sprint 5 | 6 | 0 | 📋 Planifié |
| **Total MVP** | **69** | **19** | 28% |
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
