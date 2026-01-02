# Scapin — Feuille de Route Produit

**Dernière mise à jour** : 2 janvier 2026  
**Version** : 1.0.0-alpha (suite de PKM v3.1.0)  
**Phase actuelle** : Phase 0.5 Semaine 1 ✅ → Semaine 2 en cours

---

## 📊 Résumé Exécutif

### Statut Global

**État** : ✅ **Fondation Cognitive Prête** — Construction du moteur de raisonnement

| Métrique | Valeur |
|----------|--------|
| **Tests** | 867 tests, 95% couverture, 100% pass rate |
| **Qualité Code** | 10/10 (50 warnings non-critiques) |
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

### Dernière Étape (2 janvier 2026)

- ✅ Phase 0.5 Semaine 1 complète — Modules fondation cognitifs production-ready
- ✅ Suite de tests corrigée — Tous les tests critiques passent (867/867)
- ✅ Qualité code modernisée — Annotations types, imports, linting
- ✅ **DESIGN_PHILOSOPHY.md créé** — Document fondateur capturant les principes
- ✅ Documentation mise à jour — README.md, CLAUDE.md, fiche Apple Notes

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

## 🏗️ Phase Actuelle

### Phase 0.5 : Fondation Architecture Cognitive

**Statut** : 🏗️ Semaine 1 ✅, Semaines 2-5 en cours  
**Durée** : 5 semaines total  
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

#### Semaine 2 : Sancho — Moteur de Raisonnement 🚧

**Durée cible** : 5-7 jours  
**Statut** : 📋 Planifié — Prêt à démarrer

**Livrables** :
- [ ] `src/ai/router.py` — Routage IA avec circuit breaker + rate limiting (500-800 lignes)
- [ ] `src/ai/model_selector.py` — Sélection modèle multi-provider (300-400 lignes)
- [ ] `src/ai/templates.py` — Gestion templates Jinja2 (200-300 lignes)
- [ ] `src/sancho/reasoning_engine.py` — Raisonnement itératif 5 passes (600-800 lignes)
- [ ] Intégration avec EmailProcessor (feature flag pour rollback)
- [ ] Templates pour chaque passe (pass1-5.j2)
- [ ] Tests : 100+ nouveaux tests, cible 100% pass rate

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

#### Semaine 3 : Passepartout — Base de Connaissances & Contexte

**Livrables** :
- [ ] `src/passepartout/embeddings.py` — Embeddings sentence-transformers
- [ ] `src/passepartout/vector_store.py` — Recherche sémantique FAISS
- [ ] `src/passepartout/note_manager.py` — Notes Markdown + Git
- [ ] `src/passepartout/context_engine.py` — Récupération contexte pour Passe 2

**Alignement Philosophique** : Implémente la "mémoire transactive" de Wegner — Johan sait que Passepartout "sait".

#### Semaine 4 : Planchet + Figaro — Planification & Exécution

**Livrables** :
- [ ] `src/planchet/planning_engine.py` — Planification avec évaluation risques
- [ ] `src/figaro/actions/base.py` — Classe de base Action
- [ ] `src/figaro/actions/email.py` — Actions email (archive, delete, reply)
- [ ] `src/figaro/actions/tasks.py` — Création tâches
- [ ] `src/figaro/actions/notes.py` — Création/mise à jour notes
- [ ] `src/figaro/orchestrator.py` — Exécution DAG avec rollback

**Modes d'exécution** (de DESIGN_PHILOSOPHY.md) :
- **Auto** : Confiance haute + risque faible → Exécute, informe après
- **Review** : Confiance moyenne OU risque moyen → Prépare, attend validation
- **Manual** : Confiance basse OU risque haut → Présente options, Johan décide

#### Semaine 5 : Sganarelle — Apprentissage & Intégration

**Livrables** :
- [ ] `src/sganarelle/learning_engine.py` — Apprentissage continu depuis feedback
- [ ] `src/sganarelle/feedback_processor.py` — Analyse feedback
- [ ] `src/sganarelle/confidence_calibrator.py` — Calibration confiance
- [ ] `src/sganarelle/pattern_store.py` — Détection patterns
- [ ] Intégration bout-en-bout
- [ ] Validation POC

**Alignement Philosophique** : Implémente la "boucle d'amélioration continue" — journaling → enrichissement fiches → meilleures analyses → feedback.

---

## 📅 Phases Futures

### Phase 0.6 : Refactoring Modules Valet

**Statut** : 📋 Planifié  
**Durée** : 2-3 semaines  
**Priorité** : 🟡 MOYENNE

