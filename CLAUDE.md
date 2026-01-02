# CLAUDE.md — Contexte de Session & État du Projet

**Dernière mise à jour** : 2 janvier 2026  
**Projet** : Scapin (anciennement PKM System)  
**Dépôt** : https://github.com/johanlb/scapin  
**Répertoire de travail** : `/Users/johan/Developer/scapin`

---

## 🎯 Démarrage Rapide

### Qu'est-ce que Scapin ?

Scapin est un **gardien cognitif personnel** avec une architecture inspirée du raisonnement humain. Il transforme le flux d'emails et d'informations en connaissances organisées via une analyse IA multi-passes, une mémoire contextuelle et une planification d'actions intelligente.

**Mission fondamentale** : *"Prendre soin de Johan mieux que Johan lui-même."*

### Documents de Référence Essentiels

| Document | Rôle | À lire quand |
|----------|------|--------------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | 🎯 **Document fondateur** — Principes philosophiques, fondements théoriques (Extended Mind, Stiegler, Wegner), vision du partenariat cognitif | Toujours consulter pour comprendre le *pourquoi* des décisions |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Spécifications techniques — Comment les valets fonctionnent | Pour le *comment* technique |
| **[ROADMAP.md](ROADMAP.md)** | Plan de développement par phases | Pour prioriser les tâches |

### Principes de Conception Clés

Ces principes guident TOUTES les décisions de développement :

1. **Qualité sur vitesse** — 10-20s de raisonnement pour la BONNE décision
2. **Proactivité maximale** — Anticiper, suggérer, challenger, rappeler
3. **Intimité totale** — Aucune limite d'accès pour l'efficacité
4. **Apprentissage progressif** — Seuils de confiance appris, pas de règles rigides
5. **Construction propre** — Lent mais bien construit dès le début

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

---

## 📊 État Actuel (2 janvier 2026)

### Phase Actuelle : Phase 0.5 — Architecture Cognitive

**Statut** : Semaine 1 ✅ complète, Semaine 2 en cours

**Modules Implémentés** :

| Semaine | Module | Fichiers | Statut |
|---------|--------|----------|--------|
| **1** | Fondation | `universal_event.py`, `working_memory.py`, `email_normalizer.py`, `continuity_detector.py` | ✅ |
| **2** | Sancho (IA) | `router.py`, `model_selector.py`, `templates.py`, `reasoning_engine.py` | ✅ |
| **3** | Passepartout | `embeddings.py`, `vector_store.py`, `note_manager.py`, `context_engine.py` | ✅ |
| **4** | Planchet + Figaro | `planning_engine.py`, `orchestrator.py`, `actions/*.py` | ✅ |
| **5** | Sganarelle | `learning_engine.py`, `feedback_processor.py`, `confidence_calibrator.py`, `pattern_store.py` | ✅ |

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

**Score Ruff** : 50 warnings non-critiques (réduit de 610)
- ✅ 558 problèmes auto-corrigés (annotations types, imports)
- ✅ Toutes les erreurs critiques résolues
- Restant : ARG002, B904, SIM102 (style)

### Corrections Récentes (Session 2026-01-02)

| Correction | Fichier | Impact |
|------------|---------|--------|
| Deadlock RLock | `logger.py` | Tests ne bloquent plus |
| Import get_event_bus | `events/__init__.py` | 2 tests intégration passent |
| Type annotations | 462 fichiers | Conformité Python 3.9+ |
| Constantes manquantes | `feedback_processor.py` | 4 erreurs F821 résolues |
| TYPE_CHECKING | `error_store.py` | Imports circulaires résolus |

---

## 🗺️ Feuille de Route Développement

### Phase 0.5 : Architecture Cognitive — ✅ COMPLÈTE

Tous les modules valets sont implémentés :
- Trivelin (perception)
- Sancho (raisonnement)
- Passepartout (connaissances)
- Planchet (planification)
- Figaro (exécution)
- Sganarelle (apprentissage)

