# Plan : Optimisation de la Performance

**Créé** : 24 Janvier 2026
**Mis à jour** : 24 Janvier 2026
**Objectif** : Fluidité UX, éliminer freezes/hangs causés par traitements backend
**Priorité principale** : Lenteurs sur analyses d'emails
**Focus** : Backend (quick wins) — Frontend reporté après refactoring UI

---

## Décisions prises

- [x] Focus sur le **backend** pour cette session (cause des freezes)
- [x] Tâches **frontend reportées** après le plan de refactoring UI en cours
- [x] Ajout **profiling CPU py-spy** pour analyse approfondie
- [x] Exploiter les **logs `[PERF]`** existants avant d'ajouter des outils
- [x] Plans **séparés mais séquencés** (perf backend → refactoring UI → perf frontend)

---

## Vue d'ensemble

L'architecture Scapin est déjà bien optimisée (cache multi-niveaux, async, déduplication O(N)).
Ce plan cible les **goulots d'étranglement restants**, particulièrement sur l'analyse multi-pass.

**Coupable probable** : Context search synchrone pendant l'analyse multi-pass. Chaque email déclenche des recherches vectorielles bloquantes.

---

## Phase 0 — Setup Outils

### #12 Installer py-spy

**Commandes** :
```bash
# Installation
pip install py-spy

# Vérification
py-spy --version
```

**Note macOS** : py-spy peut nécessiter des permissions supplémentaires (SIP). Si erreur "Operation not permitted" :
- Lancer avec `sudo py-spy`
- Ou désactiver SIP temporairement (déconseillé en prod)

**Action** : Ajouter à `requirements-dev.txt` si non présent

---

## Phase 1 — Profiling & Baseline

### #10 Établir baseline de performance

**Objectif** : Mesurer l'état actuel avant optimisations

**Métriques à capturer** :

| Zone | Métriques | Outil |
|------|-----------|-------|
| Analyse emails | Temps multi-pass par email | Logs `[PERF]` existants |
| Context search | Temps par recherche entité | `time.perf_counter()` |
| Notes loading | Temps startup avec N notes | Timer custom |
| API Backend | Temps réponse endpoints clés | Logs timing |

**Livrable** : Document baseline chiffrée dans `docs/plans/performance-baseline.md`

---

### #11 Profiling CPU avec py-spy

**Dépend de** : #12

**Outil** : py-spy (profiling CPU sans overhead, pas besoin de modifier le code)

**Cibles à profiler** :
1. Pipeline Four Valets (Grimaud → Bazin → Planchet → Mousqueton)
2. Context search pendant analyse
3. Recherche vectorielle FAISS
4. Lecture notes depuis iCloud

**Commandes** :
```bash
# Profiling en temps réel (voir où le CPU passe son temps)
py-spy top --pid <PID_BACKEND>

# Flamegraph pour analyse détaillée
py-spy record -o profile.svg --pid <PID_BACKEND>

# Profiler pendant une analyse d'email
py-spy record -o analysis-profile.svg -- python -c "from src.sancho import analyze_email; ..."
```

**Livrable** : Flamegraph SVG identifiant les hotspots CPU

---

## Phase 2 — Quick Wins Backend (Haute priorité)

### #4 Implémenter cache pour context search entités ⭐ PRIORITÉ

**Fichier** : `src/sancho/context_searcher.py`

**Problème** : Pipeline 4 Valets réexécute context search pour chaque email. Même entités (personnes, projets) recherchées répétitivement.

**Solution** :
- Cache résultats par entity (personnes, projets)
- TTL 15min pour entités stables
- Réutilisation contexte entre emails similaires

**Impact estimé** : ~20% gains sur analyse multi-pass

---

### #3 Ajouter early-stop aux adapters email/calendar

**Fichiers** :
- `src/passepartout/cross_source/adapters/email_adapter.py`
- `src/passepartout/cross_source/adapters/base.py`

**Problème** : Pas de filtrage serveur-side, scan complet même si quota atteint

**Solution** :
- Early-stopping si résultats >= max_results
- Offset/limit dans requêtes
- Arrêt scan dès quota atteint

---

### #2 Réduire thread pool note loading (32 → 8 workers)

