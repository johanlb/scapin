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
│  JEEVES — Interface                                           │
│  • API REST (FastAPI)                                         │
│  • Interface CLI                                              │
│  • WebSockets temps réel                                      │
└──────────────────────────────────────────────────────────────┘
```

---

## Raisonnement Multi-Passes

Sancho utilise jusqu'à 5 passes de raisonnement :

### Pass 1 : Analyse Initiale

- Classification du type de message
- Extraction du sujet et de l'expéditeur
- Score d'urgence initial

### Pass 2 : Enrichissement Contexte

- Récupération des notes liées (Passepartout)
- Historique des interactions avec l'expéditeur
- Contexte des projets mentionnés

### Pass 3 : Génération d'Action

- Proposition d'action (archive, répondre, tâche...)
- Destination (dossier cible)
- Score de confiance

### Pass 4 : Validation (optionnel)

Si confiance < 80% :
- Deuxième analyse avec contexte supplémentaire
- Consensus entre passes

### Pass 5 : Finalisation

- Extraction finale des entités
- Proposition de notes à créer/enrichir
- Tâches à suggérer

### Convergence

Le processus s'arrête quand :
- Confiance > 85%
- Maximum 5 passes atteint
- Pas de changement entre passes

---

## Flux de Données

### Email

```
IMAP Inbox
    │
    ▼
[Processor] ──► [Queue] ──► [UI Flux]
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