### Phase 0.6 : Refactoring Valet (Prochaine)

**Objectif** : Réorganiser les modules pour correspondre à l'architecture finale

| Actuel | Cible |
|--------|-------|
| `src/ai/` | `src/sancho/` |
| `src/cli/` | `src/jeeves/` |
| `src/core/email_processor.py` | `src/trivelin/processor.py` |

### Phases Suivantes

| Phase | Focus | Durée |
|-------|-------|-------|
| **0.7** | API Jeeves (FastAPI + WebSockets) | 3-4 semaines |
| **0.8** | Interface Web (SvelteKit) | 6-8 semaines |
| **0.9** | PWA Mobile | 3-4 semaines |
| **2.5** | Multi-Provider IA | 4-5 semaines |
| **3** | Système Connaissances complet | 4-6 semaines |

---

## 🔧 Détails Techniques

### Fichiers Clés

**Architecture Cognitive** :
```
src/core/events/universal_event.py    # PerceivedEvent, Entity, EventType
src/core/memory/working_memory.py     # WorkingMemory, Hypothesis, ReasoningPass
src/core/processing_events.py         # EventBus, ProcessingEvent
src/core/config_manager.py            # Configuration Pydantic
```

**Traitement Email** (legacy → Trivelin) :
```
src/core/email_processor.py           # Logique principale
src/core/processors/email_analyzer.py # Analyse IA
src/integrations/email/imap_client.py # Opérations IMAP
```

**CLI** (→ Jeeves) :
```
src/cli/app.py                        # Commandes Typer
src/cli/display_manager.py            # Rendu Rich
src/cli/menu.py                       # Menus interactifs
src/cli/review_mode.py                # Interface révision
```

**Apprentissage** (Sganarelle) :
```
src/sganarelle/learning_engine.py     # Apprentissage feedback
src/sganarelle/feedback_processor.py  # Analyse feedback
src/sganarelle/knowledge_updater.py   # Mises à jour PKM
src/sganarelle/pattern_store.py       # Détection patterns
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

**Feature Flags** :
- `enable_cognitive_reasoning` : Activer raisonnement multi-passes Sancho
- `preview_mode` : Dry-run sans exécuter les actions
- `auto_execute` : Exécution auto pour décisions haute confiance

### Commandes de Test

```bash
# Tous les tests
.venv/bin/pytest tests/ -v

# Par module
.venv/bin/pytest tests/unit/test_universal_event.py -v
.venv/bin/pytest tests/unit/test_working_memory.py -v
.venv/bin/pytest tests/unit/test_sganarelle_*.py -v
.venv/bin/pytest tests/integration/ -v

# Couverture
.venv/bin/pytest tests/ --cov=src --cov-report=html
```

### Vérifications Qualité

```bash
# Linting Ruff
.venv/bin/python3 -m ruff check src/
.venv/bin/python3 -m ruff check src/ --fix  # Auto-fix

# Type checking (TODO)
mypy src/
```

---

## 📝 Notes de Session

### Session 2026-01-02

**Durée** : ~3 heures  
**Focus** : Corrections tests + Qualité code + Documentation philosophique

**Accomplissements** :
1. ✅ Corrigé blocage tests (deadlock logger → RLock)
2. ✅ Corrigé erreurs import (get_event_bus)
3. ✅ Modernisé annotations types (558 corrections)
4. ✅ Corrigé constantes undefined (4 corrections)
5. ✅ Suite tests : 867 passed, 0 failed
6. ✅ **Créé DESIGN_PHILOSOPHY.md** — Document fondateur Scapin
7. ✅ **Mis à jour README.md** — Intégration philosophie, cohérence
8. ✅ **Mis à jour CLAUDE.md** — Références documentation

**Commits** :
- `d339120` - Fix deadlock PKMLogger (RLock)
- `e9c7966` - Fix import get_event_bus
- `898d6ca` - Corrections linting Ruff (462 issues)
- `8db8aa6` - Fix constantes undefined
- `d646625` - TYPE_CHECKING pour ErrorStore

**Insights Clés** :
- Thread-safety : RLock pour acquisition imbriquée
- Imports : Organisation critique pour architecture propre
- Documentation : DESIGN_PHILOSOPHY.md capture l'âme du projet

### Session 2025-12-31 (Précédente)

**Focus** : Phase 0.5 Semaine 1 complète  
**Résultat** : 92 tests, 95%+ couverture, fondation production-ready

---

## 🚀 Commandes Rapides

### Développement

```bash
# Activer venv
source .venv/bin/activate

