# Scapin — Feuille de Route Produit

**Dernière mise à jour** : 4 janvier 2026
**Version** : 0.9.0-alpha (suite de PKM v3.1.0)
**Phase actuelle** : Phase 0.9 PWA Mobile ✅ → Phases avancées

---

## 📊 Résumé Exécutif

### Statut Global

**État** : ✅ **Journaling Multi-Source Complété** — Phase 1.6 terminée

| Métrique | Valeur |
|----------|--------|
| **Tests** | 1414+ tests (1414 backend + 8 frontend), 95% couverture, 100% pass rate |
| **Qualité Code** | 10/10 (Ruff 0 warnings) |
| **Dépôt** | https://github.com/johanlb/scapin |
| **Identité précédente** | PKM System (archivé) |

### Vision

> **"Prendre soin de Johan mieux que Johan lui-même."**

Transformer un processeur d'emails en **assistant personnel intelligent** avec :
- 🎭 **Architecture valet** — Inspirée du valet rusé de Molière
- 🧠 **Raisonnement cognitif** — Multi-passes itératif (pas une IA one-shot)
- 🌐 **Interfaces modernes** — Web + Mobile PWA (en plus du CLI)
- 📚 **Gestion connaissances** — Base personnelle avec recherche sémantique
- 🔄 **Entrées multi-modales** — Emails, fichiers, questions, calendrier, documents

📖 *Document fondateur : [DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md) — Principes philosophiques et théoriques*

### Dernières Étapes (4 janvier 2026)

- ✅ **Phase 1.6 Journaling Complet** — Multi-source (Email, Teams, Calendar, OmniFocus), calibration Sganarelle, revues hebdo/mensuelles (38 tests)
- ✅ **Phase 0.8 Interface Web** — SvelteKit + TailwindCSS v4, design Liquid Glass, auth JWT, WebSockets
- ✅ **Phase 0.9 PWA Mobile** — Service Worker, Push Notifications, Deeplinks, Share Target
- ✅ **Phase 0.7 API Jeeves MVP** — FastAPI, endpoints system/briefing/journal, services async
- ✅ **Phase 1.4 Système de Briefing** — Generator, display multi-couches, CLI (58 tests)
- ✅ Suite de tests complète — 1414+ tests passent (1414 backend + 8 frontend)
- ✅ Qualité code — Ruff 0 warnings, svelte-check 0 warnings

---

## 📚 Documentation de Référence

### Hiérarchie des Documents

| Document | Rôle | Contenu |
|----------|------|---------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | 🎯 **Fondateur** | Pourquoi — Principes, théorie, vision |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | 🏗️ **Technique** | Comment — Spécifications, composants |
| **[ROADMAP.md](ROADMAP.md)** | 📅 **Opérationnel** | Quand — Phases, priorités, calendrier |
| **[CLAUDE.md](CLAUDE.md)** | 🤖 **Session** | État actuel pour Claude Code |

### Principes Directeurs (de DESIGN_PHILOSOPHY.md)

Ces principes guident TOUTES les décisions de développement :

1. **Qualité sur vitesse** — 10-20s pour la BONNE décision
2. **Proactivité maximale** — Anticiper, suggérer, challenger
3. **Information en couches** — Niveau 1 (30s) / Niveau 2 (2min) / Niveau 3 (complet)
4. **Apprentissage progressif** — Seuils appris, pas de règles rigides
5. **Construction propre** — Lent mais bien construit dès le début

---

## ✅ Phases Complétées

### Phase 0 : Fondations (100%) ✅

**Durée** : Semaines 1-2  
**Tests** : 115 tests, 95%+ couverture

**Livrables** :
- [x] Structure projet et organisation
- [x] Gestion configuration (Pydantic Settings)
- [x] Système logging structuré (JSON/Text)
- [x] Gestion état thread-safe (singleton)
- [x] Schémas Pydantic pour tous types
- [x] Interfaces ABC pour architecture propre
- [x] Fondation système health check
- [x] Gestionnaire templates (Jinja2)
- [x] Framework CLI (Typer + Rich)
- [x] Suite tests complète avec fixtures
- [x] Pipeline CI/CD (GitHub Actions)
- [x] Pre-commit hooks (black, ruff, mypy)
- [x] Outillage développement (Makefile)

---

### Phase 1 : Traitement Email (100%) ✅

**Durée** : Semaines 3-4  
**Tests** : 62 tests, 90%+ couverture

**Livrables** :
- [x] EmailProcessor avec support multi-comptes
- [x] AIRouter avec intégration Claude Haiku/Sonnet/Opus
- [x] Client IMAP avec support encodage UTF-8
- [x] Traitement par lots avec parallélisation
- [x] Rate limiting et logique retry
- [x] Système gestion erreurs complet :
  - ErrorManager (singleton thread-safe avec cache LRU)
  - ErrorStore (persistance SQLite)
  - RecoveryEngine (backoff exponentiel, protection timeout)
- [x] Opérations thread-safe avec double-check locking
- [x] Sanitisation contexte pour sérialisabilité JSON
- [x] Protection timeout (pas de blocages infinis)
- [x] Cache LRU pour optimisation mémoire

---

### Phase 1.5 : Système Événements & Display Manager (100%) ✅

**Durée** : Semaine 5  
**Tests** : 44 tests, 100% pass rate

**Livrables** :
- [x] Architecture événementielle (EventBus avec pub/sub)
- [x] Système événements thread-safe
- [x] ProcessingEvent avec 17 types d'événements
- [x] DisplayManager avec rendu Rich :
  - Icônes actions : 📦 Archive, 🗑️ Suppression, ✅ Tâche, 📚 Référence, ↩️ Réponse
  - Icônes catégories : 💼 Travail, 👤 Personnel, 💰 Finance, 🎨 Art, 📰 Newsletter
  - Barres confiance : ████ 95% (vert) à ██░░ 55% (orange)
  - Aperçus contenu (80 chars max)
  - Suivi progression (Email 1/10, 2/10...)
- [x] Affichage séquentiel du traitement parallèle
- [x] Mode display logger (cacher logs console pendant traitement)

---

### Phase 1.6 : Système Monitoring Santé (100%) ✅

**Durée** : Semaine 5  
**Tests** : 31 tests, 100% couverture

**Livrables** :
- [x] Système health check avec 4 services :
  - IMAP (connectivité, authentification)
  - API IA (API Anthropic, avec ModelSelector)
  - Espace disque (monitoring répertoire données)
  - File d'attente (suivi taille queue révision)
- [x] Enum ServiceStatus (healthy, degraded, unhealthy, unknown)
- [x] HealthCheckService singleton avec cache (60s TTL)
- [x] Commandes CLI (health, stats, config, settings)

---

### Phase 1.7 : Sélecteur Modèle IA (100%) ✅

**Durée** : Semaine 5  
**Tests** : 25 tests, 100% pass rate

**Livrables** :
- [x] Classe ModelSelector avec sélection intelligente par tier
- [x] Enum ModelTier (HAIKU, SONNET, OPUS)
- [x] Découverte dynamique modèles via API Anthropic
- [x] Sélection automatique du dernier modèle par tier
- [x] Stratégie fallback multi-niveaux
- [x] Modèles fallback statiques ordonnés du plus récent au plus ancien
- [x] Intégration avec health checks

---

### Phase 2 : Système Menu Interactif (80%) 🚧

**Tests** : 108 tests (menu, review, queue storage)

**Complété** ✅ :
- [x] **Menu Interactif** (navigation questionary)
  - Menu principal avec 6 options
  - Navigation flèches
  - Gestion gracieuse Ctrl+C
  - Style personnalisé
- [x] **Support Multi-Comptes**
  - EmailAccountConfig (modèle Pydantic)
  - Configuration multi-comptes (format .env)
  - MultiAccountProcessor pour traitement séquentiel
  - UI sélection comptes (checkbox pour batch)
  - Statistiques par compte
- [x] **Système File de Révision**
  - QueueStorage (JSON, singleton thread-safe)
  - InteractiveReviewMode avec UI Rich
  - Actions : Approuver/Modifier/Rejeter/Passer
  - CLI gestion file (list, stats, clear)
  - Suivi corrections IA pour apprentissage
