# 07 - Extensions API Nécessaires

[< Retour à l'index](./00-index.md) | [< UX Avancée](./06-ux-avancee.md)

---

## Résumé

Pour supporter l'interface event-centric, **~60 endpoints** doivent être ajoutés au backend FastAPI.

| Domaine | Endpoints | Priorité | Description |
|---------|-----------|----------|-------------|
| Auth | 4 | MVP | Authentification JWT |
| Events | 12 | MVP | Flux unifié (coeur du système) |
| Notes | 14 | MVP | CRUD notes PKM |
| Discussions | 9 | MVP | Chat multi-sessions |
| Briefing | 2 | MVP | Briefings (existant) |
| Journal | 5 | MVP | Journaling interactif |
| Stats | 9 | MVP | Statistiques et analytics |
| Rapports | 5 | Nice-to-have | Rapports générés |
| Search | 3 | MVP | Recherche globale (Cmd+K) |
| Settings | 10 | Nice-to-have | Configuration avancée |
| Valets | 3 | Nice-to-have | Pipeline temps réel |
| WebSocket | 5 | MVP | Temps réel |
| Autres | 12 | Nice-to-have | Focus, Filtres, Tags, etc. |

---

## 1. Auth (`/api/auth`) — MVP

```
POST   /api/auth/login           - Login avec credentials
POST   /api/auth/refresh         - Refresh token JWT
POST   /api/auth/logout          - Invalider token
GET    /api/auth/me              - Informations utilisateur
```

---

## 2. Events — Flux Unifié (`/api/events`) — MVP

Le coeur du système event-centric.

```
# Liste et filtrage
GET    /api/events               - Liste tous les événements (paginé)
                                   ?status=pending|processed|rejected|snoozed
                                   ?source=email|teams|calendar|omnifocus
                                   ?urgency=high|medium|low
                                   ?since=ISO_DATE
                                   ?limit=50&offset=0
GET    /api/events/pending       - Événements à traiter
GET    /api/events/processed     - Événements traités par Scapin
GET    /api/events/rejected      - Événements rejetés
GET    /api/events/snoozed       - Événements reportés (snooze actif)
GET    /api/events/{id}          - Détail d'un événement

# Actions utilisateur
POST   /api/events/{id}/approve  - Approuver action proposée
POST   /api/events/{id}/reject   - Rejeter action proposée
POST   /api/events/{id}/modify   - Modifier et approuver
POST   /api/events/{id}/undo     - Annuler action exécutée
POST   /api/events/{id}/snooze   - Reporter un événement
                                   {until: ISO_DATE, note?: string}
DELETE /api/events/{id}/snooze   - Annuler le snooze

# Statistiques
GET    /api/events/stats         - Statistiques (traités, en attente, etc.)
```

**Exemple réponse `GET /api/events/pending`** :
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "evt_123",
        "source": "email",
        "type": "message",
        "summary": "Email de Marie — Budget Q2",
        "urgency": "high",
        "confidence": 0.72,
        "proposed_action": {
          "type": "archive",
          "reason": "Discussion déjà traitée en réunion"
        },
        "occurred_at": "2026-01-04T09:30:00Z"
      }
    ],
    "total": 12,
    "pending_count": 12
  }
}
```

---

## 3. Notes PKM (`/api/notes`) — MVP

CRUD complet pour le système de notes Markdown.

```
# Notes
GET    /api/notes                - Liste toutes les notes
                                   ?folder=path/to/folder
                                   ?search=keyword
                                   ?recent=10
                                   ?pinned=true
GET    /api/notes/pinned         - Notes épinglées uniquement
GET    /api/notes/{path}         - Contenu d'une note
POST   /api/notes                - Créer nouvelle note
PUT    /api/notes/{path}         - Modifier note existante
DELETE /api/notes/{path}         - Supprimer note (soft delete)
POST   /api/notes/{path}/pin     - Épingler/désépingler une note
GET    /api/notes/{path}/links   - Liens bidirectionnels (backlinks)

# Dossiers
GET    /api/notes/folders        - Arborescence des dossiers
POST   /api/notes/folders        - Créer dossier

# Versions (historique)
GET    /api/notes/{path}/versions     - Liste des versions
GET    /api/notes/{path}/versions/{v} - Contenu d'une version
GET    /api/notes/{path}/diff         - Diff entre versions
                                        ?v1=X&v2=Y
POST   /api/notes/{path}/restore/{v}  - Restaurer une version
```

---

## 4. Discussions Multi-Sessions (`/api/discussions`) — MVP

Conversations persistantes avec Scapin.

```
GET    /api/discussions          - Liste toutes les discussions
                                   ?since=ISO_DATE
                                   ?context_type=event|note|report
                                   ?pinned=true
GET    /api/discussions/pinned   - Discussions épinglées uniquement
POST   /api/discussions          - Créer nouvelle discussion
                                   {title: string, context_id?: string, context_type?: string}
