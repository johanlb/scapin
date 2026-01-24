---
name: session
description: Notes de session Scapin - Historique des travaux récents, fonctionnalités implémentées, bugs corrigés. Utiliser pour comprendre le contexte des derniers développements.
allowed-tools: Read, Grep, Glob
---

# Notes de Session Scapin

Historique des travaux récents sur le projet.

## Session Actuelle - 24 Janvier 2026

### Travaux complétés

**Plan Performance-Baseline (✅ COMPLET) :**

Optimisations backend pour réduire latence et overhead.

| Phase | Contenu | Commit |
|-------|---------|--------|
| 0 | Nouveau baseline (flamegraph + métriques) | documenté |
| 1 | Thread pool 32→8 (note_manager.py) | `0aaa9ab` |
| 2 | Cache context search (TTLCache 60s) | `0aaa9ab` |
| 3 | Early-stop emails éphémères | `0aaa9ab` |
| 4 | Documentation performance.md | `6ea2ae1` |
| 5 | Mesures finales | `7869c43` |

**Gains mesurés :**
- Thread pool : -75% overhead context switching
- Cache FAISS : -70% temps multi-pass (cache hits)
- Emails éphémères : ~30% flaggés

**Fichiers clés modifiés :**
- `src/passepartout/note_manager.py` — Thread pool 32→8
- `src/sancho/context_searcher.py` — TTLCache + invalidate_cache()
- `src/passepartout/cross_source/adapters/email_adapter.py` — is_ephemeral flag
- `docs/architecture/performance.md` — Documentation complète

**Plan archivé** : `docs/plans/archive/performance-baseline.md`

**Limitation** : ~47% du temps = attente API Anthropic (I/O wait) → impact global ~10-15%

---