**Fichier** : `src/passepartout/note_manager.py:1723-1731`

**Problème** : `max_workers = min(32, ...)` = surcharge I/O, context switching overhead

**Solution** : Réduire à `max_workers = min(8, len(files_to_load))`

**Effort** : 5 minutes — Quick win immédiat

---

### #5 Ajouter batch_search() à VectorStore

**Fichier** : `src/passepartout/entity_search.py`

**Dépend de** : #4

**Solution** : Grouper 10-20 requêtes FAISS en une seule, réduire overhead embedding

---

## Phase 3 — Tests & Validation

### #16 Valider optimisations avec tests de non-régression

**Dépend de** : #2, #3, #4

**Objectif** : S'assurer que les optimisations n'introduisent pas de bugs

**Actions** :
1. Exécuter suite de tests existante :
   ```bash
   pytest tests/ -v
   ```
2. Tests E2E :
   ```bash
   cd web && npx playwright test
   ```
3. Test manuel : analyser 10 emails et vérifier résultats identiques
4. Comparer résultats d'analyse avant/après optimisations

**Critères de validation** :
- 0 test échoué
- Résultats d'analyse identiques (pas de régression fonctionnelle)
- Performance améliorée (vs baseline)

---

### #13 Créer tests de performance (benchmarks)

**Dépend de** : #2, #3, #4

**Objectif** : Tests automatisés pour mesurer et prévenir les régressions de performance

**Fichiers à créer** :
- `tests/performance/test_context_search_perf.py`
- `tests/performance/test_note_loading_perf.py`
- `tests/performance/test_multi_pass_analysis_perf.py`

**Contenu** :

| Test | Métrique | Seuil |
|------|----------|-------|
| Context search (avec cache) | Temps réponse | < 100ms |
| Note loading (1000 notes) | Temps total | < 2s |
| Multi-pass analysis | Temps par email | < 5s |

**Exemple de test** :
```python
import pytest
import time

def test_context_search_cached_performance(context_searcher):
    # Premier appel (cache miss)
    start = time.perf_counter()
    result1 = context_searcher.search("Johan")
    cold_time = time.perf_counter() - start

    # Deuxième appel (cache hit)
    start = time.perf_counter()
    result2 = context_searcher.search("Johan")
    warm_time = time.perf_counter() - start

    assert warm_time < 0.1  # < 100ms avec cache
    assert warm_time < cold_time * 0.5  # Au moins 2x plus rapide
```

**Intégration CI** : Ajouter à GitHub Actions avec seuils d'alerte

---

## Phase 4 — Documentation

### #14 Rédiger documentation technique performance

**Dépend de** : #2, #3, #4, #13

**Fichier** : `docs/technical/performance.md`

**Contenu** :

1. **Architecture de cache**
   - Cache multi-niveaux existant (TTL par source)
   - Nouveau cache context search
   - TTLs et stratégies d'invalidation

2. **Optimisations implémentées**
   - Thread pool sizing (32 → 8)
   - Early-stop adapters
   - Batch search VectorStore
   - Déduplication O(N)

3. **Profiling**
   - Comment utiliser py-spy
   - Interprétation des flamegraphs
   - Logs `[PERF]` existants et leur format

4. **Bonnes pratiques**
   - Patterns async à suivre
   - Anti-patterns à éviter (N+1, sync blocking, etc.)
   - Checklist performance pour nouvelles features

5. **Métriques de référence**
   - Baseline documentée
   - Seuils acceptables par opération
   - Comment mesurer (outils, commandes)

---

### #15 Ajouter guide utilisateur performance/troubleshooting

**Dépend de** : #14

**Fichier** : `docs/user-guide/performance.md`

**Contenu** :

1. **Comportement normal**
   - Temps attendus pour analyse email (~3-5s)
   - Indicateurs de progression dans l'UI
   - Ce qui se passe en arrière-plan

2. **Si Scapin est lent**
   - Vérifier nombre de notes (> 5000 = impact possible)
   - Vérifier connexion IMAP (latence réseau)
   - Vider le cache si incohérences (`/valets` → Reset cache)

3. **Optimiser son usage**
   - Archiver les anciennes notes inutilisées
   - Configurer les dossiers email à ignorer
   - Réduire la profondeur de recherche contextuelle