GET    /api/discussions/{id}     - Historique d'une discussion
POST   /api/discussions/{id}/message - Envoyer message
POST   /api/discussions/{id}/pin - Épingler/désépingler
DELETE /api/discussions/{id}     - Supprimer discussion
GET    /api/discussions/suggestions - Suggestions contextuelles
```

---

## 5. Chat Rapide (`/api/chat`) — MVP

Instructions rapides sans discussion persistante.

```
POST   /api/chat/quick           - Instruction rapide (one-shot)
                                   {message: string, context?: object}
GET    /api/chat/suggestions     - Suggestions contextuelles
```

---

## 6. Briefing (`/api/briefing`) — MVP (Existant)

Endpoints déjà implémentés en Phase 0.7.

```
GET    /api/briefing/morning     - Briefing du matin
GET    /api/briefing/meeting/{id}- Briefing pré-réunion
```

---

## 7. Journal (`/api/journal`) — MVP

Journaling interactif quotidien.

```
GET    /api/journal              - Liste des journaux
GET    /api/journal/{date}       - Journal du jour (YYYY-MM-DD)
POST   /api/journal/{date}/generate - Générer draft
PATCH  /api/journal/{date}/answer   - Répondre à une question
                                      {question_id: string, answer: string}
POST   /api/journal/{date}/correct  - Soumettre correction
                                      {item_id: string, correction: object}
```

---

## 8. Statistiques (`/api/stats`) — MVP

Analytics et KPIs.

```
# Stats globales
GET    /api/stats/overview       - Vue globale (KPIs principaux)
                                   ?period=today|week|month|custom
                                   ?from=ISO_DATE&to=ISO_DATE
GET    /api/stats/by-source      - Répartition par source
GET    /api/stats/confidence     - Évolution confiance dans le temps
GET    /api/stats/approval       - Taux d'approbation/rejet/modification

# Stats apprentissage
GET    /api/stats/learning       - Patterns et apprentissages Sganarelle

# Stats tokens (coût API)
GET    /api/stats/tokens         - Consommation tokens API
                                   ?period=week (input, output, coût par modèle)
GET    /api/stats/tokens/budget  - Budget et projection
POST   /api/stats/tokens/alerts  - Configurer alertes budget

# Export
GET    /api/stats/export         - Export CSV/JSON des statistiques
```

---

## 9. Valets — Pipeline Temps Réel (`/api/valets`) — Nice-to-have

Pour la visualisation Pipeline conçue dans 05-mockups-analytics.md.

```
GET    /api/valets               - Status de tous les valets
                                   Retourne: état, sujet actuel, métriques
GET    /api/valets/{name}        - Détail d'un valet spécifique
                                   (trivelin|sancho|passepartout|planchet|figaro|sganarelle)
GET    /api/valets/stats         - Statistiques par valet
                                   ?period=week (appels, succès, échecs, temps moyen)
```

**Exemple réponse `GET /api/valets`** :
```json
{
  "success": true,
  "data": {
    "scapin": {
      "state": "active",
      "current_subject": "Email: Proposition client ABC - 45K"
    },
    "valets": [
      {
        "name": "trivelin",
        "state": "idle",
        "current_subject": null,
        "metrics": {"processed_today": 47, "success_rate": 0.98}
      },
      {
        "name": "sancho",
        "state": "reasoning",
        "current_subject": "Analyse email #1234",
        "metrics": {"passes_avg": 3.2, "confidence_avg": 0.84}
      }
    ]
  }
}
```

---

## 10. Rapports (`/api/reports`) — Nice-to-have

Rapports générés automatiquement.

```
GET    /api/reports              - Liste tous les rapports
                                   ?type=daily|weekly|monthly
                                   ?since=ISO_DATE
GET    /api/reports/daily/{date} - Rapport journalier (YYYY-MM-DD)
GET    /api/reports/weekly/{week}- Rapport hebdomadaire (YYYY-Www)
GET    /api/reports/monthly/{month} - Rapport mensuel (YYYY-MM)
POST   /api/reports/generate     - Générer rapport à la demande
                                   {type: daily|weekly|monthly, date: ...}
GET    /api/reports/{id}/export  - Exporter rapport (PDF, Markdown)
```

---

## 11. Recherche Globale (`/api/search`) — MVP

Pour la Command Palette (Cmd+K).

```
GET    /api/search               - Recherche globale
                                   ?q=keyword
                                   ?types=notes,events,discussions,reports
                                   ?limit=10
GET    /api/search/recent        - Recherches récentes
POST   /api/search/commands      - Exécuter une commande
                                   {command: "new_note", params: {...}}
```

---

## 12. Settings (`/api/settings`) — Nice-to-have

Configuration avancée.

```
# Configuration générale
GET    /api/settings             - Configuration complète
PATCH  /api/settings             - Modifier paramètres

