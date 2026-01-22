# 6. Architecture

Comprendre le fonctionnement interne de Scapin vous aide à mieux l'utiliser et à diagnostiquer les problèmes.

---

## Les Valets

Scapin est composé d'une équipe de "valets" spécialisés, inspirés des serviteurs rusés de la comédie classique.

### Vue d'Ensemble

```
┌──────────────────────────────────────────────────────────────┐
│                        Entrée                                 │
│              (Email / Teams / Calendrier)                    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  TRIVELIN — Perception                                        │
│  • Reçoit les événements bruts                               │
│  • Normalise en format universel (PerceivedEvent)            │
│  • Triage initial (urgence, source)                          │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  SANCHO — Raisonnement                                        │
│  • Analyse IA multi-passes (5 passes max)                    │
│  • Extraction d'entités                                       │
│  • Génération de l'action proposée                           │
│  • Convergence par confiance                                  │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  PASSEPARTOUT — Connaissances                                 │
│  • Récupère le contexte des notes                            │
│  • Enrichit l'analyse avec l'historique                      │
│  • Gère les embeddings vectoriels (FAISS)                    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  PLANCHET — Planification                                     │
│  • Évalue les risques de chaque action                       │
│  • Propose des alternatives                                   │
│  • Gère les dépendances entre actions                        │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  FIGARO — Exécution                                           │
│  • Orchestre les actions (DAG)                               │
│  • Exécute les opérations IMAP/Graph                         │
│  • Gère les rollbacks en cas d'erreur                        │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  SGANARELLE — Apprentissage                                   │
│  • Collecte les feedbacks utilisateur                        │
│  • Calibre les seuils de confiance                           │
│  • Met à jour les patterns                                    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  FRONTIN — Interface                                          │
│  • API REST (FastAPI)                                         │
│  • Interface CLI                                              │
│  • WebSockets temps réel                                      │
└──────────────────────────────────────────────────────────────┘
```

---

## Raisonnement Multi-Passes (v2.2)

Sancho utilise une architecture multi-pass avec escalade intelligente :

### Pass 1 : Extraction Aveugle (Haiku)

- **Objectif** : Analyse SANS contexte pour éviter les biais.
- **Rôle** : Extraction brute des entités, propositions initiales.
- **Modèle** : Claude 3.5 Haiku (rapide et précis pour la syntaxe).

### Pass 2-3 : Raffinement Contextuel (Haiku)

- **Objectif** : Utiliser la connaissance du passé pour corriger le présent.
- **Rôle** : Scapin interroge **Passepartout** sur les entités trouvées.
- **Modèle** : Claude 3.5 Haiku.

### Pass de Cohérence (Validation Intégrée)

- **Rôle** : Vérifie que les nouvelles extractions ne créent pas de doublons et restent cohérentes avec les notes existantes.
- **Action** : Aligne les noms de projets, les relations et les formats.

### Pass 4 : Escalade Sonnet (Raisonnement Complexe)

- **Objectif** : Résoudre les ambiguïtés que Haiku ne peut pas trancher.
- **Rôle** : Utilisé si la confiance reste < 80% ou pour des emails denses.
- **Modèle** : Claude 3.5 Sonnet.

### Pass 5 : Escalade Opus (Expertise / Haute Importance)

- **Objectif** : Rigueur maximale pour les enjeux critiques.
- **Modèle** : Claude 3 Opus.

### Convergence

Le processus s'arrête quand :
- Confiance ≥ 95%
- Aucun changement entre deux passes
- Maximum 5 passes atteint

### Coût Optimisé

- 85% des emails : 1-2 passes Haiku (~$0.0028)
- 10% : 3 passes Haiku (~$0.0041)
- 4% : escalade Sonnet (~$0.017)
- 1% : escalade Opus (~$0.077)

---

## Architecture Four Valets (v3.0)

À partir de la version 3.0, Sancho utilise une architecture en 4 passes spécialisées, inspirée des valets de Dumas.

### Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         GRIMAUD                                  │
│                    Observation silencieuse                       │
│  • Extraction brute SANS contexte (évite les biais)             │
│  • Identifie entités, dates, montants, références               │
│  • Questions pour les passes suivantes                          │
│  • Génère les premières questions stratégiques                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          BAZIN                                   │
│                   Enrichissement contextuel                      │
│  • Consulte Passepartout (base de connaissances)                │
│  • Enrichit avec l'historique des personnes/projets             │
│  • Corrige les extractions avec le contexte                     │
│  • Identifie des questions stratégiques liées aux notes         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PLANCHET                                 │
│                    Critique et validation                        │
│  • Valide la cohérence des extractions                          │
│  • Critique les propositions de Bazin                           │
│  • Suggère des corrections si nécessaire                        │
│  • Soulève des questions sur les processus/organisation         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MOUSQUETON                                │
│                      Arbitrage final                             │
│  • Synthèse des passes précédentes                              │
│  • Décision finale (approve/archive/needs_human)                │
│  • Score de confiance consolidé                                  │
│  • Déduplique et compile les questions stratégiques             │
└─────────────────────────────────────────────────────────────────┘
```

### Caractéristiques

| Aspect | Description |
|--------|-------------|
| **Escalade** | Haiku → Sonnet → Opus selon complexité |
| **Early Stop** | Arrêt dès confiance ≥ 95% |
| **Context Influence** | Transparence sur l'impact du contexte |
| **Questions** | Accumulation multi-valets |

---

## Questions Stratégiques (v3.1)

Les Questions Stratégiques sont des questions qui émergent de l'analyse et nécessitent une réflexion humaine.

### Principe

Chaque valet peut identifier des questions qui ne concernent pas juste l'email analysé mais touchent à l'organisation, aux processus ou à la structure PKM :

| Valet | Type de questions |
|-------|-------------------|
| **Grimaud** | Questions factuelles, données manquantes |
| **Bazin** | Questions liées aux notes et à l'historique |
| **Planchet** | Questions sur les processus et la cohérence |
| **Mousqueton** | Synthèse et questions stratégiques globales |

### Catégories

```
organisation   → Comment structurer les relations, projets
processus      → Comment améliorer les workflows
structure_pkm  → Comment organiser les notes
decision       → Choix nécessitant réflexion
```

### Intégration

Les questions sont :
1. **Accumulées** par tous les valets
2. **Dédupliquées** par Mousqueton
3. **Liées** à une note thématique quand pertinent
4. **Visibles** dans la vue élément unique

### Exemple

Un email annonçant 9229 "Smart Matches" génère :
> ❓ *"Quelle stratégie pour traiter ces 9229 Smart Matches ?"*
> → Note cible : `MyHeritage.md`
> → Catégorie : `organisation`
> → Source : `grimaud`

Cette question peut ensuite être traitée lors d'une session de **Lecture** ou de **Retouche**.

---

## Flux de Données

### Email

```
IMAP Inbox
    │
    ▼
[Processor] ──► [Queue] ──► [UI Péripéties]
    │                            │
    ▼                            ▼
[Analysis] ◄─────────────► [Approval]
    │                            │
    ▼                            ▼
[Context] ◄──── [Notes] ───► [Action]
```

### Teams

```
Graph API
    │
    ▼
[TeamsClient] ──► [Normalizer] ──► [Processor]
                                       │
                                       ▼
                                   [Queue]
```

### Calendrier

```
Graph API
    │
    ▼
[CalendarClient] ──► [Normalizer] ──► [Briefing]
                                          │
                                          ▼
                                    [Conflicts]
```

---

## Stockage

### Base de Données

| Composant | Stockage |
|-----------|----------|
| Queue | JSON files (`data/queue/`) |
| Notes | Markdown files (`data/notes/`) |
| Métadonnées | SQLite (`data/metadata.db`) |
| Vecteurs | FAISS index (`data/faiss/`) |
| Config | YAML (`config/`) |

### Versioning

- Notes versionnées avec Git
- Historique complet des modifications
- Restauration possible

---

## API

### REST Endpoints

| Groupe | Endpoints |
|--------|-----------|
| **System** | `/api/health`, `/api/status`, `/api/config` |
| **Auth** | `/api/auth/login`, `/api/auth/check` |
| **Queue** | `/api/queue`, `/api/queue/{id}/approve` |
| **Notes** | `/api/notes`, `/api/notes/reviews/due` |
| **Briefing** | `/api/briefing/morning`, `/api/briefing/meeting/{id}` |

### WebSockets

| Endpoint | Usage |
|----------|-------|
| `/ws/events` | Événements en temps réel |
| `/ws/status` | État du système |
| `/ws/notifications` | Alertes push |

---

## Dashboard Valets

Accès : `/valets`

Visualisez l'activité de chaque valet :
- État actuel (idle, processing, error)
- Dernière activité
- Métriques de performance
- Logs récents

---

## Diagnostics

### Logs

```bash
# Voir les logs en temps réel
tail -f logs/scapin.log

# Filtrer par niveau
grep ERROR logs/scapin.log
```

### Métriques

- Temps de traitement par valet
- Taux de succès des actions
- Latence API

### Health Check

```bash
curl http://localhost:8000/api/health
```

Retourne l'état de chaque composant.
