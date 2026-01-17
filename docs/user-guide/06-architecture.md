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
