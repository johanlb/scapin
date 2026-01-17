# CLAUDE.md — Contexte de Session & État du Projet

**Dernière mise à jour** : 18 janvier 2026
**Version** : v1.0.0-rc.1 (Release Candidate 1)
**Projet** : Scapin
**Dépôt** : https://github.com/johanlb/scapin
**Répertoire de travail** : `/Users/johan/Developer/scapin`

---

## 🎯 Vision & Mission

Scapin est un **gardien cognitif personnel** avec une architecture cognitive inspirée du raisonnement humain. Il transforme le flux d'emails et d'informations en connaissances organisées via une analyse IA multi-pass (v2.2), une mémoire contextuelle et une planification d'actions intelligente.

**Mission** : *"Prendre soin de Johan mieux que Johan lui-même."*

---

## 📚 Documents de Référence

| Document | Rôle | Quand consulter |
|----------|------|-----------------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | 🎯 **Fondation** | Toujours, pour comprendre l'âme du projet |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | **Technique (v1.0)** | Implémentation des modules et futur |
| **[README.md](README.md)** | **Vue d'ensemble** | Points d'entrée et vision globale |
| **[ROADMAP.md](docs/archive/historical/ROADMAP.md)** | **Archive** | Historique détaillé des sprints 1-7 |
| **[UI_VOCABULARY.md](docs/UI_VOCABULARY.md)** | **Lexique** | Mapping termes UI ↔ technique |
| **[User Guide](docs/user-guide/README.md)** | **Manuel** | Utilisation et configuration v1.0 |

---

## 🏗️ Architecture Cognitive (Les Valets)

| Valet | Module | Responsabilité | Statut |
|-------|--------|----------------|--------|
| **Trivelin** | `src/trivelin/` | Perception & triage (Multi-Pass v2.2) | ✅ |
| **Sancho** | `src/sancho/` | Raisonnement itératif & convergence | ✅ |
| **Passepartout** | `src/passepartout/` | Base de connaissances (MD + FAISS + Git) | ✅ |
| **Planchet** | `src/planchet/` | Planification & évaluation risques | ✅ |
| **Figaro** | `src/figaro/` | Orchestration DAG avec rollback | ✅ |
| **Sganarelle** | `src/sganarelle/` | Apprentissage continu du feedback | ✅ |
| **Jeeves** | `src/jeeves/` | Interface API & CLI | ✅ |

---

## 📊 État Actuel (v1.0 RC-1)

**Statut Global** : ✅ **Release Candidate 1 Validée**
- **MVP Progress** : 100% (Tous les sprints complétés)
- **Tests** : 2346 tests backend, 95% couverture, 100% pass rate.
- **Qualité** : Ruff 0 warnings, svelte-check 0 errors.

### Capacités Clés :
- **Multi-Pass v2.2** : Escalade intelligente Haiku → Sonnet → Opus.
- **Atomic Transactions** : Traitement email + enrichissement PKM indissociables.
- **Sync Apple Notes** : Synchronisation bidirectionnelle avec protection des champs IA.
- **Cross-Source Search** : Recherche unifiée (Email, Teams, Calendar, WhatsApp, Files, Web).
- **Journaling & Learning** : Boucle de feedback quotidienne pour calibration IA.

---

## 🔧 Détails Techniques & Commandes

### Fichiers Critiques
- `src/trivelin/v2_processor.py` : Orchestrateur du pipeline v2.2.
- `src/sancho/multi_pass_analyzer.py` : Logique de convergence et d'escalade.
- `src/passepartout/note_manager.py` : Gestionnaire de la base de connaissances Markdown.
- `src/core/config_manager.py` : Configuration centralisée.

### Commandes Rapides
```bash
# Développement (Backend + Frontend)
./scripts/dev.sh

# Tests
.venv/bin/pytest tests/ -v

# Qualité du code
.venv/bin/ruff check src/ --fix
cd web && npm run check

# CLI Scapin
python scapin.py --help
```

---

## 📝 Notes de Session

### 18 Janvier 2026 (Suite) — Notes UX & Dev Stability 🔧
**Objectif** : Améliorer l'expérience utilisateur des notes et la stabilité du développement.