**Objectif** : Restructurer les modules pour correspondre à l'architecture valet thématique.

| Chemin Actuel | Nouveau Chemin | Valet | Responsabilité |
|---------------|----------------|-------|----------------|
| `src/ai/` | `src/sancho/` | Sancho Panza | Sagesse & Raisonnement |
| `src/core/email_processor.py` | `src/trivelin/processor.py` | Trivelin | Triage & Classification |
| `src/core/multi_account_processor.py` | `src/figaro/orchestrator.py` | Figaro | Orchestration |
| `src/cli/` | `src/jeeves/` | Jeeves | Service & Couche API |
| Nouveau | `src/planchet/` | Planchet | Planification |
| Nouveau | `src/sganarelle/` | Sganarelle | Apprentissage |
| Nouveau | `src/passepartout/` | Passepartout | Navigation & Recherche |

**Note** : `src/core/` reste pour l'infrastructure partagée (events, config, state).

**Critères de Succès** :
- ✅ Tous modules suivent thème valet
- ✅ Séparation des responsabilités claire
- ✅ Zéro changement cassant pour utilisateurs
- ✅ Tous tests passent
- ✅ Documentation mise à jour

---

### Phase 0.7 : Couche API Jeeves

**Statut** : 📋 Planifié  
**Durée** : 3-4 semaines  
**Priorité** : 🟡 MOYENNE

**Objectif** : Construire API REST FastAPI pour interfaces web et mobile.

**Livrables** :
- [ ] **Application FastAPI** (`src/jeeves/api/`)
  - Design API RESTful
  - Documentation OpenAPI/Swagger
  - Authentification JWT
  - Support CORS pour clients web

- [ ] **Endpoints Principaux**
  - `POST /api/process/email` — Traiter emails
  - `GET /api/queue` — Obtenir file révision
  - `POST /api/queue/{id}/approve` — Approuver item en file
  - `POST /api/queue/{id}/modify` — Modifier et exécuter
  - `GET /api/health` — Santé système
  - `GET /api/stats` — Statistiques traitement
  - `POST /api/reasoning/query` — Poser questions
  - `GET /api/notes` — Lister notes PKM
  - `GET /api/notes/{id}` — Obtenir note spécifique

- [ ] **Support WebSocket**
  - Événements traitement temps réel
  - Mises à jour live pendant traitement email
  - Système notification

**Stack Technologique** :
- FastAPI (framework web Python async)
- Pydantic (validation requête/réponse)
- uvicorn (serveur ASGI)
- WebSockets (mises à jour temps réel)

**Critères de Succès** :
- ✅ Toutes opérations CRUD disponibles via API
- ✅ Mises à jour temps réel via WebSocket
- ✅ < 100ms temps réponse API (endpoints non-traitement)
- ✅ Documentation API complète
- ✅ 90%+ couverture tests

---

### Phase 0.8 : Interface Web

**Statut** : 📋 Planifié  
**Durée** : 6-8 semaines  
**Priorité** : 🔴 HAUTE

**Objectif** : Construire application web moderne pour usage quotidien Scapin.

**Livrables** :
- [ ] **Application Frontend** (SvelteKit)
  - UI moderne et responsive
  - Mises à jour temps réel
  - Interface traitement email
  - Gestion file révision
  - Navigateur notes PKM
  - Dashboard statistiques
  - Gestion paramètres

- [ ] **Vues Principales**
  - `/dashboard` — Vue d'ensemble avec stats
  - `/process` — Interface traitement email
  - `/queue` — File révision avec approuver/modifier/rejeter
  - `/notes` — Navigateur base de connaissances
  - `/search` — Interface recherche sémantique
  - `/settings` — Configuration comptes et IA
  - `/health` — Monitoring santé système

- [ ] **Fonctionnalités Temps Réel**
  - Statut traitement live
  - Mises à jour WebSocket
  - Barres progression et notifications
  - Visualisations confiance

- [ ] **Raisonnement Interactif**
  - Voir trace raisonnement (les 5 passes)
  - Comprendre décisions IA
  - Fournir feedback
  - Modifier et relancer

**Stack Technologique** :
- **Frontend** : SvelteKit (moderne, rapide, simple)
- **Style** : TailwindCSS (CSS utility-first)
- **Graphiques** : Chart.js ou D3.js
- **Icônes** : Lucide ou Heroicons
- **État** : Svelte stores + client API
- **Build** : Vite (serveur dev rapide)