- [x] **Intégration CLI**
  - Commande `python scapin.py menu`
  - `python scapin.py` lance menu par défaut
  - Compatibilité arrière complète

**Restant** :
- [ ] Script migration config (90% complet)
- [ ] Tests intégration (20% complet)
- [ ] Documentation utilisateur (30% complet)

---

## ✅ Phase 0.5 : Architecture Cognitive (95% Complète)

**Statut** : ✅ Complet — Tous les modules valets implémentés
**Durée réelle** : 1 semaine (accélération significative)
**Priorité** : 🔴 CRITIQUE
**Complexité** : 🔴 TRÈS HAUTE

#### Alignement avec DESIGN_PHILOSOPHY.md

Cette phase implémente les concepts théoriques du document fondateur :

| Concept Philosophique | Implémentation Technique |
|----------------------|-------------------------|
| Extended Mind (Clark & Chalmers) | WorkingMemory comme extension cognitive |
| Mémoire Transactive (Wegner) | Passepartout comme mémoire partagée |
| Pharmacologie (Stiegler) | Journaling et feedback pour production de savoir |
| Information en couches | Niveau 1/2/3 dans tous les outputs |
| Apprentissage progressif | Sganarelle avec seuils de confiance adaptatifs |

#### Semaine 1 : Événements Universels & Mémoire de Travail ✅

**Livrables** :
- ✅ `src/core/events/universal_event.py` (PerceivedEvent, Entity, EventType, UrgencyLevel)
- ✅ `src/core/memory/working_memory.py` (WorkingMemory, Hypothesis, ReasoningPass, ContextItem)
- ✅ `src/core/events/normalizers/email_normalizer.py` (Email → PerceivedEvent)
- ✅ `src/core/memory/continuity_detector.py` (Détection continuité thread)

**Métriques Qualité** :
- Tests : 92 tests, 95%+ couverture, 100% pass rate
- Code : Dataclasses immutables (frozen=True), validation complète, type hints 100%
- Documentation : Docstrings complètes, exemples d'usage, notes architecturales

**Améliorations Session 2026-01-02** :
- ✅ Corrigé blocage tests (deadlock PKMLogger - Lock → RLock)
- ✅ Corrigé erreurs import (ré-export get_event_bus)
- ✅ Modernisé annotations types (462 corrections auto via ruff)
- ✅ Corrigé constantes undefined (4 seuils apprentissage)
- ✅ Corrigé imports TYPE_CHECKING (référence forward ErrorStore)
- ✅ Suite tests : 867 passed, 0 failed, 14 skipped
- ✅ Qualité code : 610 → 50 warnings (suggestions style non-critiques)

#### Semaine 2 : Sancho — Moteur de Raisonnement ✅

**Statut** : ✅ Complet

**Livrables réalisés** :
- [x] `src/ai/router.py` — Routage IA avec circuit breaker + rate limiting (923 lignes)
- [x] `src/ai/model_selector.py` — Sélection modèle multi-provider (202 lignes)
- [x] `src/ai/templates.py` — Gestion templates Jinja2 (296 lignes)
- [x] `src/sancho/reasoning_engine.py` — Raisonnement itératif 5 passes (700+ lignes)
- [x] Tests : 100+ tests, 100% pass rate

**Architecture du Raisonnement** (aligné sur DESIGN_PHILOSOPHY.md) :

```
Principe : "Qualité sur vitesse" — 10-20s pour la BONNE décision

ReasoningEngine :
  Passe 1 : Analyse initiale (sans contexte) → ~60-70% confiance
  Passe 2 : Enrichissement contexte (recherche PKM) → ~75-85% confiance
  Passe 3 : Raisonnement profond (multi-étapes) → ~85-92% confiance
  Passe 4 : Validation (cross-provider) → ~90-96% confiance
  Passe 5 : Clarification utilisateur (async) → ~95-99% confiance

Convergence : Arrêt quand confiance ≥ 95% OU max 5 passes
```

**Critères de Succès** :
- ✅ Tous tests passent (100+ nouveaux tests)
- ✅ Convergence démontrée sur emails de test
- ✅ Feature flag permet rollback vers analyse simple
- ✅ Performance < 20s par email en moyenne
- ✅ Qualité code 10/10 maintenue

#### Semaine 3 : Passepartout — Base de Connaissances & Contexte ✅

**Statut** : ✅ Complet

**Livrables réalisés** :
- [x] `src/passepartout/embeddings.py` — Embeddings sentence-transformers (340 lignes)
- [x] `src/passepartout/vector_store.py` — Recherche sémantique FAISS (544 lignes)
- [x] `src/passepartout/note_manager.py` — Notes Markdown + Git (681 lignes)
- [x] `src/passepartout/context_engine.py` — Récupération contexte pour Passe 2 (467 lignes)

**Alignement Philosophique** : Implémente la "mémoire transactive" de Wegner — Johan sait que Passepartout "sait".

#### Semaine 4 : Planchet + Figaro — Planification & Exécution ✅

**Statut** : ✅ Complet

**Livrables réalisés** :
- [x] `src/planchet/planning_engine.py` — Planification avec évaluation risques (~400 lignes)
- [x] `src/figaro/actions/base.py` — Classe de base Action (204 lignes)
- [x] `src/figaro/actions/email.py` — Actions email (archive, delete, reply) (507 lignes)
- [x] `src/figaro/orchestrator.py` — Exécution DAG avec rollback (~260 lignes)

**Modes d'exécution** (de DESIGN_PHILOSOPHY.md) :
- **Auto** : Confiance haute + risque faible → Exécute, informe après
- **Review** : Confiance moyenne OU risque moyen → Prépare, attend validation
- **Manual** : Confiance basse OU risque haut → Présente options, Johan décide

#### Semaine 5 : Sganarelle — Apprentissage & Intégration ✅

**Statut** : ✅ Complet

**Livrables réalisés** (8 modules, ~4100 lignes total) :
- [x] `src/sganarelle/learning_engine.py` — Apprentissage continu depuis feedback (597 lignes)
- [x] `src/sganarelle/feedback_processor.py` — Analyse feedback (567 lignes)
- [x] `src/sganarelle/confidence_calibrator.py` — Calibration confiance (577 lignes)
- [x] `src/sganarelle/pattern_store.py` — Détection patterns (562 lignes)
- [x] `src/sganarelle/provider_tracker.py` — Suivi performance providers (616 lignes)
- [x] `src/sganarelle/knowledge_updater.py` — Mise à jour base de connaissances (588 lignes)
- [x] `src/sganarelle/types.py` — Types et structures de données (382 lignes)
- [x] `src/sganarelle/constants.py` — Constantes et seuils (220 lignes)

**Alignement Philosophique** : Implémente la "boucle d'amélioration continue" — journaling → enrichissement fiches → meilleures analyses → feedback.

---

## 🎯 Plan de Développement v2.0 (Refonte Complète)

> **Principe directeur** : Livrer de la **valeur incrémentale** par couches.
> Chaque couche est utilisable indépendamment et enrichit les suivantes.

### 📊 Graphe de Dépendances

```
                    ┌─────────────────────────────────────────────────────────┐
                    │            COUCHE 4 : AMÉLIORATION CONTINUE             │
                    │                                                         │
                    │  Phase 1.6 : Journaling Complet                        │
                    │  (synthèse toutes sources + feedback Sganarelle)       │
                    └─────────────────────────────────────────────────────────┘
                                              ▲
                                              │ dépend de
                    ┌─────────────────────────────────────────────────────────┐
                    │            COUCHE 3 : INTELLIGENCE PROACTIVE            │
                    │                                                         │
                    │  Phase 1.5 : Système de Briefing                       │
                    │  (briefing matin, pré-réunion, post-réunion)           │
                    └─────────────────────────────────────────────────────────┘
                                              ▲
                                              │ dépend de
                    ┌─────────────────────────────────────────────────────────┐
                    │              COUCHE 2 : MULTI-SOURCE                    │
                    │                                                         │
                    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
                    │  │ Phase 1.2   │  │ Phase 1.3   │  │ Phase 1.4   │     │
                    │  │ Teams       │  │ Calendrier  │  │ LinkedIn    │     │
                    │  └─────────────┘  └─────────────┘  └─────────────┘     │
                    └─────────────────────────────────────────────────────────┘
                                              ▲
                                              │ dépend de
                    ┌─────────────────────────────────────────────────────────┐
                    │            COUCHE 1 : EMAIL EXCELLENCE (MVP)            │
                    │                                                         │
                    │  Phase 1.0 : Trivelin Email                            │
                    │  Phase 1.1 : Journaling Email (feedback basique)       │
                    └─────────────────────────────────────────────────────────┘
                                              ▲
                                              │ dépend de
                    ┌─────────────────────────────────────────────────────────┐
                    │              COUCHE 0 : FONDATION                       │
                    │                                                         │
                    │  Phase 0.6 : Refactoring Valet + Flux Bout-en-Bout     │
                    │  (valider que l'architecture cognitive fonctionne)     │
                    └─────────────────────────────────────────────────────────┘
```

