# Workflow v2 : Architecture Simplifiée

**Version** : 2.1.0
**Date** : 11 janvier 2026
**Statut** : Approuvé

> Remplace WORKFLOW_V2_SPEC.md (trop complexe)

---

## 1. Principes

### 1.1 Simplification Radicale

| Avant (v2 complexe) | Maintenant (v2.1) |
|---------------------|-------------------|
| 6 phases | 4 phases |
| ML local (GLiNER, SetFit) | 0 ML local |
| Fast Path complexe | Pas de Fast Path |
| Multi-pass reasoning | 1 appel API |
| ~27 nouveaux fichiers | ~6 nouveaux fichiers |
| ~$100/mois | ~$16-20/mois |

### 1.2 Philosophie

```
TOUT analyser avec l'API (Haiku)
    → Extraction entités par l'IA (pas de ML local)
    → Classification importance par l'IA
    → Enrichissement PKM
    → Action sur événement
```

**Pourquoi ?** Haiku coûte $0.03/événement. Pas rentable de complexifier pour économiser ça.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW V2.1                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PHASE 1 : PERCEPTION                        [LOCAL]    │   │
│  │  • Normalisation → PerceivedEvent (existant)            │   │
│  │  • Embedding (sentence-transformers, existant)          │   │
│  │  Temps: ~100ms                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PHASE 2 : CONTEXTE                          [LOCAL]    │   │
│  │  • Recherche sémantique notes (FAISS, existant)         │   │
│  │  • Top 3-5 notes pertinentes                            │   │
│  │  • Résumé contexte pour prompt                          │   │
│  │  Temps: ~200ms                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PHASE 3 : ANALYSE                           [API]      │   │
│  │  • 1 appel Haiku (défaut)                               │   │
│  │  • Escalade Sonnet si confidence < 0.7                  │   │
│  │  • Output: extractions + action                         │   │
│  │  Temps: ~1-2s                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PHASE 4 : APPLICATION                       [LOCAL]    │   │
│  │  • Enrichir notes (si extractions)                      │   │
│  │  • Créer tâches OmniFocus (si deadlines/engagements)    │   │
│  │  • Exécuter action (archive/flag/queue)                 │   │
│  │  • Apprentissage Sganarelle (patterns)                  │   │
│  │  Temps: ~200ms                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  TOTAL: ~2s par événement                                      │
│  COÛT: ~$0.03 par événement (Haiku)                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 3 : Analyse (Détail)

### 3.1 Sélection du Modèle

```python
async def analyze(event: PerceivedEvent, context: list[Note]) -> AnalysisResult:
    """Analyse avec escalade automatique"""

    # 1. Essayer Haiku
    result = await call_haiku(event, context)

    # 2. Escalader si pas confiant
    if result.confidence < 0.7:
        result = await call_sonnet(event, context)

    return result
```

**Estimation** : 90% Haiku, 10% Sonnet

### 3.2 Prompt

```jinja2
Tu es Scapin, assistant cognitif de Johan.

## ÉVÉNEMENT
Type: {{ event.type }}
De: {{ event.sender }}
Sujet: {{ event.subject }}
Date: {{ event.timestamp }}

{{ event.content | truncate(2000) }}

## CONTEXTE (notes existantes)
{% for note in context[:3] %}
### {{ note.title }} ({{ note.type }})
{{ note.content | truncate(300) }}
---
{% endfor %}

## RÈGLES D'EXTRACTION

Extrais UNIQUEMENT les informations PERMANENTES :

✅ EXTRAIRE :
- Décisions actées ("budget validé", "choix techno X")
- Engagements ("Marc s'engage à livrer lundi")
- Faits importants ("nouveau client signé", "Marie promue")
- Dates clés (deadlines, jalons)
- Relations ("Marc rejoint projet Alpha")

❌ NE PAS EXTRAIRE :
- Lieux/heures de réunion ponctuels
- Formules de politesse
- Confirmations simples ("OK", "Bien reçu")
- Détails logistiques temporaires

## FORMAT RÉPONSE

```json
{
  "extractions": [
    {
      "info": "Description concise de l'information",
      "type": "decision|engagement|fait|deadline|relation",
      "importance": "haute|moyenne",
      "note_cible": "Titre de la note à enrichir",
      "note_action": "enrichir|creer",
      "omnifocus": false
    }
  ],
  "action": "archive|flag|queue|rien",
  "confidence": 0.0-1.0,
  "raisonnement": "Explication courte"
}
```

Si rien d'important : `"extractions": []`
```

### 3.3 Output

```python
@dataclass
class Extraction:
    info: str
    type: str  # decision, engagement, fait, deadline, relation
    importance: str  # haute, moyenne
    note_cible: str
    note_action: str  # enrichir, creer
    omnifocus: bool  # créer tâche OmniFocus ?

@dataclass
class AnalysisResult:
    extractions: list[Extraction]
    action: str  # archive, flag, queue, rien
    confidence: float
    raisonnement: str
    model_used: str  # haiku, sonnet
    tokens_used: int
```

---

## 4. Phase 4 : Application (Détail)

### 4.1 Enrichissement Notes

