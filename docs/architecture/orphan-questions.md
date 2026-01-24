# Questions Orphelines

**Version** : v3.2 | **Module** : Sancho (génération) + Frontin (API/UI)

---

## Vue d'ensemble

Les **questions stratégiques** sont générées par les valets IA pendant l'analyse multi-pass des emails. Elles représentent les décisions que seul Johan peut prendre.

Une question devient **orpheline** quand :
- Elle n'a pas de `target_note` définie
- La note cible spécifiée n'existe pas dans le PKM

---

## Génération des Questions

### Valets et types de questions

| Valet | Modèle | Pass | Type de questions |
|-------|--------|------|-------------------|
| **Grimaud** | Haiku | 1 | Organisation : "Comment traiter ce type de contenu ?" |
| **Bazin** | Sonnet | 2-3 | Structure PKM : "Faut-il créer une note dédiée ?" |
| **Planchet** | Sonnet | 3 | Processus : "Un système batch serait-il utile ?" |
| **Mousqueton** | Sonnet/Opus | 4 | Décisions : "Quelle stratégie adopter ?" |

### Structure d'une question

```python
@dataclass
class StrategicQuestion:
    question: str           # Le texte de la question
    target_note: str | None # Note cible (null → orpheline)
    category: str           # decision, processus, organisation, structure_pkm
    context: str            # Pourquoi cette question est posée
    source: str             # Valet source (grimaud, bazin, planchet, mousqueton)
```

**Code source** : `src/frontin/api/models/queue.py` (StrategicQuestionResponse)

---

## Triage et Distribution

Quand un email est approuvé dans la queue, `_distribute_strategic_questions()` est appelée :

```
strategic_questions[]
        │
        ├─ target_note trouvée dans PKM
        │       │
        │       └→ Ajoutée à la note Apple Notes
        │          Format: ### ❓ {question}
        │
        └─ target_note null OU note inexistante
                │
                └→ Stockée comme ORPHELINE
                   Fichier: data/orphan_questions.json
```

### Points d'appel

La distribution est déclenchée à 3 endroits dans `queue_service.py` :
1. `approve_item()` — Approbation standard
2. `modify_item()` — Modification avec approbation
3. `reject_item()` — Rejet (questions quand même distribuées)

**Code source** : `src/frontin/api/services/queue_service.py`

---

## Stockage

### Questions avec cible → Notes Apple

Ajoutées à la note avec le format Markdown :

```markdown
### ❓ {question}
- **Catégorie** : {category}
- **Source** : {source_valet}
- **Contexte** : {context}
- **Date** : {created_at}
```

**Code source** : `src/passepartout/note_manager.py`

### Questions orphelines → JSON

**Fichier** : `data/orphan_questions.json`

```json
{
  "question_id": "uuid-v4",
  "question": "Faut-il créer une note Généalogie ?",
  "category": "structure_pkm",
  "context": "De nombreux contenus généalogiques identifiés...",
  "source_valet": "bazin",
  "source_email_subject": "MyHeritage - Nouveaux Smart Matches",
  "source_item_id": "queue-item-id",
  "created_at": "2026-01-23T15:30:00Z",
  "intended_target": null,
  "resolved": false,
  "resolved_at": null,
  "resolution": null
}
```

**Code source** : `src/integrations/storage/orphan_questions_storage.py`

---

## Interface Utilisateur

### Page dédiée : `/memoires/orphan-questions`

**Trois onglets** :
- **En attente** : Questions non résolues (`resolved=false`)
- **Résolues** : Questions marquées résolues
- **Par catégorie** : Regroupées par type

**Actions disponibles** :
- Résoudre avec texte optionnel
- Supprimer définitivement
- Filtrer et rechercher

**Affichage** :
- Badge catégorie avec couleur
- Source email (sujet tronqué)
- Temps relatif (il y a 2j)
- Valet source
- Contexte (collapsible)

**Code source** : `web/src/routes/memoires/orphan-questions/+page.svelte`

### Briefing matinal

Section "❓ QUESTIONS STRATÉGIQUES (N)" affichée si `pending_count > 0`.

Intégrée dans le Filage avec **Priorité 1** :
```
Priority 1: 🔴 Questions → Notes avec questions en attente (max 5)
Priority 2: 📅 Événements
Priority 3: 📚 SM-2 Due
Priority 4: ✨ Retouchées
```

**Code source** : `src/frontin/briefing/generator.py`

### Store Svelte