**Principes Design** :
- **Propre & Minimal** : Focus sur contenu, pas chrome
- **Rapide** : < 2s chargement page, interactions instantanées
- **Accessible** : WCAG 2.1 AA conforme
- **Responsive** : Design mobile-first

---

### Phase 0.9 : PWA Mobile

**Statut** : 📋 Planifié  
**Durée** : 3-4 semaines  
**Priorité** : 🟡 MOYENNE

**Objectif** : Convertir UI web en Progressive Web App pour usage mobile.

**Livrables** :
- [ ] **Infrastructure PWA**
  - Service Worker pour support offline
  - Manifest app (icônes, couleurs, nom)
  - Prompts installation
  - Notifications push
  - Sync background

- [ ] **Optimisations Mobile**
  - UI touch-friendly
  - Patterns navigation mobile
  - Gestion file offline
  - Actions rapides (traiter, réviser)
  - Intégration partage natif

**Critères de Succès** :
- ✅ Fonctionne offline (lecture seule)
- ✅ Installation comme app sur iOS/Android
- ✅ Notifications push fonctionnelles
- ✅ < 3s chargement sur 3G
- ✅ Score Lighthouse PWA > 90

---

### Phase 2.5 : Système IA Multi-Provider

**Statut** : 📋 Planifié  
**Durée** : 4-5 semaines  
**Priorité** : 🔴 HAUTE

**Objectif** : Supporter plusieurs providers IA avec mécanisme consensus intelligent.

**Livrables** :
- [ ] **Couche Abstraction Provider**
  - `ClaudeProvider` (existant) ✅
  - `OpenAIProvider` (GPT-4o, GPT-4-turbo)
  - `MistralProvider` (Mistral Large/Medium/Small)
  - `GeminiProvider` (Gemini 2.0 Flash, Gemini 1.5 Pro)

- [ ] **Moteur Consensus**
  - Déclenchement quand confiance < 75%
  - Interrogation 2-3 providers
  - Agrégation réponses
  - Consensus pondéré basé sur précision provider

- [ ] **Routage Intelligent**
  - Utiliser provider le moins cher pour tâches simples
  - Consensus pour décisions incertaines
  - Failover automatique
  - Suivi et optimisation coûts

**Bénéfices** :
- **Résilience** : Pas de point unique de défaillance
- **Précision** : Consensus réduit erreurs de 10%+
- **Optimisation Coûts** : Choisir le moins cher pour la tâche
- **Pérennité** : Facile d'ajouter nouveaux providers

---

### Phase 3 : Système de Connaissances

**Statut** : 📋 Planifié  
**Durée** : 4-6 semaines  
**Priorité** : 🟡 MOYENNE

**Objectif** : Construire système gestion connaissances avec notes Markdown, versioning Git, et extraction entités.

**Livrables** :
- [ ] **NoteManager** (`src/passepartout/note_manager.py`)
  - CRUD notes
  - Support frontmatter YAML
  - Auto-linking entre notes
  - Gestion tags
  - Fonctionnalité recherche

- [ ] **Intégration Git**
  - Auto-commit sur changements notes
  - Suivi historique versions
  - Résolution conflits
  - Gestion branches

- [ ] **Moteur Contexte** (`src/passepartout/context_engine.py`)
  - Récupération notes récentes pour contexte IA
  - Suggestions contexte pertinent
  - Recherche intelligente avec embeddings (FAISS)
  - Gestion fenêtre contexte

- [ ] **Extraction Entités**
  - Reconnaissance entités nommées (personnes, organisations, projets)
  - Tagging automatique
  - Liaison entités aux notes
  - Suivi relations

---

### Phase 4 : Système Révision FSRS

**Statut** : 📋 Planifié  
**Durée** : 3-4 semaines  
**Priorité** : 🟢 BASSE

**Objectif** : Implémenter système répétition espacée pour révision connaissances utilisant algorithme FSRS.

**Alignement Philosophique** : Adresse le risque "érosion mémoire biologique" identifié dans DESIGN_PHILOSOPHY.md — révision espacée pour les connaissances critiques (visages, principes, relations clés).

---

### Phase 5 : Graphe de Propriétés

**Statut** : 📋 Planifié  
**Durée** : 3-4 semaines  
**Priorité** : 🟢 BASSE

**Objectif** : Construire graphe de propriétés pour relations connaissances utilisant NetworkX.

---

### Phase 6 : Intégrations

**Statut** : 🔶 Partiel (30% — OmniFocus uniquement)  
**Durée** : 4-5 semaines restantes  
**Priorité** : 🟢 BASSE