# Lancer tests
.venv/bin/pytest tests/ -v

# Linting
.venv/bin/ruff check src/ --fix

# Traiter emails (preview)
python scapin.py process --preview

# Révision interactive
python scapin.py review
```

### Git

```bash
# Statut
git status

# Créer branche
git checkout -b feature/nom-feature

# Commit avec template
git add -A
git commit -m "feat: description courte

- Détail 1
- Détail 2

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Push
git push origin feature/nom-feature
```

---

## 🤝 Travailler avec Claude Code

### Chargement du Contexte

**Toujours commencer par** :
1. Lire ce fichier (CLAUDE.md)
2. Consulter DESIGN_PHILOSOPHY.md pour le *pourquoi*
3. Consulter ARCHITECTURE.md pour le *comment*
4. Vérifier ROADMAP.md pour les priorités

### Avant Toute Modification

1. Exécuter les tests pour établir la baseline
2. Vérifier la branche git actuelle
3. Relire les commits récents pour le contexte

### Standards de Qualité

- Maintenir score qualité 10/10
- Écrire tests AVANT implémentation (TDD)
- Type hints 100%
- Docstrings complètes
- Thread-safety vérifiée

### Principes de Conception (rappel)

Toujours respecter les principes de DESIGN_PHILOSOPHY.md :

1. **Information en couches** (Niveau 1/2/3)
2. **Apprentissage progressif** (seuils appris, pas de règles rigides)
3. **Proactivité maximale** (anticiper > attendre)
4. **Qualité > Vitesse** (10-20s pour bonne décision)

### Checklist Fin de Session

- [ ] Tous les tests passent
- [ ] Vérifications qualité passent
- [ ] Documentation mise à jour (CLAUDE.md, ROADMAP.md si applicable)
- [ ] Commits poussés
- [ ] Notes de session enregistrées

---

## 🎯 Objectifs Prochaine Session

**Phase 0.6 — Refactoring Valet** :

1. Corriger erreurs import restantes
2. Lancer suite tests complète — cible 100% pass
3. Commencer renommage modules si souhaité :
   - `src/ai/` → `src/sancho/ai/`
   - `src/cli/` → `src/jeeves/`
4. Mettre à jour documentation architecture

**Contexte à charger** :
- Ce fichier (CLAUDE.md)
- DESIGN_PHILOSOPHY.md
- ARCHITECTURE.md

**Livrables attendus** :
- Tests 100% pass
- Qualité code 10/10 maintenue
- Documentation cohérente

---

## 📚 Index Documentation

| Document | Description | Quand consulter |
|----------|-------------|-----------------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | Principes philosophiques, fondements théoriques, vision | Décisions de conception |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Architecture système, spécifications valets | Implémentation technique |
| **[ROADMAP.md](ROADMAP.md)** | Plan développement par phases | Priorisation tâches |
| **[BREAKING_CHANGES.md](BREAKING_CHANGES.md)** | Changements cassants, migrations | Mises à jour API |
| **[MIGRATION.md](MIGRATION.md)** | Migration PKM → Scapin | Nouveaux utilisateurs |
| **[README.md](README.md)** | Vue d'ensemble projet | Introduction |

---

**Dernière mise à jour** : 2 janvier 2026 par Claude  
**Prochaine révision** : Début prochaine session