# Comptes email
GET    /api/settings/accounts    - Liste comptes email
POST   /api/settings/accounts    - Ajouter compte
PUT    /api/settings/accounts/{id} - Modifier compte
DELETE /api/settings/accounts/{id} - Supprimer compte

# Intégrations
GET    /api/settings/integrations - Status intégrations
POST   /api/settings/integrations/{name}/test - Tester intégration

# Synchronisation
GET    /api/settings/sync                    - Config synchro tous comptes
GET    /api/settings/sync/defaults           - Valeurs par défaut par source
PATCH  /api/settings/sync/defaults/{source}  - Modifier défauts d'une source
PATCH  /api/settings/sync/account/{account_id} - Modifier synchro d'un compte
                                     {frequency_minutes: int, latency_minutes: int}
```

---

## 13. Autres Endpoints — Nice-to-have

### Mode Focus (`/api/focus`)

```
GET    /api/focus/status         - Status actuel (actif/désactivé, temps restant)
POST   /api/focus/enable         - Activer mode focus
                                   {duration_minutes: int, sync_enabled: bool}
POST   /api/focus/disable        - Désactiver mode focus
```

### Filtres Sauvegardés (`/api/filters`)

```
GET    /api/filters              - Liste des filtres sauvegardés
POST   /api/filters              - Créer nouveau filtre
                                   {name: string, criteria: {...}}
PUT    /api/filters/{id}         - Modifier filtre
DELETE /api/filters/{id}         - Supprimer filtre
```

### Notifications (`/api/notifications`)

```
GET    /api/notifications        - Liste des notifications
                                   ?unread=true
POST   /api/notifications/{id}/read - Marquer comme lue
POST   /api/notifications/read-all  - Tout marquer comme lu
DELETE /api/notifications/{id}   - Supprimer notification
```

### Tags (`/api/tags`)

```
GET    /api/tags                 - Liste des tags
POST   /api/tags                 - Créer un tag
                                   {name: string, color: string, emoji?: string}
PUT    /api/tags/{id}            - Modifier un tag
DELETE /api/tags/{id}            - Supprimer un tag
POST   /api/events/{id}/tags     - Ajouter tags à un événement
DELETE /api/events/{id}/tags/{tag_id} - Retirer un tag
```

### Annotations (`/api/annotations`)

```
POST   /api/events/{id}/annotation - Ajouter annotation
PUT    /api/events/{id}/annotation - Modifier annotation
DELETE /api/events/{id}/annotation - Supprimer annotation
```

### Templates Notes (`/api/templates`)

```
GET    /api/templates            - Liste des templates
POST   /api/templates            - Créer nouveau template
PUT    /api/templates/{id}       - Modifier template
DELETE /api/templates/{id}       - Supprimer template
```

### Quick Capture (`/api/capture`)

```
POST   /api/capture              - Capture rapide d'une note
                                   {content: string, destination?: path, tags?: []}
GET    /api/capture/inbox        - Liste des captures en inbox
```

### Activité / Timeline (`/api/activity`)

```
GET    /api/activity             - Timeline d'activité
                                   ?filter=scapin|user|system|all
                                   ?since=ISO_DATE
                                   ?limit=50
```

### Scapin Status (`/api/status`)

```
GET    /api/status               - Status temps réel de Scapin
                                   {state: active|reasoning|focus|error|paused,
                                    last_sync: ISO_DATE, focus_remaining: minutes}
```

---

## 14. WebSocket Temps Réel (`/ws`) — MVP

Connexions persistantes pour mises à jour temps réel.

```
WS     /ws/events                - Nouveaux événements en temps réel
WS     /ws/discussions/{id}      - Chat temps réel dans une discussion
WS     /ws/chat                  - Chat rapide avec Scapin
WS     /ws/status                - Status Scapin en temps réel
WS     /ws/notifications         - Notifications push
```

**Format messages WebSocket** :
```json
{
  "type": "event_created|event_processed|status_change|notification",
  "data": { ... },
  "timestamp": "2026-01-04T10:30:00Z"
}
```

---

## Ordre d'Implémentation Suggéré

| Priorité | Endpoints | Justification |
|----------|-----------|---------------|
| **1** | Auth | Sécurité avant tout |
| **2** | Events (base) | Coeur du système |
| **3** | Status + WebSocket | Temps réel |
| **4** | Search | Command Palette (UX critique) |
| **5** | Notes | Accès PKM |
| **6** | Discussions + Chat | Interaction Scapin |
| **7** | Journal | Feedback loop |
| **8** | Stats | Analytics |
| **9** | Valets | Pipeline visualisation |
| **10** | Reste | Settings, Rapports, etc. |

---

[< UX Avancée](./06-ux-avancee.md) | [Suivant : Implémentation >](./08-implementation.md)