**Complété** ✅ :
- [x] **Intégration OmniFocus MCP** (30%)
  - Outils MCP disponibles
  - Création tâches depuis emails
  - Organisation projet basique

**Restant** :
- [ ] OmniFocus complet (70%)
- [ ] Sync Apple Contacts
- [ ] Intégration Apple Calendar

---

### Phase 7 : Sync Bidirectionnelle

**Statut** : 📋 Planifié  
**Durée** : 5-6 semaines  
**Priorité** : 🟢 BASSE

**Objectif** : Activer sync bidirectionnelle entre notes Markdown et Apple Notes.

---

## 📈 Progression Globale

### Vue d'Ensemble Phases

```
Phase 0:   ████████████████████ 100% ✅ Fondations
Phase 1:   ████████████████████ 100% ✅ Traitement Email
Phase 1.5: ████████████████████ 100% ✅ Événements & Display
Phase 1.6: ████████████████████ 100% ✅ Monitoring Santé
Phase 1.7: ████████████████████ 100% ✅ Sélecteur Modèle IA
Phase 2:   ████████████████░░░░  80% 🚧 Menu Interactif
Phase 0.5: ████░░░░░░░░░░░░░░░░  20% 🏗️ Architecture Cognitive (CRITIQUE)
Phase 0.6: ░░░░░░░░░░░░░░░░░░░░   0% 📋 Refactoring Valet
Phase 0.7: ░░░░░░░░░░░░░░░░░░░░   0% 📋 API Jeeves
Phase 0.8: ░░░░░░░░░░░░░░░░░░░░   0% 📋 UI Web
Phase 0.9: ░░░░░░░░░░░░░░░░░░░░   0% 📋 PWA Mobile
Phase 2.5: ░░░░░░░░░░░░░░░░░░░░   0% 📋 IA Multi-Provider
Phase 3:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Système Connaissances
Phase 4:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Révision FSRS
Phase 5:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Graphe Propriétés
Phase 6:   ██████░░░░░░░░░░░░░░  30% 📋 Intégrations
Phase 7:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Sync Bidirectionnelle

Global:    ██████████████░░░░░░  70% 🚀
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
| Phase 0.5 | 92+ | 95%+ | 100% | 🏗️ |
| **Total** | **867** | **95%** | **100%** | **✅** |

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

### Q1 2026 (3 Prochains Mois)

1. **Compléter Phase 2** (Menu Interactif) — 2-3 semaines
2. **Phase 0.5** (Architecture Cognitive) — 4-5 semaines ⭐ CRITIQUE
3. **Phase 0.6** (Refactoring Valet) — 2-3 semaines
4. **Début Phase 0.7** (API Jeeves) — Si temps permet

### Q2 2026

1. **Compléter Phase 0.7** (API Jeeves)
2. **Phase 0.8** (UI Web) — 6-8 semaines
3. **Phase 0.9** (PWA Mobile) — 3-4 semaines
4. **Phase 2.5** (IA Multi-Provider)
5. **Début Phase 3** (Système Connaissances)

### Q3 2026

1. **Compléter Phase 3** (Système Connaissances)
2. **Phase 4** (Révision FSRS)
3. **Phase 5** (Graphe Propriétés)
4. **Phase 6** (Compléter Intégrations)

### Q4 2026

1. **Phase 7** (Sync Bidirectionnelle)
2. **Polish & Optimisation Performance**
3. **Release Beta Publique**

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

- **v1.0.0-alpha** (2025-12-31) : Migration dépôt PKM vers Scapin
  - Renommé de "PKM System" en "Scapin"
  - Établi vision architecture valet
  - Planifié phases UI (Web + PWA)
  - Migré 88 fichiers et 6 issues ouvertes

- **v1.0.0-alpha.2** (2026-01-02) : Documentation fondatrice
  - ✅ Créé DESIGN_PHILOSOPHY.md
  - ✅ Mis à jour README.md, CLAUDE.md, ROADMAP.md
  - ✅ Créé fiche Apple Notes "Scapin — Principes de Conception"
  - ✅ 867 tests, 95% couverture, 100% pass rate

---

**Statut** : Phase 0.5 Semaine 1 ✅ → Semaine 2 🚧  
**Qualité** : 10/10 Production Ready Core 🚀  
**Tests** : 867 tests, 95% couverture, 100% pass ✅  
**Prochaine Étape** : Semaine 2 — Moteur de raisonnement Sancho
