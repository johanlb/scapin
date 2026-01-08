# Suivi des Écarts — Scapin

**Dernière mise à jour** : 8 janvier 2026
**Total items** : 133
**MVP** : 80 | **Nice-to-have** : 53 | **Complétés** : 45
**Sprint actuel** : Sprint Cross-Source — Phase 2 (7/13 — 54%)
**Prochaine priorité** : Sprint 3 Finalisation + Cross-Source Phase 3

---

## Légende

- ⬜ À faire
- 🟡 En cours
- ✅ Terminé
- ❌ Annulé

---

## 1. Notes PKM (13 items)

### Git Versioning (5)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | Git Versioning - historique des versions (backend) | MVP |
| ✅ | API: GET /notes/{id}/versions - liste versions | MVP |
| ✅ | API: GET /notes/{id}/versions/{v} - version spécifique | MVP |
| ✅ | API: GET /notes/{id}/diff?v1=X&v2=Y - diff entre versions | MVP |
| ✅ | API: POST /notes/{id}/restore/{v} - restaurer version | MVP |

### Fonctionnalités (8)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | Apple Notes Sync - synchronisation bidirectionnelle | Nice-to-have |
| ⬜ | Entity Manager - gestion des entités extraites | Nice-to-have |
| ⬜ | Relationship Manager - graphe NetworkX des relations | Nice-to-have |
| ✅ | API: POST /api/notes/folders - créer dossier | MVP |
| ✅ | UI: Éditeur Markdown complet | MVP |
| ✅ | UI: Bouton "Discuter de cette note" | MVP |
| ⬜ | API: POST /api/capture - capture rapide | Nice-to-have |
| ⬜ | API: GET /api/capture/inbox - inbox captures | Nice-to-have |

---

## 2. Email (25 items)

### Events API Unifiée (4)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | GET /api/events/snoozed - items reportés | MVP |
| ✅ | POST /api/events/{id}/undo - annuler action exécutée | MVP |
| ✅ | POST /api/events/{id}/snooze - reporter événement | MVP |
| ✅ | DELETE /api/events/{id}/snooze - annuler snooze | MVP |

### Brouillons de Réponse (4)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | PrepareEmailReplyAction - génération brouillons (backend) | MVP |
| ✅ | DraftReply dataclass - modèle de données brouillons | MVP |
| ✅ | API brouillons: récupérer/modifier drafts | MVP |
| ✅ | UI: Affichage et édition brouillons | MVP |

### Extraction Entités (3)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | Extraction entités automatique (personnes, dates, projets) | MVP |
| ✅ | extracted_entities dans EmailProcessingResult | MVP |
| ✅ | Proposition ajout entités à PKM (proposed_notes) | MVP |

### Undo & Snooze Backend (2)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | Undo: historique actions pour rollback | MVP |
| ✅ | Snooze: rappel automatique à expiration | MVP |

### Settings Email (4)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | POST /api/settings/accounts - ajouter compte | Nice-to-have |
| ⬜ | PUT /api/settings/accounts/{id} - modifier compte | Nice-to-have |
| ⬜ | DELETE /api/settings/accounts/{id} - supprimer compte | Nice-to-have |
| ⬜ | POST /api/settings/integrations/{name}/test - tester connexion | Nice-to-have |

### Sync Settings (2)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | GET /api/settings/sync - config synchronisation | Nice-to-have |
| ⬜ | PATCH /api/settings/sync/account/{id} - fréquence par compte | Nice-to-have |

### UI Email (3)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | Vue détail email (corps HTML/texte complet) | MVP |
| ⬜ | Bouton Snooze dans l'interface | MVP |
| ⬜ | Bouton Undo après approbation | MVP |

### Données Enrichies (2)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | proposed_tasks dans EmailProcessingResult | MVP |
| ✅ | proposed_notes dans EmailProcessingResult | MVP |

### Contexte & Analyse (1)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | ContextEngine connecté au CognitivePipeline (#40) | MVP |

---

## 3. Calendar (7 items)

### CRUD Événements (3)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | POST /api/calendar/events - créer événement | MVP |
| ⬜ | PUT /api/calendar/events/{id} - modifier événement | MVP |
| ⬜ | DELETE /api/calendar/events/{id} - supprimer événement | MVP |