### 🎁 Quick Wins (de DESIGN_PHILOSOPHY.md)

| Quick Win | Livré par | Valeur |
|-----------|-----------|--------|
| **Inbox Zero assisté** | Phase 1.0 | Emails pré-analysés, brouillons prêts |
| **Tri données existantes** | Phase 1.1 | Transformation emails → fiches organisées |
| **Contexte avant réunion** | Phase 1.5 | Briefing pré-réunion automatique |
| **Moins d'oublis** | Phase 1.6 | Journaling capture tout, rien ne se perd |

---

## 📋 COUCHE 0 : FONDATION

### Phase 0.6 : Refactoring Valet & Validation Bout-en-Bout

**Statut** : ✅ COMPLÉTÉ (2 janvier 2026)
**Priorité** : 🔴 BLOQUANT (était)

#### Objectif
Finaliser l'architecture valet et **prouver** que le flux cognitif complet fonctionne sur un email réel.

#### Accomplissements

| Migration | Détails | État |
|-----------|---------|------|
| `src/ai/` → `src/sancho/` | router.py, model_selector.py, templates.py, providers/ | ✅ |
| `src/cli/` → `src/jeeves/` | cli.py, display_manager.py, menu.py, review_mode.py | ✅ |
| `email_processor.py` → `src/trivelin/` | processor.py | ✅ |
| Mise à jour imports | 38 fichiers modifiés | ✅ |
| Tests passent | 967 tests (100% pass rate) | ✅ |
| Ruff clean | 0 warnings | ✅ |

#### Structure Finale des Valets

```
src/
├── sancho/          # AI + Reasoning (~2650 lignes)
├── jeeves/          # CLI Interface (~2500 lignes)
├── trivelin/        # Event Perception (~740 lignes)
├── passepartout/    # Knowledge Base (~2000 lignes)
├── planchet/        # Planning (~400 lignes)
├── figaro/          # Execution (~770 lignes)
└── sganarelle/      # Learning (~4100 lignes)
```

#### Critères de Succès
- [x] 100% des tests existants passent après migration
- [x] Documentation des imports mise à jour
- [x] Aucun fichier orphelin dans les anciens emplacements
- [ ] Test d'intégration E2E (flux complet) — À faire en Phase 1.0

---

## 📋 COUCHE 1 : EMAIL EXCELLENCE (MVP)

### Phase 1.0 : Trivelin Email — Pipeline Cognitif Complet

**Statut** : ✅ COMPLÉTÉ (2 janvier 2026)
**Priorité** : 🔴 CRITIQUE
**Durée estimée** : 1 journée (était 2 semaines)
**Dépendance** : Phase 0.6

#### Objectif
Transformer le traitement email existant pour utiliser pleinement l'architecture cognitive avec Trivelin comme point d'entrée unique.

#### Accomplissements

| Composant | Fichier | Description |
|-----------|---------|-------------|
| **ProcessingConfig** | `src/core/config_manager.py` | Configuration opt-in pour le pipeline cognitif |
| **CognitivePipeline** | `src/trivelin/cognitive_pipeline.py` | Orchestrateur central coordonnant tous les valets |
| **ActionFactory** | `src/trivelin/action_factory.py` | Conversion EmailAnalysis → Figaro Actions |
| **Intégration Processor** | `src/trivelin/processor.py` | Intégration du pipeline dans `_analyze_email()` |
| **Tests unitaires** | `tests/unit/test_cognitive_pipeline.py` | 15 tests couvrant init, process, timeout, config |

**Flux implémenté** :
```
Email → EmailNormalizer → ReasoningEngine (Sancho) → PlanningEngine (Planchet)
      → ActionOrchestrator (Figaro) → LearningEngine (Sganarelle)
```

**Configuration** :
```python
# src/core/config_manager.py
class ProcessingConfig(BaseModel):
    enable_cognitive_reasoning: bool = False  # Opt-in, OFF par défaut
    cognitive_confidence_threshold: float = 0.85
    cognitive_timeout_seconds: int = 20
    cognitive_max_passes: int = 5
    fallback_on_failure: bool = True  # Fallback au mode legacy
```

**Activation** :
```bash
# Dans .env
PROCESSING__ENABLE_COGNITIVE_REASONING=true
```

#### User Stories

```gherkin
STORY 1 : Traitement email intelligent
En tant que Johan,
Je veux que Scapin analyse mes emails avec raisonnement multi-passes
Afin d'avoir des décisions de qualité (pas du one-shot).

Critères d'acceptation :
- Chaque email passe par Sancho (1-5 passes selon complexité)
- La confiance finale est ≥ 85% ou l'email va en file de révision
- Le temps de traitement est < 20s par email
- Je peux voir la trace de raisonnement si je le souhaite

---

STORY 2 : Brouillons de réponse
En tant que Johan,
Je veux que Scapin prépare des brouillons de réponse pour les emails nécessitant action
Afin de réduire mon temps de réponse.

Critères d'acceptation :
- Les emails identifiés comme "nécessite réponse" ont un brouillon
- Le brouillon est dans le style de Johan (appris)
- Je peux modifier et envoyer, ou rejeter
- Le feedback améliore les futurs brouillons

---

STORY 3 : Extraction d'entités
En tant que Johan,
Je veux que Scapin extraie automatiquement les personnes, dates, et projets des emails
Afin d'enrichir ma base de connaissances.

Critères d'acceptation :
- Nouvelles personnes → proposition de fiche (pas création automatique)
- Dates importantes → proposition de rappel/tâche
- Projets mentionnés → liaison avec fiches existantes
```

#### Modèle de Données

```python
@dataclass(frozen=True)
class EmailProcessingResult:
    """Résultat du traitement d'un email par Trivelin → ... → Sganarelle"""

    # Identification
    email_id: str
    message_id: str

    # Perception (Trivelin)
    perceived_event: PerceivedEvent
    extracted_entities: list[Entity]

    # Raisonnement (Sancho)
    reasoning_result: ReasoningResult
    passes_executed: int
    final_confidence: float

    # Planification (Planchet)
    planned_actions: list[PlannedAction]
    risk_assessment: RiskAssessment
    execution_mode: ExecutionMode  # AUTO | REVIEW | MANUAL

    # Exécution (Figaro)
    executed_actions: list[ExecutedAction]
    execution_status: ExecutionStatus

    # Outputs
    draft_reply: Optional[DraftReply]
    proposed_tasks: list[ProposedTask]
    proposed_notes: list[ProposedNote]

    # Métriques
    processing_duration_seconds: float
    tokens_used: TokenUsage

@dataclass
class DraftReply:
    """Brouillon de réponse préparé par Scapin"""
    subject: str
    body: str
    tone: str  # formal, casual, friendly
    confidence: float
    alternatives: list[str]  # Autres formulations possibles
```

