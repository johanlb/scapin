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

| Phase | Nom | Statut |
|-------|-----|--------|
| **0** | Fondations | ✅ |
| **1** | Intelligence Email | ✅ |
| **2** | Expérience Interactive | ✅ |
| **0.5** | Architecture Cognitive | ✅ Complet |

### Phase Actuelle : 0.6 — Refactoring Valet

**Objectif** : Réorganiser les modules pour correspondre à l'architecture finale

| Actuel | Cible |
|--------|-------|
| `src/ai/` | `src/sancho/` |
| `src/cli/` | `src/jeeves/` |
| `src/core/email_processor.py` | `src/trivelin/processor.py` |

### Modules Implémentés (Phase 0.5)

| Semaine | Module | Fichiers Clés | Statut |
|---------|--------|---------------|--------|
| **1** | Fondation | `universal_event.py`, `working_memory.py`, `continuity_detector.py` | ✅ |
| **2** | Sancho | `router.py`, `model_selector.py`, `reasoning_engine.py` | ✅ |
| **3** | Passepartout | `embeddings.py`, `vector_store.py`, `note_manager.py`, `context_engine.py` | ✅ |
| **4** | Planchet + Figaro | `planning_engine.py`, `orchestrator.py`, `actions/*.py` | ✅ |
| **5** | Sganarelle | `learning_engine.py`, `feedback_processor.py`, `confidence_calibrator.py` | ✅ |

### Suite des Tests

**Global** : 867 tests, 95% couverture, 100% pass rate

| Module | Tests | Statut |
|--------|-------|--------|
| Core events | 19 | ✅ |
| Display Manager | 18 | ✅ |
| Sganarelle types | 29 | ✅ |
| Feedback Processor | 24 | ✅ |
| Sganarelle complet | 100+ | ✅ |

### Qualité du Code

**Score** : 10/10  
**Ruff** : 50 warnings non-critiques (réduit de 610)

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

## 🗺️ Feuille de Route

### Phases Suivantes

| Phase | Focus | Durée Estimée |
|-------|-------|---------------|
| **0.6** | Refactoring Valet | 2-3 semaines |
| **0.7** | API Jeeves (FastAPI + WebSockets) | 3-4 semaines |
| **0.8** | Interface Web (SvelteKit) | 6-8 semaines |
| **0.9** | PWA Mobile | 3-4 semaines |
| **2.5** | Multi-Provider IA | 4-5 semaines |
| **3** | Système Connaissances complet | 4-6 semaines |

---

## 📝 Notes de Session

### Session 2026-01-02

**Durée** : ~3 heures  
**Focus** : Documentation philosophique + Corrections tests + Cohérence

**Accomplissements** :
1. ✅ Créé **DESIGN_PHILOSOPHY.md** — Document fondateur complet
2. ✅ Créé fiche Apple Notes "Scapin — Principes de Conception"
3. ✅ Mis à jour **README.md** — Intégration philosophie, 5 principes, boucle amélioration
4. ✅ Mis à jour **CLAUDE.md** — Cohérence avec DESIGN_PHILOSOPHY.md
5. ✅ Corrigé suite tests (867 passed, 0 failed)
6. ✅ Corrigé deadlock logger (RLock)
7. ✅ Modernisé annotations types (558 corrections)

**Documents créés/modifiés** :
- `docs/DESIGN_PHILOSOPHY.md` (nouveau)
- `README.md` (amélioré)
- `CLAUDE.md` (amélioré)
- Fiche Apple Notes "Personal Knowledge Management/Scapin — Principes de Conception"

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

- Score qualité 10/10 maintenu
- Tests AVANT implémentation (TDD)
- Type hints 100%
- Docstrings complètes
- Thread-safety vérifiée

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

**Phase 0.6 — Refactoring Valet** :

1. Vérifier erreurs import restantes
2. Lancer suite tests complète — cible 100% pass
3. Commencer renommage modules :
   - `src/ai/` → `src/sancho/`
   - `src/cli/` → `src/jeeves/`
4. Mettre à jour imports dans tout le codebase

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