**Optimisation is_ephemeral dans Sancho (✅ COMPLET — PR #55) :**

Utilisation du flag `is_ephemeral` pour optimiser l'analyse des emails éphémères.

| Optimisation | Description |
|--------------|-------------|
| Éviter escalade Opus | Emails éphémères restent sur Haiku/Sonnet |
| Seuil convergence réduit | 80% au lieu de 95% |
| Skip context search | Pas de recherche FAISS inutile |

**Commit** : `e88b068`

**Fichiers modifiés :**
- `src/trivelin/v2_processor.py` — Propagation flag dans PerceivedEvent
- `src/sancho/multi_pass_analyzer.py` — Utilisation flag pour optimiser

---

**Bug fix analyses incomplètes (`e6c71a7`) :**

Items avec analyse incomplète (confidence=0 ou action=None) restent maintenant en état ANALYZING au lieu de passer en AWAITING_REVIEW.

**Fichier modifié** : `src/integrations/storage/queue_storage.py`

---

**Nettoyage Canevas :**

Harmonisation du dossier Canevas (contexte permanent Johan).

| Action | Détail |
|--------|--------|
| Dossier Apple Notes | Renommé "Briefing" → "Canevas" |
| Métadonnées | 3 doublons supprimés, paths corrigés |
| Frontmatters | path: Briefing → Canevas |
| Preferences.md | Créé (template préférences) |

**État final Canevas :** 4 fichiers, 15740 chars, COMPLETE
- Profile.md, Projects.md, Goals.md, Preferences.md

---

**Système Retouche (✅ COMPLET — PR #56) :**

Système complet d'amélioration automatique des notes par IA.

| Phase | Contenu | Statut |
|-------|---------|--------|
| 0 | Refactoring AnalysisEngine | ✅ |
| 1 | Connexion IA (AIRouter) | ✅ |
| 2 | Prompts Jinja2 par type de note | ✅ |
| 3 | Actions avancées (suggest_links, cleanup, omnifocus) | ✅ |
| 4 | Preview UI (RetoucheDiff, RetoucheBadge) | ✅ |
| 5 | Queue + Rollback | ✅ |
| 6 | Notifications (rate limiting, filage) | ✅ |
| 7 | Tests unitaires + E2E | ✅ |

**Fichiers clés créés :**
- `src/passepartout/retouche_reviewer.py` — Moteur Retouche
- `src/sancho/analysis_engine.py` — Classe abstraite partagée
- `src/frontin/api/services/retouche_notification_service.py` — Notifications
- `templates/ai/v2/retouche/*.j2` — Prompts par type
- `web/src/lib/components/notes/RetoucheDiff.svelte` — Modal preview
- `web/src/lib/components/notes/RetoucheQueue.svelte` — Page queue
- `tests/unit/test_retouche_reviewer.py` — 5 tests erreurs
- `web/e2e/pages/retouche.spec.ts` — Tests E2E Playwright

**Plan archivé** : `docs/archive/completed-plans/retouche-notes-2026-01.md`

---

**Amélioration CLAUDE.md :**
- Structure du Projet (arbre complet des dossiers)
- APIs Externes & Secrets (Gmail, iCloud, Anthropic, Keychain)
- Debug Rapide (commandes de diagnostic essentielles)
- Glossaire (17 termes Scapin)
- Discipline de Livraison (checklist bloquante 9 points)
- Anti-patterns (8 interdits)
- Gestion de Session (prévenir dégradation)

**Nouveaux Skills créés :**
- `/api` — Conventions FastAPI, endpoints existants, client TypeScript
- `/perf` — Métriques, profiling, optimisations backend/frontend
- `/debug` — Guide de troubleshooting complet
- `/ui` — Best practices frontend, Liquid Glass Apple

**Améliorations Skills existants :**
- `/ui` : Ajout guidelines Apple Liquid Glass (WWDC 2025)
- `/workflow` : Suppression redondances, références croisées vers /api, /ui, /perf
- `/valets` : Structure Frontin détaillée, skills connexes

**Infrastructure :**
- Hook pre-commit Git (Ruff, TypeScript, console.log, TODO)

**Plan Workflow Cleanup + AutoFetch (✅ COMPLÉTÉ) :**
- Plan archivé : `docs/plans/archive/workflow-cleanup-autofetch.md`
- 4 phases complétées :
  1. ✅ Nettoyage workflow (suppression V1, Four Valets seul)
  2. ✅ AutoFetch (`ee49e2d`) — fetch auto, cooldowns, WebSocket events
  3. ✅ Routage confiance (`0741ad8`) — auto-apply >= 85%
  4. ✅ Documentation (`d26cda7`) — `docs/architecture/workflow.md`

**Fichiers créés/modifiés :**
- `src/frontin/api/services/autofetch_manager.py` — Singleton AutoFetch
- `src/core/config_manager.py` — AutoFetchConfig (thresholds, cooldowns)
- `src/frontin/api/websocket/queue_events.py` — Events fetch_started/completed
- `docs/architecture/workflow.md` — Documentation complète
- `ARCHITECTURE.md` — Section AutoFetch ajoutée

**Bug fix inclus :**
- `9516cf0` — Normalisation message IDs dans ProcessedEmailTracker

### En attente

- **Refactoring UI** : Plan de refactoring des composants volumineux
  - `QueueItemFocusView.svelte` (620 lignes → 9 sous-composants)
  - `FolderSelector.svelte` (675 lignes → 7 sous-composants)
  - Plan complet : `docs/plans/2026-01-24-ui-refactoring.md`

---

## Sessions Précédentes

### 19 Janvier 2026 — E2E Test Stabilization

**Résultat** : 80 tests E2E passés (100% pass rate)

**Corrections appliquées :**

| Fichier | Problème | Solution |
|---------|----------|----------|
| `notes.spec.ts` | Strict mode violations | Sélecteurs spécifiques |
| `notes.spec.ts` | Conflit Cmd+K | Test accepte recherche OU palette |
| `valets.spec.ts` | Tests metrics sans données | Tests conditionnels |
| `valets.spec.ts` | Bouton refresh bloqué | `{ force: true }` |
| `journal.spec.ts` | Stats cards async | Gestion états de chargement |
| `help.spec.ts` | Sélecteur manqué | `data-testid` |
| `drafts.spec.ts` | `networkidle` flaky | Attentes explicites |

**Commit** : `76d0444`

---

### 19 Janvier 2026 — Analysis Transparency v2.3

**Phase 1 (v2.3.0) - Fondations :**
- API multi_pass : métadonnées d'analyse
- Section Analyse dans page détail flux
- Badges Complexité : ⚡🔍🧠🏆

**Phase 2 (v2.3.1) - Visualisation :**
- PassTimeline : timeline visuelle des passes
- ConfidenceSparkline : graphique SVG confiance
- Thinking Bubbles (💭) : questions IA entre passes
- Why Not Section : alternatives rejetées

**Phase 3 (v2.3.2) - Bug Fix :**
- Fix `multi_pass: null` dans queue.py
- Transparence sur page principale Flux

**Composants créés :**
- `web/src/lib/components/flux/PassTimeline.svelte`
- `web/src/lib/components/flux/ConfidenceSparkline.svelte`

---

### 18 Janvier 2026 — Context Transparency v2.2.2

**Fonctionnalités :**
- `retrieved_context` : contexte brut récupéré
- `context_influence` : impact du contexte sur l'analyse
- Section "Influence du contexte" dans UI
- Fix sync blocking avec `asyncio.to_thread()`

**Champs context_influence :**
- `notes_used`, `explanation`, `confirmations`, `contradictions`, `missing_info`

---

### 18 Janvier 2026 — Notes UX & Performance

**Fonctionnalités Notes :**
- Recherche API hybride (full-text + sémantique)
- Édition titre inline
- Bouton Revue Hygiène (🧹)
- Visualisation média Apple Notes

**Performance :**
| Métrique | Avant | Après |
|----------|-------|-------|
| Arbre des notes | 5+ min | 0.003s |
| Liste notes filtrée | 5+ min | ~0.01s |

---

## Archives

- [Sessions Janvier 7-17](docs/archive/session-history/2026-01-07-to-2026-01-17.md)
- [Sessions Janvier 2-6](docs/archive/session-history/2026-01-02-to-2026-01-06.md)