#### Architecture Technique

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRIVELIN                                  │
│  src/trivelin/                                                   │
│  ├── __init__.py                                                │
│  ├── processor.py          # Point d'entrée, orchestration      │
│  ├── email_fetcher.py      # Récupération IMAP (existant)       │
│  └── normalizers/                                                │
│      ├── __init__.py                                            │
│      ├── base.py           # Interface Normalizer               │
│      └── email_normalizer.py  # Email → PerceivedEvent          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ PerceivedEvent
┌─────────────────────────────────────────────────────────────────┐
│                         SANCHO                                   │
│  (Existant - reasoning_engine.py)                               │
│  Raisonnement multi-passes jusqu'à confiance ≥ 95%              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ ReasoningResult
┌─────────────────────────────────────────────────────────────────┐
│                        PLANCHET                                  │
│  (Existant - planning_engine.py)                                │
│  Planification avec évaluation des risques                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ ActionPlan
┌─────────────────────────────────────────────────────────────────┐
│                         FIGARO                                   │
│  (Existant - orchestrator.py)                                   │
│  Exécution DAG avec rollback                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ ExecutionResult
┌─────────────────────────────────────────────────────────────────┐
│                       SGANARELLE                                 │
│  (Existant - learning_engine.py)                                │
│  Apprentissage du feedback                                      │
└─────────────────────────────────────────────────────────────────┘
```

#### Livrables

| Livrable | Fichier | Lignes estimées |
|----------|---------|-----------------|
| Processeur Trivelin | `src/trivelin/processor.py` | ~400 |
| Actions brouillon réponse | `src/figaro/actions/draft_reply.py` | ~200 |
| Tests unitaires | `tests/unit/test_trivelin_*.py` | ~500 |
| Test intégration | `tests/integration/test_email_e2e.py` | ~200 |

#### Critères de Succès
- [ ] 10 emails de test traités avec succès
- [ ] Temps moyen < 15s par email
- [ ] Confiance moyenne > 85%
- [ ] Brouillons générés pour emails "nécessite réponse"
- [ ] Entités extraites et proposées (pas forcément acceptées)

---

### Phase 1.1 : Journaling Email — Feedback Basique

**Statut** : ✅ COMPLÉTÉ (2 janvier 2026)
**Priorité** : 🔴 CRITIQUE
**Durée estimée** : 2 semaines
**Dépendance** : Phase 1.0

#### Accomplissements

| Module | Fichier | Lignes | État |
|--------|---------|--------|------|
| Models | `src/jeeves/journal/models.py` | ~350 | ✅ |
| Generator | `src/jeeves/journal/generator.py` | ~400 | ✅ |
| Interactive | `src/jeeves/journal/interactive.py` | ~300 | ✅ |
| Feedback | `src/jeeves/journal/feedback.py` | ~250 | ✅ |
| CLI Command | `src/jeeves/cli.py` (journal) | ~80 | ✅ |
| Tests | `tests/unit/test_journal_*.py` | ~500 | ✅ (56 tests) |

**Total** : ~1880 lignes de code + tests

#### Objectif
Implémenter le journaling quotidien sur la base des emails traités. C'est la **boucle de feedback minimale** qui permet à Sganarelle d'apprendre.

#### User Stories

```gherkin
STORY 1 : Journal pré-rempli
En tant que Johan,
Je veux que Scapin pré-remplisse mon journal quotidien avec les emails traités
Afin de ne pas partir d'une page blanche.

Critères d'acceptation :
- Commande `scapin journal` génère un brouillon
- Le brouillon liste : emails traités, actions prises, décisions
- Je peux compléter/corriger en ~15 minutes
- Le format est Markdown avec YAML frontmatter

---

STORY 2 : Questions ciblées
En tant que Johan,
Je veux que Scapin me pose des questions ciblées sur les éléments incertains
Afin d'améliorer sa compréhension.

Critères d'acceptation :
- Questions sur les emails où confiance < 80%
- Questions sur les nouvelles personnes détectées
- Format interactif (questionary) avec choix rapides
- Possibilité de passer une question

---

STORY 3 : Enrichissement fiches
En tant que Johan,
Je veux que mes corrections enrichissent automatiquement les fiches
Afin que Scapin s'améliore.

Critères d'acceptation :
- Correction "cette personne est X" → mise à jour fiche personne
- Correction "ce projet est Y" → mise à jour fiche projet
- Correction "cette action était fausse" → feedback Sganarelle
- Historique des corrections conservé
```

#### Modèle de Données

```python
@dataclass
class JournalEntry:
    """Entrée de journal quotidien"""

    # Métadonnées
    date: date
    created_at: datetime
    updated_at: datetime

    # Contenu pré-rempli par Scapin
    emails_processed: list[EmailSummary]
    tasks_completed: list[TaskSummary]  # Depuis OmniFocus
    decisions_made: list[DecisionSummary]

    # Questions de Scapin
    questions: list[JournalQuestion]

    # Réponses de Johan
    answers: dict[str, Any]

    # Ajouts manuels de Johan
    notes: str
    reflections: str

    # Feedback pour Sganarelle
    corrections: list[Correction]

    # Statut
    status: JournalStatus  # DRAFT | IN_PROGRESS | COMPLETED

@dataclass
class JournalQuestion:
    """Question posée par Scapin"""
    id: str
    category: QuestionCategory  # PERSON | PROJECT | DECISION | CLARIFICATION
    question: str
    context: str  # Pourquoi Scapin pose cette question
    options: list[str]  # Choix rapides proposés
    related_entity_id: Optional[str]
    priority: int  # 1-5, 5 = plus important

@dataclass
class Correction:
    """Correction apportée par Johan"""
    original_analysis: str
    corrected_analysis: str
    correction_type: CorrectionType  # CATEGORY | ACTION | ENTITY | OTHER
    entity_id: Optional[str]
    feedback_strength: float  # 0-1, importance de la correction
```

#### Format Journal (Markdown)

```markdown
---
date: 2026-01-03
status: completed
emails_processed: 12
corrections: 2
duration_minutes: 14
---

# Journal du 3 janvier 2026

## 📧 Emails Traités (12)

### Haute importance (3)
- **Marie Dupont** : Budget Q2 - [Archivé] ✅
  - Action : Tâche créée "Réviser budget Q2" (due: 10 jan)
- **Client ABC** : Proposition commerciale - [En attente] ⏳
  - Brouillon réponse préparé
- **Direction** : Réunion stratégique - [Archivé] ✅
  - Événement calendrier détecté

### Normale (7)
- 3 newsletters archivées automatiquement
- 2 notifications LinkedIn (priorité basse)
- 2 emails internes traités

### Basse priorité (2)
- Spam filtré

## ❓ Questions de Scapin

### Q1 : Nouvelle personne détectée
> "Jean Martin" apparaît pour la première fois. Qui est-ce ?
- [x] Collègue Eufonie
- [ ] Client
- [ ] Fournisseur
- [ ] Autre : ___

### Q2 : Clarification projet
> L'email de Marie mentionne "Projet Alpha". Est-ce lié à "Initiative Q2" ?
- [x] Oui, c'est le même projet
- [ ] Non, projets différents

## 📝 Notes personnelles

(Ajoutées par Johan)

Journée productive. La proposition pour ABC nécessite une relecture demain matin.

## 🔄 Corrections

1. Email de Jean classé "personnel" → devrait être "professionnel Eufonie"
2. Priorité newsletter TechCrunch trop haute → baisser à "basse"
```

#### Interface CLI

```bash
# Générer le brouillon du journal
$ scapin journal
📅 Génération du journal du 3 janvier 2026...
✅ 12 emails traités aujourd'hui
❓ 2 questions à répondre

# Mode interactif
$ scapin journal --interactive
? [1/2] "Jean Martin" apparaît pour la première fois. Qui est-ce ?
  ○ Collègue Eufonie
  ○ Client
  ○ Fournisseur
  ○ Autre (saisir)
> Collègue Eufonie ✓

? [2/2] L'email de Marie mentionne "Projet Alpha". Est-ce lié à "Initiative Q2" ?
  ○ Oui, c'est le même projet
  ○ Non, projets différents
> Oui ✓

📝 Voulez-vous ajouter des notes personnelles ? (o/N) o
> Journée productive. La proposition pour ABC nécessite une relecture demain.

