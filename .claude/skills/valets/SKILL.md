---
name: valets
description: Architecture cognitive de Scapin - Les 7 valets et leurs responsabilités. Utiliser pour comprendre les modules, leurs interactions, et où implémenter une fonctionnalité.
allowed-tools: Read, Grep, Glob
---

# Les Valets de Scapin

Architecture cognitive inspirée des valets de la comédie classique française.

## Vue d'ensemble

| Valet | Module | Responsabilité | Origine |
|-------|--------|----------------|---------|
| **Trivelin** | `src/trivelin/` | Perception & triage (Multi-Pass v2.2) | Marivaux |
| **Sancho** | `src/sancho/` | Raisonnement itératif & convergence | Cervantes |
| **Passepartout** | `src/passepartout/` | Base de connaissances (MD + FAISS + Git) | Verne |
| **Planchet** | `src/planchet/` | Planification & évaluation risques | Dumas |
| **Figaro** | `src/figaro/` | Orchestration DAG avec rollback | Beaumarchais |
| **Sganarelle** | `src/sganarelle/` | Apprentissage continu du feedback | Molière |
| **Frontin** | `src/frontin/` | Interface API & CLI | Molière |

## Flux de traitement

```
1. TRIVELIN reçoit et trie l'événement
        ↓
2. SANCHO raisonne (jusqu'à 5 passes)
        ↓ ← consulte → PASSEPARTOUT (base de connaissances)
        ↓
3. PLANCHET conçoit un plan d'action
        ↓
4. FIGARO orchestre l'exécution
        ↓
5. SGANARELLE apprend du résultat → enrichit PASSEPARTOUT
        ↑
6. FRONTIN fournit l'API pour web/mobile
```

## Détails par Valet

### Trivelin - Perception (`src/trivelin/`)
- **Rôle** : Premier contact avec les événements entrants
- **Fichiers clés** :
  - `v2_processor.py` : Orchestrateur du pipeline v2.2
  - `event_classifier.py` : Classification des événements
- **Capacités** : Multi-Pass v2.2, escalade Haiku → Sonnet → Opus

### Sancho - Raisonnement (`src/sancho/`)
- **Rôle** : Moteur de raisonnement IA
- **Fichiers clés** :
  - `multi_pass_analyzer.py` : Logique de convergence et d'escalade
  - `convergence.py` : Critères de convergence
  - `context_searcher.py` : Recherche de contexte
- **Capacités** : Jusqu'à 5 passes, context influence, thinking bubbles

### Passepartout - Mémoire (`src/passepartout/`)
- **Rôle** : Base de connaissances persistante
- **Fichiers clés** :
  - `note_manager.py` : Gestionnaire notes Markdown
  - `faiss_index.py` : Index vectoriel pour recherche sémantique
- **Capacités** : Sync Apple Notes, recherche hybride (full-text + sémantique)

### Planchet - Planification (`src/planchet/`)
- **Rôle** : Conception des plans d'action
- **Fichiers clés** :
  - `action_planner.py` : Génération de plans
  - `risk_evaluator.py` : Évaluation des risques
- **Capacités** : Plans atomiques, évaluation risques

### Figaro - Orchestration (`src/figaro/`)
- **Rôle** : Exécution coordonnée des actions
- **Fichiers clés** :
  - `dag_executor.py` : Exécution DAG
  - `rollback_manager.py` : Gestion des rollbacks
- **Capacités** : Transactions atomiques, rollback automatique

### Sganarelle - Apprentissage (`src/sganarelle/`)
- **Rôle** : Amélioration continue par feedback
- **Fichiers clés** :
  - `learning_engine.py` : Moteur d'apprentissage
  - `feedback_processor.py` : Traitement du feedback
- **Capacités** : Journaling, calibration IA

### Frontin - Interface (`src/frontin/`)
- **Rôle** : Interface API REST et CLI
- **Fichiers clés** :
  - `api/routers/` : Endpoints FastAPI
  - `api/services/` : Services métier
  - `cli.py` : Interface ligne de commande
- **Capacités** : REST API, WebSockets, CLI Typer

## Où implémenter ?

| Type de fonctionnalité | Valet cible |
|------------------------|-------------|
| Nouvelle source de données | Trivelin |
| Logique IA / prompts | Sancho |
| Stockage / recherche | Passepartout |
| Planification d'actions | Planchet |
| Exécution / intégrations | Figaro |
| Feedback / métriques | Sganarelle |
| API / UI | Frontin |
