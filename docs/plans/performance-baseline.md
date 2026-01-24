# Baseline Performance — 24 Janvier 2026

**Objectif** : Documenter l'état de performance actuel avant optimisations
**Backend PID** : 11171
**Profiling** : py-spy 0.4.1

---

## Flamegraph CPU

**Fichier** : `data/profiling/baseline-20260124-121436.svg`
**Samples** : 4560
**Durée** : 45 secondes

> Ouvrir le fichier SVG dans un navigateur pour analyse interactive.
> Les barres les plus larges = fonctions consommant le plus de CPU.

---

## Métriques Four Valets (logs [PERF])

Les logs `[PERF]` dans `src/sancho/multi_pass_analyzer.py` capturent :

| Phase | Description | Métrique |
|-------|-------------|----------|
| Starting | Début analyse | Timestamp |
| Grimaud | Pass 1 - Triage initial | ms + modèle |
| Context search | Recherche entités | ms + nb notes |
| Bazin | Pass 2 - Enrichissement | ms + modèle |
| Planchet | Pass 3 - Critique | ms + modèle |
| Mousqueton | Pass 4 - Synthèse (optionnel) | ms + modèle |
| Total | Temps total | ms + tokens |

### Observations Queue

| Email | Passes | Modèle | Status |
|-------|--------|--------|--------|
| Menaces de mise à mort | 4 passes | opus | pending |
| RE: CONSTRUCTION PLANS | 3 passes | opus | pending |
| Request for Cost Breakdown | 3 passes | opus | pending |
| Bilan au 31 juillet 2025 | 3 passes | opus | pending |
| FW: Location H45 | 3 passes | opus | pending |

---

## Configuration Actuelle

### Thread Pool (note_manager.py:1723)
```python
max_workers = min(32, len(files_to_load))  # ACTUEL
# Recommandation : min(8, len(files_to_load))
```

### Context Search
- Pas de cache actuellement
- Chaque analyse déclenche des recherches vectorielles

### Adapters Email
- Pas d'early-stop
- Scan complet même si quota atteint

---

## Prochaines Étapes

1. **Analyser le flamegraph** pour identifier les hotspots CPU
2. **Implémenter Quick Wins** :
   - #2 Thread pool 32→8
   - #4 Cache context search
   - #3 Early-stop adapters
3. **Mesurer après optimisations** pour comparer

---

## Analyse Flamegraph (session 24/01/2026)

**Fichier analysé** : `data/profiling/analysis-20260124-121931.svg`
**Samples** : 22,741 (analyse réelle pendant reanalysis)

### Découverte Clé

**~47% du temps = Attente API Anthropic (I/O wait, pas CPU)**

| Valet | % temps | Samples |
|-------|---------|---------|
| Planchet | 16.64% | 3,785 |
| Bazin | 13.57% | 3,087 |
| Mousqueton | 11.82% | 2,689 |
| Grimaud | 5.05% | 1,148 |

### Implications

1. **Pas un problème CPU** : Le bottleneck est l'attente des réponses Claude
2. **Parallelisation déjà en place** : `asyncio.Semaphore(3)` dans workflow.py
3. **Modèle sélection optimisé** : Haiku → Sonnet → Opus selon confiance
4. **Quick wins backend** : Toujours valides mais impact limité

### Décision (historique)

~~**Plan performance mis en pause** pour prioritiser le nettoyage du workflow~~ → **REPRIS**

Le workflow cleanup est terminé (voir `docs/plans/archive/workflow-cleanup-autofetch.md`).

---

## Plan d'Optimisation Corrigé

> Conforme aux directives CLAUDE.md et skill /perf

### Phase 0 : Nouveau Baseline

1. Générer nouveau flamegraph (fetch réparé)
2. Capturer métriques : notes load, context search, email fetch
3. Exécuter tests performance
4. Documenter valeurs de référence

### Phase 1 : Thread Pool 32 → 8

**Fichier critique** : `note_manager.py` (confirmation Johan requise)

| Métrique | Avant | Cible | Seuil |
|----------|-------|-------|-------|
| `get_all_notes()` 150 notes | 450ms | 350ms | -20% |

### Phase 2 : Cache Context Search

**Prérequis** : Dépendance `cachetools`

- TTLCache (maxsize=100, ttl=60s)
- Invalidation obligatoire lors rebuild FAISS
- Logs cache hit/miss

| Métrique | Avant | Cible | Seuil |
|----------|-------|-------|-------|
| Context search | 500ms | 150ms | -70% |

### Phase 3 : Early-Stop Emails

Détection : list-id, list-unsubscribe, auto-submitted

| Métrique | Avant | Cible | Seuil |
|----------|-------|-------|-------|
| Emails skipped | 0% | 30% | 30% |
| Temps batch 10 emails | 10s | 7s | -30% |

### Phase 4 : Documentation

- `docs/architecture/performance.md` (nouveau)
- Mise à jour ce fichier avec résultats

### Phase 5 : Mesures Finales

Comparer avec baseline et documenter gains réels.

---

## Avertissement Impact

**Rappel** : ~47% du temps = attente API Anthropic (I/O wait).

Impact global estimé sur latence utilisateur : **~10-15%**.

---

## Historique

| Date | Action |
|------|--------|
| 2026-01-24 | Création baseline, flamegraph généré |
| 2026-01-24 | Analyse flamegraph : bottleneck = I/O API, pas CPU |
| 2026-01-24 | **PAUSE** : Priorité au cleanup workflow |
| 2026-01-24 | Workflow cleanup terminé, plan **REPRIS** |
| 2026-01-24 | Plan corrigé (conformité CLAUDE.md, cachetools, invalidation FAISS) |