✅ Journal complété en 4 minutes
📊 Feedback envoyé à Sganarelle (2 corrections, 1 nouvelle entité)
```

#### Livrables

| Livrable | Fichier | Lignes estimées |
|----------|---------|-----------------|
| Générateur journal | `src/jeeves/journal/generator.py` | ~300 |
| Modèles journal | `src/jeeves/journal/models.py` | ~200 |
| Interface CLI | `src/jeeves/journal/cli.py` | ~250 |
| Intégration Sganarelle | `src/sganarelle/journal_feedback.py` | ~150 |
| Storage journal | `src/passepartout/journal_store.py` | ~200 |
| Tests | `tests/unit/test_journal_*.py` | ~400 |

#### Critères de Succès
- [ ] Journal généré en < 5s
- [ ] Session journaling complète en < 15 min (objectif DESIGN_PHILOSOPHY)
- [ ] Corrections intégrées dans Sganarelle
- [ ] Nouvelles entités ajoutées à Passepartout
- [ ] Historique des journaux consultable

---

## 📋 COUCHE 2 : MULTI-SOURCE

### Phase 1.2 : Intégration Microsoft Teams

**Statut** : ✅ COMPLÉTÉ (2 janvier 2026)
**Priorité** : 🔴 HAUTE
**Durée réelle** : 1 journée
**Dépendance** : Phase 1.0

#### Objectif
Intégrer les messages Teams dans le flux Trivelin. Teams est critique car c'est le canal principal pour Eufonie/Skiillz.

#### User Stories

```gherkin
STORY 1 : Lecture messages Teams
En tant que Johan,
Je veux que Scapin lise mes messages Teams comme il lit mes emails
Afin d'avoir une vue unifiée de mes communications.

Critères d'acceptation :
- Messages Teams passent par Trivelin → même pipeline
- Priorisation : mentions directes > channels importants > autres
- Pas de duplication si même info par email et Teams

---

STORY 2 : Brouillons réponse Teams
En tant que Johan,
Je veux que Scapin prépare des brouillons de réponse Teams
Afin de répondre rapidement.

Critères d'acceptation :
- Brouillon adapté au format Teams (court, informel)
- Option d'envoyer directement ou modifier
- Tracking des réponses envoyées

---

STORY 3 : Contexte avant appel Teams
En tant que Johan,
Je veux un briefing avant chaque appel Teams planifié
Afin d'être préparé.

Critères d'acceptation :
- Notification 10 min avant l'appel
- Briefing : participants, historique, points à aborder
- Intégration avec calendrier
```

#### Architecture Technique

```python
# Configuration Microsoft Graph
@dataclass
class TeamsConfig:
    tenant_id: str
    client_id: str
    client_secret: str  # Ou certificat
    scopes: list[str] = field(default_factory=lambda: [
        "Chat.Read",
        "Chat.ReadWrite",
        "ChannelMessage.Read.All",
        "User.Read",
        "Calendars.Read"
    ])

# Normalizer Teams
class TeamsNormalizer(BaseNormalizer):
    """Convertit un message Teams en PerceivedEvent"""

    def normalize(self, teams_message: TeamsMessage) -> PerceivedEvent:
        return PerceivedEvent(
            id=f"teams_{teams_message.id}",
            source=EventSource.TEAMS,
            title=self._extract_title(teams_message),
            content=teams_message.body.content,
            timestamp=teams_message.created_datetime,
            entities=self._extract_entities(teams_message),
            metadata={
                "channel_id": teams_message.channel_id,
                "chat_id": teams_message.chat_id,
                "is_mention": teams_message.mentions_me,
                "importance": teams_message.importance,
                "reply_to": teams_message.reply_to_id,
            },
            perception_confidence=0.95
        )
```

#### Stratégie de Polling

```python
class TeamsPoller:
    """Polling des messages Teams avec delta queries"""

    # Fréquences de polling
    POLL_INTERVALS = {
        "mentions": timedelta(minutes=1),      # Mentions directes : rapide
        "important_channels": timedelta(minutes=5),  # Channels Eufonie/Skiillz
        "other_channels": timedelta(minutes=15),     # Autres channels
        "chats": timedelta(minutes=2),               # Messages privés
    }

    async def poll(self):
        """Polling avec delta pour éviter les doublons"""
        delta_link = self.get_delta_link()
        new_messages = await self.graph_client.get_messages(delta_link)

        for message in new_messages:
            if self._should_process(message):
                yield message
```

#### Livrables Réalisés

| Livrable | Fichier | Lignes |
|----------|---------|--------|
| Auth MSAL | `src/integrations/microsoft/auth.py` | ~160 |
| Client Graph API | `src/integrations/microsoft/graph_client.py` | ~200 |
| Models Teams | `src/integrations/microsoft/models.py` | ~220 |
| Client Teams | `src/integrations/microsoft/teams_client.py` | ~160 |
| Normalizer Teams | `src/integrations/microsoft/teams_normalizer.py` | ~240 |
| Processor Teams | `src/trivelin/teams_processor.py` | ~260 |
| Actions Teams | `src/figaro/actions/teams.py` | ~330 |
| Tests | `tests/unit/test_teams_*.py` | 116 tests |

#### Critères de Succès
- [x] OAuth fonctionnel avec Microsoft 365
- [x] Messages Teams dans le flux Trivelin
- [x] Brouillons de réponse générés
- [x] Latence polling < 2 min pour mentions
- [x] Pas de rate limiting (respect quotas Graph API)

**Commande** : `scapin teams [--poll] [--interactive] [--limit] [--since]`

---

### Phase 1.3 : Intégration Calendrier

**Statut** : ✅ COMPLÉTÉ (3 janvier 2026)
**Priorité** : 🟠 MOYENNE-HAUTE
**Durée réelle** : 1 journée
**Dépendance** : Phase 1.2 (réutilise Graph API)

#### Objectif
Lire les calendriers (iCloud + Exchange) pour alimenter les briefings et le contexte.

#### User Stories

```gherkin
STORY 1 : Vue unifiée calendriers
En tant que Johan,
Je veux que Scapin voie tous mes calendriers (perso + pro)
Afin d'avoir une vue complète de mon emploi du temps.

Critères d'acceptation :
- iCloud Calendar (perso + AWCS)
- Exchange Calendar (Eufonie/Skiillz)
- Détection des conflits cross-calendriers
- Respect des permissions (pas de modification sans validation)

---

STORY 2 : Briefing automatique
En tant que Johan,
Je veux un briefing avant chaque réunion importante
Afin d'être préparé.

Critères d'acceptation :
- Notification configurable (10 min par défaut)
- Contenu : participants, historique, contexte, points à discuter
- Format adapté (court pour standup, détaillé pour client)

---

STORY 3 : Autonomie progressive (DESIGN_PHILOSOPHY 7.3)
En tant que Johan,
Je veux que Scapin apprenne quand il peut modifier mon calendrier
Afin qu'il devienne plus autonome sur les patterns établis.

Critères d'acceptation :
- Phase 1 : Lecture + suggestions seulement
- Phase 2 : "Je propose ce créneau, j'ajoute ?" (après N validations)
- Phase 3 : Ajout automatique pour types validés
- Tracking des patterns d'approbation dans Sganarelle
```

#### Modèle Autonomie Progressive

```python
@dataclass
class CalendarAutonomyLevel:
    """Niveau d'autonomie pour un type d'événement"""
    event_type: str  # "standup", "1:1", "client_meeting", etc.
    approvals: int  # Nombre de fois Johan a approuvé
    rejections: int  # Nombre de fois Johan a rejeté

    @property
    def approval_rate(self) -> float:
        total = self.approvals + self.rejections
        return self.approvals / total if total > 0 else 0

    @property
    def autonomy_level(self) -> int:
        """
        1 = Lecture seule (< 5 approbations ou taux < 80%)
        2 = Suggestion avec validation (5-15 approbations, taux >= 80%)
        3 = Autonome (> 15 approbations, taux >= 95%)
        """
        if self.approvals < 5 or self.approval_rate < 0.8:
            return 1
        elif self.approvals < 15 or self.approval_rate < 0.95:
            return 2
        else:
            return 3