```python
async def apply_extractions(result: AnalysisResult) -> EnrichmentResult:
    notes_updated = []
    notes_created = []
    tasks_created = []

    for extraction in result.extractions:
        # 1. Trouver ou créer la note
        note = note_manager.get_by_title(extraction.note_cible)

        if note is None and extraction.note_action == "creer":
            note = note_manager.create(title=extraction.note_cible)
            notes_created.append(note.id)

        if note:
            # 2. Enrichir la note
            note_manager.add_info(
                note_id=note.id,
                info=extraction.info,
                type=extraction.type,
                source=event.id,
                date=datetime.now()
            )
            notes_updated.append(note.id)

        # 3. Créer tâche OmniFocus si demandé
        if extraction.omnifocus:
            task_id = await omnifocus.create_task(
                title=extraction.info,
                note=f"Source: {event.subject}"
            )
            tasks_created.append(task_id)

    return EnrichmentResult(
        notes_updated=notes_updated,
        notes_created=notes_created,
        tasks_created=tasks_created
    )
```

### 4.2 Format d'Enrichissement dans les Notes

```markdown
# Projet Alpha

## Informations clés

### Décisions
- **2026-01-11** : Budget validé à 50k€ — [source](scapin://email/123)
- **2025-11-20** : Choix techno Python/FastAPI — [source](scapin://email/89)

### Équipe
- Marc Dupont (Tech Lead) — depuis 2026-01-05
- Marie Martin (Finance)

### Jalons
- [x] 2025-10-15 : Kickoff
- [ ] 2026-03-15 : MVP
- [ ] 2026-06-30 : Go-live
```

### 4.3 Seuils de Validation

| Confidence | Action |
|------------|--------|
| ≥ 0.85 | Application automatique |
| 0.7 - 0.85 | Application auto + notification |
| < 0.7 | Queue pour validation manuelle |

---

## 5. Coûts

### 5.1 Estimation Mensuelle

```
460 événements/jour × 30 jours = 13,800 événements/mois

90% Haiku (12,420 événements) :
  Input  : 12,420 × 2,500 tokens × $0.25/M = $7.76
  Output : 12,420 × 500 tokens × $1.25/M = $7.76
  Sous-total Haiku : $15.52

10% Sonnet (1,380 événements) :
  Input  : 1,380 × 2,500 tokens × $3/M = $10.35
  Output : 1,380 × 500 tokens × $15/M = $10.35
  Sous-total Sonnet : $20.70

TOTAL : ~$36/mois
```

### 5.2 Optimisations Possibles

| Optimisation | Économie | Effort |
|--------------|----------|--------|
| Réduire contexte (2 notes au lieu de 3) | -15% | Facile |
| Résumer événements longs | -20% | Moyen |
| Batch nocturne pour newsletters | -10% | Moyen |

---

## 6. Configuration

```python
# src/core/config_manager.py

class WorkflowV2Config(BaseSettings):
    """Configuration Workflow v2.1 simplifié"""

    # Activation
    enabled: bool = True

    # Modèles
    default_model: str = "haiku"
    escalation_model: str = "sonnet"
    escalation_threshold: float = 0.7

    # Contexte
    context_notes_count: int = 3
    context_note_max_chars: int = 300
    event_content_max_chars: int = 2000

    # Application
    auto_apply_threshold: float = 0.85
    notify_threshold: float = 0.7

    # OmniFocus
    omnifocus_enabled: bool = True
    omnifocus_default_project: str = "Inbox"
```

---

## 7. Fichiers à Créer/Modifier

### 7.1 Nouveaux Fichiers (6)

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `src/core/models/v2_models.py` | ~100 | Extraction, AnalysisResult |
| `src/sancho/analyzer.py` | ~150 | Analyse Haiku/Sonnet |
| `src/sancho/templates/extraction.j2` | ~80 | Prompt template |
| `src/passepartout/enricher.py` | ~200 | Application des extractions |
| `src/integrations/apple/omnifocus.py` | ~150 | Client OmniFocus |
| `tests/unit/test_v2_workflow.py` | ~200 | Tests |

**Total : ~880 lignes** (vs ~5000 dans la spec précédente)

### 7.2 Fichiers à Modifier (4)

| Fichier | Modification |
|---------|--------------|
| `src/trivelin/processor.py` | Appeler nouveau workflow |
| `src/core/config_manager.py` | Ajouter WorkflowV2Config |
| `src/passepartout/note_manager.py` | Méthode `add_info()` |
| `src/jeeves/api/routers/queue.py` | Nouveaux types queue |

---

## 8. Plan d'Implémentation

### Semaine 1 : Fondations

1. `WorkflowV2Config` dans config_manager.py
2. `v2_models.py` avec types
3. Tests unitaires modèles

### Semaine 2 : Analyse

4. `analyzer.py` avec appel Haiku/Sonnet
5. `extraction.j2` template
6. Tests avec mocks API

### Semaine 3 : Application

7. `enricher.py` pour notes
8. `omnifocus.py` client
9. Intégration dans processor.py

### Semaine 4 : Polish

10. Tests intégration
11. Ajustements prompts
12. Documentation

**Total : 4 semaines** (vs 12 semaines dans la spec précédente)

---

## 9. Migration

### 9.1 Feature Flag

```bash
# .env
WORKFLOW_V2_ENABLED=true  # Active le nouveau workflow
```

### 9.2 Rollback

Si problème, simplement `WORKFLOW_V2_ENABLED=false` → retour au v1.

### 9.3 Coexistence

Les deux workflows peuvent coexister pendant la période de test.

---

## 10. Métriques de Succès

| Métrique | Objectif | Mesure |
|----------|----------|--------|
| Temps/événement | < 3s | Logs |
| Coût/mois | < $50 | Anthropic dashboard |
| Extractions pertinentes | > 85% | Review manuelle |
| Notes enrichies/jour | > 20 | Compteur |
| Erreurs/jour | < 5 | Logs |

---

*Document simplifié le 11 janvier 2026*