**Fonctionnalités Notes :**
- ✅ **Recherche API** : Barre de recherche hybride (full-text + sémantique) dans la colonne 2
- ✅ **Édition titre inline** : Double-clic sur le titre pour édition directe
- ✅ **Bouton Revue Hygiène** : Analyse de qualité des notes avec suggestions (🧹)
- ✅ **Visualisation média** : Support images, audio, vidéo, PDF depuis Apple Notes

**Stabilité dev.sh :**
- ✅ **Nettoyage zombies** : Tue automatiquement les processus uvicorn/vite orphelins
- ✅ **Vérification ports** : Libère les ports 8000/5173 avant démarrage
- ✅ **Script stop.sh** : Arrêt manuel de tous les processus Scapin
- ✅ **Cleanup robuste** : Trap sur SIGINT, SIGTERM et EXIT

**Corrections API :**
- ✅ `/api/notes/{id}/metadata` : Retourne 200 avec `null` au lieu de 404 pour notes sans métadonnées SM-2

**Performance Notes (Optimisation majeure) :**
- ✅ **Index de métadonnées léger** : `.scapin_notes_meta.json` chargé instantanément (~0.02s)
- ✅ **`get_notes_summary()`** : Retourne métadonnées sans lire les fichiers
- ✅ **`get_notes_tree()` optimisé** : Utilise summaries pour l'arbre, charge seulement pinned + récentes
- ✅ **`list_notes()` optimisé** : Filtrage/pagination sur métadonnées, charge uniquement page demandée
- ✅ **Chargement lazy du cache** : Cache se remplit à la demande (évite lecture 792+ fichiers au démarrage)

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Arbre des notes (2ème appel) | 5+ min | 0.003s | ~100,000x |
| Liste notes avec filtre | 5+ min | ~0.01s | ~30,000x |

**Fichiers clés créés/modifiés :**
- `src/jeeves/api/routers/media.py` (nouveau) : Endpoint `/api/media/{uuid}` pour médias Apple Notes
- `web/src/lib/utils/markdown.ts` : Extension `apple-media://` pour marked.js
- `scripts/dev.sh` (refonte) : Gestion robuste des processus
- `scripts/stop.sh` (nouveau) : Arrêt manuel des serveurs

### 18 Janvier 2026 — Documentation Cleanup (Final Stage) 🏁
**Objectif** : Finaliser le passage à la v1.0 RC-1 par un nettoyage radical de la documentation.
- ✅ Archivage de `ROADMAP.md` et `BREAKING_CHANGES.md` dans `docs/archive/historical/`.
- ✅ Intégration des recommandations stratégiques dans `ARCHITECTURE.md`.
- ✅ Optimisation de `CLAUDE.md` (suppression de 1500+ lignes d'historique archivé).
- ✅ Mise à jour de tous les liens internes vers les nouvelles localisations d'archives.

### Archives d'historique
- [Sessions Janvier 7-17](docs/archive/session-history/2026-01-07-to-2026-01-17.md) (Stabilisation v1.0)
- [Sessions Janvier 2-6](docs/archive/session-history/2026-01-02-to-2026-01-06.md) (Fondations Cognitive Architecture)

---

## 🤝 Travailler avec Claude Code

### Méthodologie "Scapin-Clean"
1. **Évaluation** : Demander confirmation avant de modifier des fichiers critiques.
2. **Atomicité** : Un commit par fonctionnalité ou correction cohérente.
3. **Qualité** : 0 warning Ruff toléré. Type hints obligatoires.
4. **Information en couches** : Toujours proposer des résumés actionnables (Niveau 1) avant les détails techniques (Niveau 3).

### Checklist de fin de tâche
- [ ] Tests backend (`pytest`) passent.
- [ ] Vérification types frontend (`npm run check`) passe.
- [ ] `ROADMAP.md` (Archive) et `CLAUDE.md` à jour.
- [ ] `walkthrough.md` généré pour les changements importants.

---
**Version Actuelle** : [v1.0.0-rc.1](https://github.com/johanlb/scapin/releases/tag/v1.0.0-rc.1)