```

#### Livrables Réalisés

| Livrable | Fichier | Lignes |
|----------|---------|--------|
| Models Calendar | `src/integrations/microsoft/calendar_models.py` | ~400 |
| Client Calendar | `src/integrations/microsoft/calendar_client.py` | ~400 |
| Normalizer Calendar | `src/integrations/microsoft/calendar_normalizer.py` | ~400 |
| Processor Calendar | `src/trivelin/calendar_processor.py` | ~400 |
| Actions Calendar | `src/figaro/actions/calendar.py` | ~580 |
| Tests | `tests/unit/test_calendar_*.py` | 92 tests |

#### Critères de Succès
- [x] OAuth fonctionnel avec Microsoft 365
- [x] Événements calendrier dans le flux Trivelin
- [x] Détection urgence basée sur proximité temporelle
- [x] Actions create/respond/block/task
- [x] Réutilisation 100% de GraphClient

**Commande** : `scapin calendar [--poll] [--briefing] [--hours] [--limit]`

---

### Phase 1.4 : Système de Briefing

**Statut** : ✅ COMPLÉTÉ (3 janvier 2026)
**Priorité** : 🟠 MOYENNE-HAUTE
**Durée réelle** : 1 journée
**Dépendance** : Phase 1.3 (Calendrier)

#### Objectif
Créer le système de briefing contextuel qui prépare Johan avant chaque interaction importante.

#### Livrables Réalisés

| Livrable | Fichier | Lignes |
|----------|---------|--------|
| Models Briefing | `src/jeeves/briefing/models.py` | ~400 |
| Generator Briefing | `src/jeeves/briefing/generator.py` | ~450 |
| Display Briefing | `src/jeeves/briefing/display.py` | ~400 |
| CLI Command | `src/jeeves/cli.py` (briefing) | ~80 |
| Tests | `tests/unit/test_briefing_*.py` | 58 tests |

#### Critères de Succès
- [x] Briefing matin généré automatiquement
- [x] Briefing pré-réunion avec contexte participants
- [x] Information en 3 niveaux (DESIGN_PHILOSOPHY)
- [x] Affichage Rich multi-couches

**Commande** : `scapin briefing [--morning/-m] [--meeting/-M <id>] [--hours/-H] [--output/-o]`

---

### Phase 1.5 : Intégration LinkedIn (Priorité Basse)

**Statut** : 📋 Planifié
**Priorité** : 🟢 BASSE
**Durée estimée** : 1-2 semaines
**Dépendance** : Phase 1.0

#### Objectif
Intégrer les messages LinkedIn avec filtrage agressif (beaucoup de spam/prospection).

#### Scope Limité
- ✅ Lecture messages uniquement
- ✅ Filtrage agressif (spam, prospection)
- ❌ Pas de publication de contenu (hors scope v1.0)
- ❌ Pas de gestion du profil

#### Livrables

| Livrable | Fichier | Lignes estimées |
|----------|---------|-----------------|
| Client LinkedIn API | `src/integrations/linkedin/client.py` | ~200 |
| Normalizer LinkedIn | `src/trivelin/normalizers/linkedin_normalizer.py` | ~150 |
| Filtre spam | `src/trivelin/filters/linkedin_spam.py` | ~100 |

---

## 📋 COUCHE 3 : INTELLIGENCE PROACTIVE

> **Note** : Le Système de Briefing (anciennement Phase 1.5) a été déplacé en Phase 1.4 et est maintenant **COMPLÉTÉ**.
> Voir la section Phase 1.4 ci-dessus pour les détails.

### Types de Briefings Implémentés

| Type | Déclencheur | Contenu | Commande |
|------|-------------|---------|----------|
| **Briefing Matin** | Manuel | Priorités, réunions, emails en attente | `scapin briefing -m` |
| **Pré-Réunion** | Manuel | Participants, historique, contexte | `scapin briefing -M <id>` |

---

## 📋 COUCHE 4 : AMÉLIORATION CONTINUE

### Phase 1.6 : Journaling Complet Multi-Source ✅

**Statut** : ✅ COMPLÉTÉ (4 janvier 2026)
**Priorité** : 🔴 CRITIQUE
**Durée réelle** : 1 journée
**Dépendance** : Phases 1.1, 1.2, 1.3

#### Objectif
Étendre le journaling basique (Phase 1.1) pour synthétiser TOUTES les sources et boucler complètement avec Sganarelle.

#### Différence avec Phase 1.1

| Aspect | Phase 1.1 (Basique) | Phase 1.6 (Complet) |
|--------|---------------------|---------------------|
| Sources | Emails uniquement | Emails + Teams + Calendrier + OmniFocus |
| Questions | Clarifications simples | Questions sur patterns, préférences, calibration |
| Feedback | Corrections ponctuelles | Calibration complète Sganarelle par source |
| Revues | Quotidienne seulement | Quotidienne + Hebdo + Mensuelle |

#### Livrables Réalisés

| Livrable | Fichier | État |
|----------|---------|------|
| Modèles multi-source | `src/jeeves/journal/models.py` | ✅ |
| Providers multi-source | `src/jeeves/journal/providers/` | ✅ |
| Revues hebdo/mensuelle | `src/jeeves/journal/reviews.py` | ✅ |
| Calibration Sganarelle | `src/jeeves/journal/feedback.py` | ✅ |
| API Router Journal | `src/jeeves/api/routers/journal.py` | ✅ |
| Service Journal | `src/jeeves/api/services/journal_service.py` | ✅ |
| Frontend Journal | `web/src/routes/journal/+page.svelte` | ✅ |
| Tests | 38 nouveaux tests | ✅ |

#### API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/journal/{date}` | Récupérer journal d'une date |
| GET | `/api/journal/list` | Liste des journals (pagination) |
| POST | `/api/journal/{date}/answer` | Répondre à une question |
| POST | `/api/journal/{date}/correction` | Soumettre correction |
| POST | `/api/journal/{date}/complete` | Marquer comme terminé |
| GET | `/api/journal/weekly/{week}` | Revue hebdomadaire |
| GET | `/api/journal/monthly/{month}` | Revue mensuelle |
| GET | `/api/journal/calibration` | Données calibration |
| POST | `/api/journal/{date}/export` | Export markdown/json/html |

#### Critères de Succès
- [x] Multi-source : Email, Teams, Calendar, OmniFocus intégrés
- [x] Revues hebdo/mensuelles avec détection patterns
- [x] Calibration par source avec tracking précision
- [x] API REST complète pour le journal
- [x] Frontend avec tabs multi-sources
- [x] 38 nouveaux tests (1414 total)

---

## 📋 COUCHES TECHNIQUES

### Phase 0.7 : API Jeeves (MVP)

**Statut** : ✅ COMPLÉTÉ (3 janvier 2026)
**Durée réelle** : 1 journée

#### Livrables Réalisés

| Livrable | Fichier | Lignes |
|----------|---------|--------|
| App Factory | `src/jeeves/api/app.py` | ~100 |
| Response Models | `src/jeeves/api/models/responses.py` | ~180 |
| Common Models | `src/jeeves/api/models/common.py` | ~30 |
| Dependencies | `src/jeeves/api/deps.py` | ~25 |
| System Router | `src/jeeves/api/routers/system.py` | ~200 |
| Briefing Router | `src/jeeves/api/routers/briefing.py` | ~140 |
| Briefing Service | `src/jeeves/api/services/briefing_service.py` | ~80 |
| Tests | `tests/unit/test_api_*.py` | 20 tests |

#### Endpoints Disponibles

| Endpoint | Description |
|----------|-------------|
| `GET /` | API info |
| `GET /api/health` | Health check avec status composants |
| `GET /api/stats` | Statistiques de traitement |
| `GET /api/config` | Configuration (secrets masqués) |
| `GET /api/briefing/morning` | Briefing du matin |
| `GET /api/briefing/meeting/{id}` | Briefing pré-réunion |

**Commande** : `scapin serve [--host] [--port] [--reload]`
**Documentation** : `http://localhost:8000/docs` (OpenAPI/Swagger)

#### Extensions Complétées ✅

| Extension | Statut | Phase |
|-----------|--------|-------|
| Routers Queue, Email, Calendar, Teams | ✅ | 0.7.1 |
| Router Journal | ✅ | 1.6 |
| Authentification JWT | ✅ | 0.8 |
| WebSockets temps réel | ✅ | 0.8 |