```typescript
// web/src/lib/stores/orphan-questions.svelte.ts

interface OrphanQuestionsState {
  questions: OrphanQuestion[]
  loading: boolean
  error: string | null
  includeResolved: boolean
  pendingCount: number
  totalCount: number
}

// Dérivés
pendingQuestions   // resolved=false
resolvedQuestions  // resolved=true
byCategory         // Groupées par catégorie
isEmpty            // Aucune question
```

---

## API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/briefing/orphan-questions` | GET | Lister les questions (`?include_resolved=true`) |
| `/api/briefing/orphan-questions/{id}/resolve` | POST | Marquer comme résolue |
| `/api/briefing/orphan-questions/{id}` | DELETE | Supprimer définitivement |

### Résoudre une question

```bash
curl -X POST http://localhost:8000/api/briefing/orphan-questions/{id}/resolve \
  -H "Content-Type: application/json" \
  -d '{"resolution": "Texte optionnel de résolution"}'
```

**Effet** :
```json
{
  "resolved": true,
  "resolved_at": "2026-01-23T16:45:00Z",
  "resolution": "Texte de résolution"
}
```

**Code source** : `src/frontin/api/routers/briefing.py`

---

## Catégories

| Catégorie | Valet typique | Exemple |
|-----------|---------------|---------|
| `organisation` | Grimaud | "Comment traiter ce volume de contenu ?" |
| `processus` | Planchet | "Un système batch serait-il utile ?" |
| `structure_pkm` | Bazin | "Faut-il créer une note Généalogie ?" |
| `decision` | Mousqueton | "Quelle stratégie adopter ?" |

---

## Intégrations

### Notes (Passepartout)

- `add_strategic_question(note_id, question)` : Ajoute à une note
- `get_strategic_questions(note_id)` : Extrait les questions
- `resolve_strategic_question(note_id, question_id)` : Marque ❓ → ✅

### Working Memory

Les questions enrichissent le contexte des analyses futures :

```python
working_memory.add_question(question)  # Tracking
working_memory.questions  # List[str] pour context awareness
```

**Code source** : `src/core/memory/working_memory.py`

---

## Cycle de Vie Complet

```
┌─────────────────────────────────────────────────────────────┐
│                    EMAIL ENTRANT                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────┐
        │   ANALYSE MULTI-PASS (4 Valets)    │
        │   → Génère strategic_questions[]   │
        └────────────────┬────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────┐
        │   QUEUE (Péripéties)               │
        │   Email en attente + questions     │
        └────────────────┬────────────────────┘
                         │
                    User Approve
                         │
                         ▼
        ┌─────────────────────────────────────┐
        │ _distribute_strategic_questions()  │
        └────────────────┬────────────────────┘
                         │
        ┌────────────────┴────────────────────┐
        │                                     │
   WITH TARGET                         WITHOUT TARGET
        │                                     │
        ▼                                     ▼
   Apple Note                      orphan_questions.json
   ### ❓ Question                  { resolved: false }
        │                                     │
        └────────────────┬────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────┐
        │   BRIEFING + UI                     │
        │   /memoires/orphan-questions        │
        └────────────────┬────────────────────┘
                         │
                    User Action
                         │
        ┌────────────────┴────────────────────┐
        │                                     │
    RESOLVE                              DELETE
    { resolved: true,                    Supprimé
      resolution: "..." }                définitivement
    (Tracé pour audit)
```

---

## Fichiers Clés

| Fichier | Rôle |
|---------|------|
| `src/sancho/multi_pass_analyzer.py` | Génération des questions par les valets |
| `src/frontin/api/services/queue_service.py` | Distribution (approve/modify/reject) |
| `src/integrations/storage/orphan_questions_storage.py` | Stockage JSON |
| `src/passepartout/note_manager.py` | Questions dans les notes |
| `src/frontin/api/routers/briefing.py` | Endpoints API |
| `src/frontin/briefing/generator.py` | Intégration briefing |
| `web/src/routes/memoires/orphan-questions/+page.svelte` | Page UI |
| `web/src/lib/stores/orphan-questions.svelte.ts` | Store Svelte |

---

## Historique

| Version | Commit | Feature |
|---------|--------|---------|
| v3.2 | `224b245` | Lifecycle complet (génération → résolution) |
| v3.2 | `9f9e820` | Distribution aux notes + orphans |
| v3.2 | `3a0553f` | UI page dédiée `/orphan-questions` |
| v3.1 | `b77cd13` | Exposition API initiale |