### Fonctionnalités (4)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | Bouton briefing pré-réunion sur chaque événement | MVP |
| ⬜ | Blocs Focus automatiques (création ne pas déranger) | Nice-to-have |
| ✅ | Détection et alerte conflits calendrier | MVP |
| ⬜ | Vue calendrier mensuelle/hebdomadaire (UI) | Nice-to-have |

---

## 4. Teams (5 items)

| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | POST /api/teams/chats/{id}/read - marquer lu | MVP |
| ⬜ | Support channels Teams (pas juste chats 1:1) | Nice-to-have |
| ⬜ | Filtrage par mentions directes | MVP |
| ⬜ | Déduplication si même info par email et Teams | Nice-to-have |
| ⬜ | UI: Vue détail message Teams | MVP |

---

## 5. API Générales (25 items)

### Discussions API (2)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | CRUD /api/discussions (list, create, get, delete, update, messages) | MVP |
| ✅ | Messages et suggestions contextuelles | MVP |

### Chat Rapide (1)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | POST /api/discussions/quick - instruction rapide one-shot | MVP |

### Recherche API (3)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | GET /api/search - recherche globale multi-types | MVP |
| ✅ | GET /api/search/recent - recherches récentes | Nice-to-have |
| ⬜ | POST /api/search/commands - exécuter commande | Nice-to-have |

### Stats API (5)
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | GET /api/stats/overview - vue globale KPIs | MVP |
| ✅ | GET /api/stats/by-source - répartition par source | MVP |
| ⬜ | GET /api/stats/confidence - évolution confiance | Nice-to-have |
| ⬜ | GET /api/stats/tokens + budget - consommation API | Nice-to-have |
| ⬜ | GET /api/stats/learning - patterns Sganarelle | Nice-to-have |

### Rapports API (2)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | CRUD /api/reports (daily, weekly, monthly) | Nice-to-have |
| ⬜ | Export PDF/Markdown | Nice-to-have |

### Valets Pipeline API (1)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | GET /api/valets - status et métriques valets (Pipeline view) | Nice-to-have |

### Autres APIs (11)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | GET/POST /api/focus - mode focus | MVP |
| ⬜ | CRUD /api/filters - filtres sauvegardés | Nice-to-have |
| ⬜ | CRUD /api/notifications - centre notifications | MVP |
| ⬜ | CRUD /api/tags + association événements | Nice-to-have |
| ⬜ | CRUD annotations sur événements | Nice-to-have |
| ⬜ | CRUD /api/templates - templates notes | Nice-to-have |
| ⬜ | GET /api/activity - timeline activité | Nice-to-have |
| ✅ | GET /api/status - status temps réel Scapin | MVP |

---

## 6. WebSocket (4 items)

| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | /ws/events - événements temps réel | MVP |
| ⬜ | /ws/discussions/{id} - chat temps réel | MVP |
| ⬜ | /ws/status - status Scapin temps réel | MVP |
| ⬜ | /ws/notifications - push notifications | MVP |

---

## 7. UX Avancée (17 items)

### MVP (10)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | Mode Focus / Do Not Disturb | MVP |
| ⬜ | Quick Actions dans Briefing (boutons rapides items urgents) | MVP |
| ⬜ | Centre de Notifications (panneau) | MVP |
| ⬜ | Snooze événements avec rappel | MVP |
| ⬜ | Raccourcis clavier complets (?, 1/2/3, j/k, etc.) | MVP |
| ⬜ | Mode traitement focus pleine page | MVP |
| ⬜ | Swipe gestures mobile complet | MVP |
| ✅ | Page Discussions multi-sessions | MVP |
| ⬜ | Page Stats avec Pipeline valets | MVP |
| ⬜ | Settings: onglets Comptes/Intégrations/IA/Notifications | MVP |

### Nice-to-have (7)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | Prévisualisation liens hover [[]] | Nice-to-have |
| ⬜ | Templates de notes (UI) | Nice-to-have |
| ⬜ | Bulk Actions (sélection multiple + actions) | Nice-to-have |
| ⬜ | Filtres sauvegardés (UI) | Nice-to-have |
| ⬜ | Activity Log (timeline UI) | Nice-to-have |
| ⬜ | Quick Capture (Cmd+Shift+N) | Nice-to-have |
| ⬜ | Tags personnalisés colorés (UI) | Nice-to-have |

---

## 8. Intégrations Futures (6 items)

| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | LinkedIn messagerie (lecture messages directs) | Nice-to-have |
| ⬜ | WhatsApp (question ouverte - API limitée) | Nice-to-have |
| ⬜ | Apple Shortcuts bidirectionnel (v1.1) | Nice-to-have |
| ⬜ | OneDrive/SharePoint lecture (v1.2) | Nice-to-have |
| ⬜ | Transcriptions réunion (v1.0) | Nice-to-have |
| ⬜ | Planner lecture (contexte équipe) | Nice-to-have |

---

## 9. Fonctionnalités Cognitives (3 items)

| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | Multi-Provider Consensus (Pass 4, Phase 2.5) | Nice-to-have |
| ✅ | Révision espacée (connaissances critiques) | Nice-to-have |
| ⬜ | Continuity Detector amélioré | Nice-to-have |

---

## 10. Phase 0.9+ Futures (3 items)

| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | Prédictions Scapin ("Demain tu auras probablement 8 emails") | Nice-to-have |
| ⬜ | Résumé Audio Briefing (TTS) | Nice-to-have |
| ⬜ | Mode vocal (dialogues audio) | Nice-to-have |

---

## 11. UI Components Manquants (6 items)

| Status | Item | Priorité |
|--------|------|----------|
| ✅ | Modal.svelte (dialog générique) | MVP |
| ✅ | Tabs.svelte (navigation par onglets) | MVP |
| ✅ | Toast.svelte (notifications temporaires) | MVP |
| ✅ | ConfidenceBar.svelte (barre de confiance visuelle) | MVP |
| ✅ | Skeleton.svelte (loading placeholders) | MVP |
| ✅ | Infinite Scroll + Virtualisation (listes longues) | MVP |

---

## 12. Qualité & Documentation (3 items)

| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | Tests E2E Playwright (scénarios critiques) | MVP |
| ⬜ | Performance Lighthouse > 80 (PWA) | MVP |
| ⬜ | Documentation utilisateur (guide démarrage) | MVP |

---

## 13. 🔥 Cross-Source Intelligence (13 items — 7 complétés) — PRIORITÉ

> **Vision** : Permettre à Scapin d'interroger TOUTES les sources d'information disponibles
> pour enrichir les notes et améliorer l'analyse.
>
> **Phase 2 complétée** : Core Engine + Email/Calendar/Teams Adapters (63 tests)

### Core Engine (3) — ✅ COMPLÉTÉ
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | CrossSourceEngine service | MVP |
| ✅ | Unified search interface (models, cache, config) | MVP |
| ✅ | Query routing intelligent | MVP |

### Adapters Sources Existantes (4) — ✅ COMPLÉTÉ
| Status | Item | Priorité |
|--------|------|----------|
| ✅ | Adapter: Emails archivés (IMAP search) | MVP |
| ✅ | Adapter: Calendrier Microsoft (événements passés/futurs) | MVP |
| ✅ | Adapter: Calendrier iCloud (CalDAV API) | MVP |
| ✅ | Adapter: Teams (historique messages) | MVP |

### Adapters Nouvelles Sources (3)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | Adapter: WhatsApp (historique SQLite local) | MVP |
| ⬜ | Adapter: Fichiers locaux (ripgrep) | MVP |
| ⬜ | Adapter: Web/Internet (Tavily API) | MVP |

### Intégration Pipeline (3)
| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | Hook dans ReasoningEngine (Pass 2+ si confiance < 75%) | MVP |
| ⬜ | Hook dans NoteReviewer (enrichissement révisions) | MVP |
| ⬜ | API: POST /api/search/cross-source | MVP |

---

## 14. Valets Dashboard (4 items)

> **Vision** : Visualiser le travail d'équipe des valets en temps réel.

| Status | Item | Priorité |
|--------|------|----------|
| ⬜ | UI: Statut workers (running/idle/paused) | MVP |
| ⬜ | UI: Activité NoteReviewer en cours | MVP |
| ⬜ | UI: Visualisation travail d'équipe valets | MVP |
| ⬜ | API: GET /api/valets/status | MVP |

---

## Résumé par Catégorie