### Phase 0.8 : Interface Web (SvelteKit) ✅

**Dépendance** : Phase 0.7
**Durée** : 3-4 janvier 2026
**Statut** : ✅ COMPLÉTÉ

📖 **Plan détaillé** : [`docs/plans/phase-0.8-web/`](docs/plans/phase-0.8-web/00-index.md)

**Livrables** :
- [x] SvelteKit + TailwindCSS v4 + Svelte 5 runes
- [x] Design system Liquid Glass (Apple WWDC 2025)
- [x] 7 pages : Briefing, Flux, Notes, Discussions, Journal, Stats, Settings
- [x] Authentification JWT avec PIN mobile
- [x] WebSockets temps réel pour événements
- [x] Gestes mobiles : pull-to-refresh, swipe cards
- [x] Recherche globale Cmd+K

Le plan complet est découpé en 10 documents :
- `00-index.md` — Vue d'ensemble et navigation
- `01-vision.md` — Concept event-centric et principes UX
- `02-architecture.md` — Stack technique (SvelteKit, TailwindCSS)
- `03-design-system.md` — Couleurs, typographie, composants
- `04-mockups-core.md` — Briefing, Flux, Notes PKM, Discussions
- `05-mockups-analytics.md` — Statistiques, Rapports, Settings
- `06-ux-avancee.md` — 17 améliorations UX (Cmd+K, Focus, etc.)
- `07-api-endpoints.md` — ~50 nouveaux endpoints API
- `08-implementation.md` — 20 étapes d'implémentation
- `09-criteres-succes.md` — Checklist de validation

Vues principales :
- `/` — Briefing du matin avec résumé IA
- `/flux` — Flux unifié d'événements (A traiter, Traités, Historique)
- `/notes` — CRUD complet notes PKM avec liens bidirectionnels
- `/discussions` — Multi-sessions chat comme Claude Desktop
- `/stats` — Dashboard KPIs et consommation tokens
- `/rapports` — Journaliers, hebdomadaires, mensuels
- `/settings` — Configuration comptes et seuils IA

### Phase 0.9 : PWA Mobile ✅

**Dépendance** : Phase 0.8
**Durée** : 4 janvier 2026
**Statut** : ✅ COMPLÉTÉ

**Livrables** :
- [x] Service Worker v0.9.0 avec caching intelligent (network-first API, cache-first static)
- [x] Push Notifications via Service Worker avec urgence
- [x] Icônes PNG générées (192, 512, apple-touch-icon, favicons)
- [x] Manifest avec shortcuts, share_target, protocol_handlers
- [x] Deeplinks via `web+scapin://` protocol
- [x] Share Target pour recevoir du contenu partagé
- [x] Background sync support

---

## 📅 Calendrier Révisé

### Q1 2026 (Janvier - Mars)

| Mois | Phase | Focus |
|------|-------|-------|
| **Janvier** | 0.6 | Refactoring + Validation E2E |
| **Janvier-Février** | 1.0 | Trivelin Email (MVP) |
| **Février-Mars** | 1.1 | Journaling Email (feedback basique) |

**Livrable Q1** : Email Excellence — Inbox Zero assisté fonctionnel

### Q2 2026 (Avril - Juin)

| Mois | Phase | Focus |
|------|-------|-------|
| **Avril** | 1.2 | Intégration Teams |
| **Avril-Mai** | 1.3 | Intégration Calendrier |
| **Mai** | 1.4 | LinkedIn (optionnel, basse priorité) |
| **Mai-Juin** | 1.5 | Système de Briefing |

**Livrable Q2** : Multi-Source + Briefings — Préparation réunions automatique

### Q3 2026 (Juillet - Septembre)

| Mois | Phase | Focus |
|------|-------|-------|
| **Juillet** | 1.6 | Journaling Complet |
| **Juillet-Août** | 0.7 | API Jeeves |
| **Août-Septembre** | 0.8 | Interface Web |

**Livrable Q3** : Boucle complète + Interface Web

### Q4 2026 (Octobre - Décembre)

| Mois | Phase | Focus |
|------|-------|-------|
| **Octobre** | 0.9 | PWA Mobile |
| **Novembre** | 2.5 | IA Multi-Provider |
| **Décembre** | — | Polish + Beta |

**Livrable Q4** : Mobile + Consensus IA + Beta Release

---

## 📈 Progression Globale

### Vue d'Ensemble Phases (Réorganisée)

```
=== INFRASTRUCTURE (Complète) ===
Phase 0:   ████████████████████ 100% ✅ Fondations
Phase 1:   ████████████████████ 100% ✅ Traitement Email
Phase 1.5: ████████████████████ 100% ✅ Événements & Display
Phase 1.6: ████████████████████ 100% ✅ Monitoring Santé
Phase 1.7: ████████████████████ 100% ✅ Sélecteur Modèle IA
Phase 0.5: ████████████████████ 100% ✅ Architecture Cognitive
Phase 2:   ████████████████░░░░  80% 🚧 Menu Interactif

=== VALEUR FONCTIONNELLE (Complète) ===
Phase 0.6: ████████████████████ 100% ✅ Refactoring Valet
Phase 1.0: ████████████████████ 100% ✅ Trivelin Email (Pipeline Cognitif)
Phase 1.1: ████████████████████ 100% ✅ Journaling & Feedback Loop
Phase 1.2: ████████████████████ 100% ✅ Intégration Teams
Phase 1.3: ████████████████████ 100% ✅ Intégration Calendrier
Phase 1.4: ████████████████████ 100% ✅ Système de Briefing

=== INTERFACES ===
Phase 0.7: ████████████████████ 100% ✅ API Jeeves MVP
Phase 0.8: ████████████████████ 100% ✅ UI Web (SvelteKit)
Phase 0.9: ████████████████████ 100% ✅ PWA Mobile

=== AVANCÉ ===
Phase 1.6: ████████████████████ 100% ✅ Journaling Complet Multi-Source
Phase 1.5: ░░░░░░░░░░░░░░░░░░░░   0% 📋 LinkedIn (basse priorité)
Phase 2.5: ░░░░░░░░░░░░░░░░░░░░   0% 📋 IA Multi-Provider
Phase 3:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Connaissances Avancées
Phase 4:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Révision FSRS

Infrastructure:    ████████████████████ 100% ✅
Valeur Fonct.:     ████████████████████ 100% ✅
Interfaces:        ████████████████████ 100% ✅
Avancé:            █████░░░░░░░░░░░░░░░  25% 🏗️
Global:            █████████████████░░░  85% 🚀
```

### Évolution Couverture Tests

| Phase | Tests | Couverture | Pass Rate | Statut |
|-------|-------|------------|-----------|--------|
| Phase 0 | 115 | 95%+ | 100% | ✅ |
| Phase 1 | 62 | 90%+ | 100% | ✅ |
| Phase 1.5 | 44 | 100% | 100% | ✅ |
| Phase 1.6 | 31 | 100% | 100% | ✅ |
| Phase 1.7 | 25 | 100% | 100% | ✅ |
| Phase 2 | 108 | 85%+ | 100% | 🚧 |
| Phase 0.5 | 200+ | 95%+ | 100% | ✅ |
| Phase 1.0 | 15 | 100% | 100% | ✅ |
| Phase 1.1 | 56 | 100% | 100% | ✅ |
| **Phase 1.2** | **116** | **100%** | **100%** | **✅** |
| **Phase 1.3** | **92** | **100%** | **100%** | **✅** |
| **Phase 1.4** | **58** | **100%** | **100%** | **✅** |
| **Phase 0.7** | **20** | **100%** | **100%** | **✅** |
| **Phase 1.6** | **38** | **100%** | **100%** | **✅** |
| **Total** | **1414+** | **95%** | **100%** | **✅** |

---

## 🎯 Métriques de Succès

### Complétées (Phases 0-2) ✅

- ✅ Qualité code 10/10
- ✅ 867 tests, 95% couverture, 100% pass rate
- ✅ Zéro bug critique
- ✅ Traitement email production-ready
- ✅ UX événementielle élégante
- ✅ Menu interactif fonctionnel
- ✅ Support multi-comptes opérationnel
- ✅ Système file révision fonctionnel
- ✅ Monitoring santé complet
- ✅ Sélection modèle IA intelligente

