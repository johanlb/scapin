---
name: session
description: Notes de session Scapin - Historique des travaux récents, fonctionnalités implémentées, bugs corrigés. Utiliser pour comprendre le contexte des derniers développements.
allowed-tools: Read, Grep, Glob
---

# Notes de Session Scapin

Historique des travaux récents sur le projet.

## Session Actuelle - 24 Janvier 2026

### Travaux complétés

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
