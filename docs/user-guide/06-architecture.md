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

## Raisonnement Multi-Passes (v2.2)

Sancho utilise une architecture multi-pass avec escalade intelligente :

### Pass 1 : Extraction Aveugle (Haiku)

- Analyse SANS contexte (évite les biais)
- Extraction des entités mentionnées (personnes, projets, dates...)
- Action suggérée initiale
- Confiance typique : 60-80%

### Recherche Contextuelle

Si confiance < 95%, recherche PRÉCISE par entités :
- Notes PKM contenant ces personnes/projets
- Événements calendrier liés
- Tâches OmniFocus existantes
- Emails précédents avec ces contacts

### Pass 2-3 : Raffinement (Haiku)

- Re-analyse avec contexte trouvé
- Corrections : "Marc" → "Marc Dupont (CFO)"
- Détection doublons : "info déjà dans note X"
- Confiance typique : 80-95%

### Pass 4 : Escalade Sonnet (si nécessaire)

Si confiance < 80% après pass 3 :
- Raisonnement plus profond
- Résolution d'ambiguïtés complexes
- Confiance typique : 85-95%

### Pass 5 : Escalade Opus (cas complexes)

Si confiance < 75% OU cas "high-stakes" :
- Montant > 10,000€
- Deadline < 48 heures
- Expéditeur VIP (CEO, partenaire clé)
- Raisonnement expert, confiance : 90-99%

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
