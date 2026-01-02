# CLAUDE.md — Contexte de Session & État du Projet

**Dernière mise à jour** : 2 janvier 2026  
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

## 📊 État Actuel (2 janvier 2026)

### Phases Complétées

| Phase | Nom | Statut | Lignes Code |
|-------|-----|--------|-------------|
| **0** | Fondations | ✅ | — |
| **1** | Intelligence Email | ✅ | — |
| **2** | Expérience Interactive | 80% 🚧 | — |
| **0.5** | Architecture Cognitive | ✅ 95% | ~8000 lignes |

### Modules Valets Implémentés

| Valet | Module | Lignes | Statut |
|-------|--------|--------|--------|
| **Sancho** | `reasoning_engine.py` | ~700 | ✅ |
| **Passepartout** | `context_engine`, `embeddings`, `note_manager`, `vector_store` | ~2000 | ✅ |
| **Planchet** | `planning_engine.py` | ~400 | ✅ |
| **Figaro** | `orchestrator.py`, `actions/` | ~770 | ✅ |
| **Sganarelle** | 8 modules (learning, feedback, calibration, patterns, etc.) | ~4100 | ✅ |
| **Trivelin** | À créer (fusion avec email_processor) | 0 | 📋 |
| **Jeeves** | À créer (migration de cli/) | 0 | 📋 |

### Phase Actuelle : 0.6 — Refactoring Valet

**Objectif** : Finaliser l'architecture valet et valider le flux bout-en-bout

| Tâche | État |
|-------|------|
| Modules valets créés | ✅ Fait |
| `src/ai/` → `src/sancho/` | 📋 À faire |
| `src/cli/` → `src/jeeves/` | 📋 À faire |
| `src/core/email_processor.py` → `src/trivelin/` | 📋 À faire |
| Flux bout-en-bout validé | 📋 À faire |

### Nouvelles Phases (Alignées DESIGN_PHILOSOPHY.md)

| Phase | Nom | Priorité | Focus |
|-------|-----|----------|-------|
| **1.0** | Journaling & Feedback Loop | 🔴 CRITIQUE | Boucle d'amélioration |
| **1.1** | Flux Entrants Unifiés | 🔴 HAUTE | Trivelin multi-source |
| **1.2** | Intégration Teams | 🔴 HAUTE | Messages + réponses + appels |
| **1.3** | Intégration Calendrier | 🟠 MOYENNE-HAUTE | Autonomie progressive |
| **1.4** | Système de Briefing | 🟠 MOYENNE-HAUTE | Matin, pré-réunion |

### Suite des Tests

**Global** : 967 tests, 95% couverture, 100% pass rate

| Catégorie | Tests | Statut |
|-----------|-------|--------|
| Unit tests | 912 | ✅ |
| Integration tests | 55 | ✅ |
| Skipped | 52 | ⏭️ |

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

**Traitement Email** (legacy → Trivelin) :
```
src/core/email_processor.py           # Logique principale
src/integrations/email/imap_client.py # Opérations IMAP
```