### Cibles Phase 0.5 (Architecture Cognitive)

- Temps raisonnement : 10-20s moyenne
- Convergence confiance : >90% des cas
- Amélioration précision : +15% vs actuel
- Zéro boucle infinie
- 100+ tests unitaires, 90%+ couverture

### Cibles Phases 0.7-0.9 (Couches UI)

- Temps réponse API : < 100ms
- Chargement page Web UI : < 2s
- Score Lighthouse PWA : > 90
- Taux installation mobile : > 50% utilisateurs web
- Satisfaction utilisateur : "mieux que CLI"

### Long Terme (Toutes Phases)

- Graphe connaissances : 1000+ notes
- Rétention répétition espacée : 90%+
- Zéro perte données
- Performance recherche sub-seconde

---

## 🚀 Priorités Développement

### Q1 2026 (Janvier - Mars)

**Focus** : Valeur fonctionnelle immédiate — **COMPLÉTÉ**

1. ✅ **Phase 0.5** (Architecture Cognitive) — FAIT
2. ✅ **Phase 0.6** (Refactoring Valet) — FAIT
3. ✅ **Phase 1.0** (Trivelin Email - Pipeline Cognitif) — FAIT
4. ✅ **Phase 1.1** (Journaling & Feedback Loop) — FAIT
5. ✅ **Phase 1.2** (Intégration Teams) — FAIT
6. ✅ **Phase 1.3** (Intégration Calendrier) — FAIT
7. ✅ **Phase 1.4** (Système de Briefing) — FAIT
8. ✅ **Phase 0.7** (API Jeeves MVP) — FAIT

### Q2 2026 (Avril - Juin)

**Focus** : Interfaces utilisateur

1. ✅ **Phase 0.8** (UI Web SvelteKit) — COMPLÉTÉ
2. ✅ **Phase 0.9** (PWA Mobile) — COMPLÉTÉ

### Q3 2026 (Juillet - Septembre)

**Focus** : Améliorations et consensus IA

1. ✅ **Phase 1.6** (Journaling Complet multi-source) — FAIT (avancé de Q3 à Q1)
2. **Phase 2.5** (IA Multi-Provider)
3. **Phase 1.5** (LinkedIn - basse priorité)

### Q4 2026 (Octobre - Décembre)

**Focus** : Optimisation et release

1. **Phase 3** (Connaissances Avancées)
2. **Phase 4** (Révision FSRS)
3. **Polish & Optimisation Performance**
4. **Release Beta**

---

## 📝 Principes Développement

### Qualité Code

1. **Utilisateur d'abord** : UX élégante non-négociable
2. **Qualité sur vitesse** : Qualité code 10/10 maintenue
3. **Tout tester** : Cible 90%+ couverture
4. **Événementiel** : Découpler backend du frontend
5. **Amélioration progressive** : Chaque phase construit sur précédente

### Principes Architecturaux

1. **Thème Valet** : Tous modules suivent métaphore assistant serviable
2. **Séparation Responsabilités** : Frontières modules claires
3. **API-First** : API Jeeves active toutes interfaces
4. **Cœur Cognitif** : Phase 0.5 est fondation intelligence
5. **Multi-Interface** : CLI + Web + Mobile (pas CLI seul)

### Stack Technique

- **Backend** : Python 3.11+, FastAPI, Pydantic
- **Frontend** : SvelteKit, TailwindCSS, TypeScript
- **IA** : Claude (Anthropic), GPT-4o (OpenAI), Mistral, Gemini
- **Stockage** : SQLite, Markdown+Git, FAISS
- **Tests** : pytest, 90%+ couverture
- **Déploiement** : Docker, cloud-ready

---

## 💡 Backlog / Idées Futures

### Interface Queue (Flux)

| Idée | Description | Priorité |
|------|-------------|----------|
| **Bouton "Réanalyser"** | Ajouter un bouton pour relancer l'analyse IA sur un item de queue | Moyenne |
| **Liens vers notes liées** | Afficher les notes PKM liées à l'expéditeur/sujet en Level 3 | Basse |

### Améliorations IA

| Idée | Description | Priorité |
|------|-------------|----------|
| **Multi-provider consensus** | Utiliser plusieurs providers IA et voter | Basse |
| **Apprentissage des corrections** | Ajuster les seuils basé sur les corrections utilisateur | Moyenne |

### Intégrations

| Idée | Description | Priorité |
|------|-------------|----------|
| **LinkedIn** | Importer et traiter les messages LinkedIn | Basse |
| **Apple Notes sync** | Synchronisation bidirectionnelle avec Apple Notes | Moyenne |

---

## 🔗 Ressources

- **Dépôt GitHub** : https://github.com/johanlb/scapin
- **Dépôt Précédent** : https://github.com/johanlb/pkm-system (archivé)
- **Documentation** : 
  - `DESIGN_PHILOSOPHY.md` — Principes fondateurs
  - `ARCHITECTURE.md` — Spécifications techniques
  - `README.md` — Vue d'ensemble
  - `MIGRATION.md` — Guide migration

---

## 📊 Historique Versions

- **v1.0.0-alpha.6** (2026-01-03) : Refactoring PKM → Scapin
  - ✅ Renommage classes : PKMLogger → ScapinLogger, PKMConfig → ScapinConfig, PKMError → ScapinError
  - ✅ Mise à jour tous les imports et références
  - ✅ Mise à jour chemins de dossiers (_PKM → _Scapin)
  - ✅ 1350+ tests, 95% couverture, 100% pass rate
  - ✅ Ruff 0 warnings

- **v1.0.0-alpha.5** (2026-01-03) : Phases 1.2, 1.3, 1.4, 0.7 complétées
  - ✅ Phase 1.2 : Intégration Microsoft Teams (116 tests)
  - ✅ Phase 1.3 : Intégration Calendrier Microsoft (92 tests)
  - ✅ Phase 1.4 : Système de Briefing (58 tests)
  - ✅ Phase 0.7 : API Jeeves MVP (20 tests)
  - ✅ 1350+ tests, 95% couverture, 100% pass rate

- **v1.0.0-alpha.4** (2026-01-02) : Phase 1.0 complétée
  - ✅ `CognitivePipeline` orchestrant tous les valets
  - ✅ `ProcessingConfig` avec activation opt-in
  - ✅ `ActionFactory` pour conversion EmailAnalysis → Actions
  - ✅ Intégration dans `processor.py` avec fallback
  - ✅ 978 tests, 95% couverture, 100% pass rate

- **v1.0.0-alpha.3** (2026-01-02) : Phase 0.6 complétée
  - ✅ Migré `src/ai/` → `src/sancho/` (router, model_selector, templates, providers)
  - ✅ Migré `src/cli/` → `src/jeeves/` (cli, display_manager, menu, review_mode)
  - ✅ Migré `email_processor.py` → `src/trivelin/processor.py`
  - ✅ 7 valets tous implémentés et peuplés
  - ✅ 967 tests, 95% couverture, 100% pass rate

- **v1.0.0-alpha.2** (2026-01-02) : Documentation fondatrice
  - ✅ Créé DESIGN_PHILOSOPHY.md
  - ✅ Mis à jour README.md, CLAUDE.md, ROADMAP.md
  - ✅ Créé fiche Apple Notes "Scapin — Principes de Conception"
  - ✅ 867 tests, 95% couverture, 100% pass rate

- **v1.0.0-alpha** (2025-12-31) : Migration dépôt PKM vers Scapin
  - Renommé de "PKM System" en "Scapin"
  - Établi vision architecture valet
  - Planifié phases UI (Web + PWA)
  - Migré 88 fichiers et 6 issues ouvertes

---

**Statut** : Phase 1.6 Journaling Complet ✅ — Multi-source terminé
**Qualité** : 10/10 Production Ready Core 🚀
**Tests** : 1414+ tests, 95% couverture, 100% pass ✅
**Prochaine Étape** : Phases avancées (IA Multi-Provider, LinkedIn)