4. **Diagnostic**
   - Où trouver les logs : `data/logs/`
   - Métriques dans page `/valets`
   - Quand signaler un problème de performance

---

## Phase 5 — Frontend (REPORTÉ)

> **Reporté après refactoring UI** — Ces tâches seront reprises une fois le refactoring UI terminé pour éviter les conflits.

| # | Tâche | Statut |
|---|-------|--------|
| #1 | Splitter API client monolithique | 🔜 Après refactoring UI |
| #6 | Auditer reactivity stores Svelte | 🔜 Après refactoring UI |
| #7 | Unifier WebSocket et HTTP polling | 🔜 Après refactoring UI |
| #9 | Lazy-load composants charts Valets | 🔜 Après refactoring UI |

---

## Phase 6 — Infrastructure (Basse priorité)

### #8 Ajouter compression Gzip aux réponses API

**Solution** : Middleware Gzip FastAPI

**Statut** : Peut être fait indépendamment, faible priorité

---

## Dépendances

```
#12 (install py-spy)
 └── #11 (profiling CPU)

#10 (baseline) + #11 (profiling CPU)
 ├── #2 (thread pool) ← Quick win immédiat
 ├── #3 (early-stop adapters)
 └── #4 (cache context search) ← Plus gros impact
      └── #5 (batch search)

#2, #3, #4 (optimisations)
 ├── #16 (tests non-régression)
 └── #13 (tests performance)
      └── #14 (doc technique)
           └── #15 (guide utilisateur)

[REPORTÉ après refactoring UI]
#1 (API client split)
#6 (audit stores) → #7 (unify WebSocket)
#9 (lazy-load charts)
```

---

## Outils

### Backend Python
| Outil | Usage | Installation |
|-------|-------|--------------|
| **py-spy** | Profiling CPU, flamegraphs | `pip install py-spy` |
| **Logs `[PERF]`** | Déjà en place pour Four Valets | Aucune |
| **`time.perf_counter()`** | Timers précis hot paths | Natif Python |
| **pytest** | Tests unitaires et performance | Déjà installé |

### Frontend (reporté)
- Lighthouse CI, vite-bundle-visualizer, Chrome DevTools

---

## Ordre d'exécution complet

```
Phase 0 — Setup
  1. #12 — Installer py-spy

Phase 1 — Mesure
  2. #10 — Établir baseline
  3. #11 — Profiling CPU

Phase 2 — Optimisations
  4. #2 — Thread pool 32→8 (quick win)
  5. #4 — Cache context search (plus gros impact)
  6. #3 — Early-stop adapters
  7. #5 — Batch search VectorStore

Phase 3 — Validation
  8. #16 — Tests non-régression
  9. #13 — Tests performance

Phase 4 — Documentation
  10. #14 — Doc technique
  11. #15 — Guide utilisateur

Phase 5 — Optionnel
  12. #8 — Gzip (si temps)

Phase 6 — Après refactoring UI
  13. #1, #6, #7, #9 — Optimisations frontend
```

---

## Critères de succès

| Métrique | Objectif |
|----------|----------|
| **Freezes UX** | Zéro hang perceptible |
| **Analyse email** | Amélioration mesurable vs baseline |
| **Context search** | Cache hit ratio > 50% |
| **Temps réponse API** | < 200ms p95 |
| **Tests** | 100% pass, 0 régression |
| **Documentation** | Technique + utilisateur complètes |

---

## Livrables

| Livrable | Fichier |
|----------|---------|
| Baseline chiffrée | `docs/plans/performance-baseline.md` |
| Flamegraph CPU | `profile.svg` |
| Tests performance | `tests/performance/*.py` |
| Doc technique | `docs/technical/performance.md` |
| Guide utilisateur | `docs/user-guide/performance.md` |

---

## Historique

| Date | Action |
|------|--------|
| 2026-01-24 | Création du plan |
| 2026-01-24 | Ajout profiling CPU py-spy (#11) |
| 2026-01-24 | Décision : focus backend, frontend reporté après refactoring UI |
| 2026-01-24 | Ajout installation py-spy (#12), tests (#13, #16), documentation (#14, #15) |