**CLI** (→ Jeeves) :
```
src/cli/app.py                        # Commandes Typer
src/cli/display_manager.py            # Rendu Rich
src/cli/menu.py                       # Menus interactifs
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
| **0.6** | Refactoring Valet & flux bout-en-bout | 🏗️ EN COURS |
| **1.0** | Journaling & Feedback Loop | 🔴 CRITIQUE |
| **1.1** | Flux Entrants Unifiés (Trivelin) | 🔴 HAUTE |

### Priorités Q2 2026

| Phase | Focus | Priorité |
|-------|-------|----------|
| **1.2** | Intégration Teams | 🔴 HAUTE |
| **1.3** | Intégration Calendrier | 🟠 MOYENNE-HAUTE |
| **1.4** | Système de Briefing | 🟠 MOYENNE-HAUTE |

### Phases Ultérieures

| Phase | Focus |
|-------|-------|
| **0.7** | API Jeeves (FastAPI) |
| **0.8** | Interface Web (SvelteKit) |
| **0.9** | PWA Mobile |
| **2.5** | Multi-Provider IA (consensus) |

---

## 📝 Notes de Session

### Session 2026-01-02 (Soir) — Plan v2.0 Complet

**Focus** : Refonte complète du plan de développement

**Accomplissements** :
1. ✅ Analysé les dépendances réelles entre phases
2. ✅ Identifié les gaps dans les spécifications existantes
3. ✅ **Restructuré entièrement le plan en 4 couches** :
   - **Couche 0** : Fondation (Phase 0.6 - Refactoring Valet)
   - **Couche 1** : Email Excellence MVP (Phases 1.0-1.1)
   - **Couche 2** : Multi-Source (Phases 1.2-1.4)
   - **Couche 3** : Intelligence Proactive (Phase 1.5)
   - **Couche 4** : Amélioration Continue (Phase 1.6)
4. ✅ **Créé spécifications fonctionnelles détaillées** pour chaque phase :
   - User Stories en format Gherkin
   - Modèles de données (dataclasses Python)
   - Diagrammes d'architecture
   - Tables de livrables avec estimations
   - Critères de succès mesurables
5. ✅ Ajouté graphe de dépendances visuel
6. ✅ Mappé les Quick Wins de DESIGN_PHILOSOPHY aux phases
7. ✅ Calendrier révisé Q1-Q4 2026

**Décisions clés** :
- Journaling divisé : Phase 1.1 (email-only MVP) + Phase 1.6 (complet multi-source)
- Teams avant Calendrier (réutilise Graph API)
- Briefings après Calendrier (nécessite les événements)
- Couches techniques (API/Web/PWA) après valeur fonctionnelle

### Session 2026-01-02 (Après-midi)

**Focus** : Révision initiale du plan de développement

**Accomplissements** :
1. ✅ Analysé état réel vs ROADMAP — Découvert Phase 0.5 à 95% (pas 20%)
2. ✅ Mis à jour ROADMAP.md avec l'état réel des modules valets
3. ✅ Tests : 967 passed (912 unit + 55 integration)

**Changement majeur** : Le plan passe d'une approche "couches techniques" (API → Web → Mobile) à une approche "valeur fonctionnelle" (Journaling → Teams → Briefings).

### Session 2026-01-02 (Matin)

**Focus** : Documentation philosophique + Corrections tests

**Accomplissements** :
1. ✅ Créé **DESIGN_PHILOSOPHY.md** — Document fondateur complet
2. ✅ Corrigé suite tests (867 → 967 tests)
3. ✅ Corrigé deadlock logger (RLock)
4. ✅ Modernisé annotations types

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
```

---

## 🤝 Travailler avec Claude Code

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

# Règles principales activées (voir pyproject.toml) :
# - E/W : Erreurs de style PEP8
# - F : Erreurs PyFlakes (imports inutilisés, variables non définies)
# - I : Import sorting (isort)
# - UP : Modernisation Python (type hints PEP 585)
# - B : Bug patterns (flake8-bugbear)
# - SIM : Simplifications de code
# - ARG : Arguments inutilisés
```

Conventions ruff :
- Arguments intentionnellement inutilisés : préfixer avec `_` (ex: `_frame`)
- Exceptions chaînées : `raise Exception(...) from e` ou `from None`
- Importer pour type checking : `from typing import TYPE_CHECKING`
- Simplifier conditions : retourner directement au lieu de `if x: return True; return False`

**Tests** :
- Tests unitaires pour chaque module
- Tests d'intégration pour les flux critiques
- Tests de performance pour valider les fondations (temps de réponse, mémoire)
- TDD encouragé mais pas obligatoire — tests et code peuvent être écrits en parallèle

**Commits** :
- Chaque commit doit être production-ready
- Pas de dette technique acceptée
- Code exploratoire → branche séparée, puis nettoyage avant merge

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

## 🎯 Objectifs Prochaine Session

### Option A : Compléter Phase 0.6 (Refactoring Valet)

1. Migrer `src/ai/router.py`, `model_selector.py` → `src/sancho/`
2. Migrer `src/cli/` → `src/jeeves/`
3. Migrer `src/core/email_processor.py` → `src/trivelin/processor.py`
4. Mettre à jour tous les imports
5. Valider flux bout-en-bout : Email → Trivelin → Sancho → ... → Sganarelle

### Option B : Démarrer Phase 1.0 (Journaling)

1. Concevoir structure du journal quotidien
2. Implémenter pré-remplissage automatique
3. Créer interface CLI journaling (questionary)
4. Intégrer avec Sganarelle pour feedback loop

### Recommandation

Compléter **Phase 0.6 d'abord** (flux bout-en-bout validé) avant de commencer le journaling.
Cela garantit que l'architecture cognitive fonctionne de bout en bout.

---

## 📚 Index Documentation Complet

| Document | Description | Priorité |
|----------|-------------|----------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | Principes philosophiques, fondements théoriques | 🔴 Critique |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Architecture technique, spécifications valets | 🟠 Haute |
| **[ROADMAP.md](ROADMAP.md)** | Plan développement par phases | 🟡 Moyenne |
| **[README.md](README.md)** | Vue d'ensemble projet | 🟢 Intro |
| **[BREAKING_CHANGES.md](BREAKING_CHANGES.md)** | Changements cassants, migrations | 📋 Référence |
| **[MIGRATION.md](MIGRATION.md)** | Migration PKM → Scapin | 📋 Référence |

---

**Dernière mise à jour** : 2 janvier 2026 par Claude  
**Prochaine révision** : Début prochaine session