| Catégorie | Total | MVP | Nice-to-have |
|-----------|-------|-----|--------------|
| Notes | 13 | 5 | 8 |
| Email | 24 | 15 | 9 |
| Calendar | 7 | 5 | 2 |
| Teams | 5 | 3 | 2 |
| API Générales | 25 | 12 | 13 |
| WebSocket | 4 | 4 | 0 |
| UX Avancée | 17 | 10 | 7 |
| Intégrations Futures | 6 | 0 | 6 |
| Cognitif | 3 | 0 | 3 |
| Phase 0.9+ | 3 | 0 | 3 |
| UI Components | 6 | 6 | 0 |
| Qualité & Docs | 3 | 3 | 0 |
| **🔥 Cross-Source** | **13** | **13** | **0** |
| **Valets Dashboard** | **4** | **4** | **0** |
| **TOTAL** | **133** | **80** | **53** |

---

## Progression

```
MVP:          ███████████░░░░░░░░░ 48/79 (61%)
Nice-to-have: ██░░░░░░░░░░░░░░░░░░ 3/53 (6%)
Total:        █████████░░░░░░░░░░░ 51/132 (39%)

Sprint 1:     ████████████████████ 19/19 (100%) ✅
Sprint 2:     ████████████████████ 13/13 (100%) ✅
Sprint 3:     ███████████░░░░░░░░░ 10/18 (56%) 🚧
Cross-Source: ██████████░░░░░░░░░░  7/13 (54%) 🚧 🔥 Phase 2 ✅
Valets Dash:  ░░░░░░░░░░░░░░░░░░░░  0/4 (0%) 📋
```

---

## Historique des Mises à Jour

| Date | Action |
|------|--------|
| 2026-01-08 | **iCloud Calendar Adapter ✅** — CalDAV API support (29 tests) |
| 2026-01-08 | **Cross-Source Phase 2 ✅** — Calendar + Teams Adapters (63 tests total) |
| 2026-01-08 | **Cross-Source Phase 1 ✅** — Core Engine + Email Adapter (34 tests) |
| 2026-01-08 | **🔥 Cross-Source AJOUTÉ** — 12 items MVP prioritaires (emails archivés, calendar, teams, whatsapp, files, web search) |
| 2026-01-08 | **Valets Dashboard AJOUTÉ** — 4 items MVP (statut workers, activité reviewer, visualisation équipe) |
| 2026-01-07 | **Discussions Frontend COMPLÉTÉ** — Store Svelte 5, page intégrée, modal création, vue détail |
| 2026-01-06 | **Sprint 1 COMPLÉTÉ** — 19/19 items (100%) |
| 2026-01-06 | **Security Hardening** — Analyse profonde + corrections sécurité avant Sprint 2 |
| 2026-01-06 | Nouveaux modules : error_handling.py, constants.py, rate_limiter.py |
| 2026-01-05 | Création initiale - Analyse complète des écarts vs specs |
| 2026-01-05 | Seconde passe - Ajout 21 items (Intégrations, Cognitif, UI Components, Qualité) |
| 2026-01-05 | Git Versioning complété (5 items) - backend + 4 endpoints API |
| 2026-01-05 | Search API complétée (2 items) - GET /api/search + /api/search/recent |
| 2026-01-05 | Note Enrichment System complété - Révision espacée SM-2 (7 modules, 75 tests) |
| 2026-01-05 | UI Components complétés (5 items) - Modal, Tabs, Toast, ConfidenceBar, Skeleton |
| 2026-01-05 | Éditeur Markdown complété - Preview live, wikilinks, toolbar, auto-save |
| 2026-01-06 | **Stats API complétée (2 items)** - GET /api/stats/overview + /by-source |
| 2026-01-06 | **POST /api/notes/folders complété** - création dossiers notes + GET /api/notes/folders |
| 2026-01-06 | **Infinite Scroll + Virtualisation complété** - VirtualList.svelte avec @tanstack/svelte-virtual |
| 2026-01-06 | **Bouton briefing pré-réunion complété** - PreMeetingModal.svelte + intégration dashboard |
| 2026-01-06 | **Revue qualité VirtualList + PreMeetingModal** - Corrections critiques (AbortSignal, stale closures, guards) |
| 2026-01-06 | **GET /api/status complété** - Status temps réel système (état, composants, session) |

---

## Notes

- Ce fichier liste les écarts entre les spécifications de conception (`docs/plans/phase-0.8-web/`) et l'implémentation actuelle
- Les priorités MVP sont basées sur les documents `04-mockups-core.md` et `06-ux-avancee.md`
- Mettre à jour le status (⬜ → 🟡 → ✅) au fur et à mesure de l'avancement
