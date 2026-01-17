# Workflow v2 : Architecture Simplifiée

**Version** : 2.2.0
**Date** : 12 janvier 2026
**Statut** : Approuvé

> Remplace WORKFLOW_V2_SPEC.md (trop complexe)
> **v2.2** : Architecture Multi-Pass avec escalade Haiku → Sonnet → Opus
> Voir [MULTI_PASS_SPEC.md](MULTI_PASS_SPEC.md) pour la spécification complète.

---

## 1. Principes

### 1.1 Évolution Architecturale

| Aspect | v2.1 | v2.2 (Multi-Pass) |
|--------|------|-------------------|
| Phases | 4 phases linéaires | Multi-pass itératif |
| Contexte | Avant extraction | Après extraction (ciblé) |
| Appels API | 1-2 (Haiku/Sonnet) | 1-5 (Haiku → Sonnet → Opus) |
| Convergence | Seuil fixe 0.7 | Confiance 95% + stabilité |
| Coût/mois | ~$38 | ~$59 (qualité +50%) |
| Qualité | Variable | Excellente (92%+ confiance) |

### 1.2 Philosophie v2.2

```
Multi-Pass : Extraire → Contextualiser → Raffiner
    → Pass 1: Extraction AVEUGLE (sans contexte)
    → Recherche contextuelle par ENTITÉS extraites
    → Pass 2+: Raffinement avec contexte PRÉCIS
    → Escalade Haiku → Sonnet → Opus si complexe
    → Arrêt dès confiance 95% atteinte
```

**Pourquoi l'inversion ?**
- v2.1 : Recherche contexte AVANT extraction → recherche floue (sémantique)
- v2.2 : Recherche contexte APRÈS extraction → recherche précise (par entité)

**Coût maîtrisé** : ~85% des emails convergent en 2 passes Haiku (~$0.0028).

---

## 2. Architecture v2.2 Multi-Pass

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW V2.2 MULTI-PASS                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  PERCEPTION                                            [LOCAL]      │ │
│  │  Email → PerceivedEvent (normalisation + embedding)                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 1: EXTRACTION AVEUGLE                            [HAIKU]     │ │
│  │  • Prompt SANS contexte (évite biais)                              │ │
│  │  • Extraction entités + action suggérée                            │ │
│  │  • Confiance typique: 60-80%                                       │ │
│  │  • Coût: ~$0.0013                                                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 95%? │──→ OUI ──→ APPLICATION                       │
│            └──────┬──────┘                                              │
│                   ↓ NON                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  RECHERCHE CONTEXTUELLE                           [LOCAL + API]    │ │
│  │  Pour chaque entité extraite:                                      │ │
│  │  • Notes PKM (recherche par titre/type)                            │ │
│  │  • Calendar (événements avec cette personne/projet)                │ │
│  │  • OmniFocus (tâches existantes)                                   │ │
│  │  • Email archive (échanges précédents)                             │ │
│  │  → CrossSourceEngine.search(entities)                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 2-3: RAFFINEMENT                                 [HAIKU]     │ │
│  │  • Extraction + Contexte trouvé                                    │ │
│  │  • Corrections: "Marc" → "Marc Dupont"                             │ │
│  │  • Doublons: "info déjà dans note X"                               │ │
│  │  • Confiance typique: 80-95%                                       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 90%? │──→ OUI ──→ APPLICATION                       │
│            └──────┬──────┘                                              │
│                   ↓ NON (conf < 80%)                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 4: ESCALADE SONNET                              [SONNET]     │ │
│  │  • Raisonnement plus profond                                       │ │
│  │  • Résolution ambiguïtés complexes                                 │ │
│  │  • Coût: ~$0.015                                                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 90%? │──→ OUI ──→ APPLICATION                       │
│            └──────┬──────┘                                              │
│                   ↓ NON (conf < 75% OU high-stakes)                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 5: ESCALADE OPUS                                 [OPUS]      │ │
│  │  • Raisonnement expert                                             │ │
│  │  • High-stakes: montant > 10k€, deadline < 48h, VIP               │ │
│  │  • Si incertain: génère question clarification                     │ │
│  │  • Coût: ~$0.075                                                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  APPLICATION                                                        │ │
│  │  • Enrichir notes PKM                                              │ │
│  │  • Créer tâches OmniFocus / événements Calendar                    │ │
│  │  • Exécuter action (archive/flag/queue)                            │ │
│  │  • Apprentissage Sganarelle                                        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  DISTRIBUTION: 15% Pass 1 | 70% Pass 2 | 10% Pass 3 | 4% Pass 4 | 1% P5│
│  COÛT MOYEN: ~$0.0043/événement | TOTAL: ~$59/mois                      │
│  CONFIANCE MOYENNE: 92%+                                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
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

### ✅ EXTRAIRE (14 types)

| Type | Description | OmniFocus |
|------|-------------|-----------|
| **decision** | Choix actés, arbitrages | Non |
| **engagement** | Promesses, obligations | Oui si deadline |
| **fait** | Faits importants, événements passés | Non |
| **deadline** | Dates limites avec conséquences | **Toujours** |
| **evenement** | Dates sans obligation (réunion, anniversaire) | Optionnel |
| **relation** | Liens entre personnes/projets | Non |
| **coordonnees** | Téléphone, adresse, email | Non |
| **montant** | Valeurs financières, factures | Non |
| **reference** | Numéros de dossier, facture, ticket | Non |
| **demande** | Requêtes faites à Johan | Oui si deadline |
| **citation** | Propos exacts à retenir (verbatim) | Non |
| **objectif** | Buts, cibles, KPIs | Non |
| **competence** | Expertise/compétences d'une personne | Non |
| **preference** | Préférences de travail d'une personne | Non |

### Niveaux d'importance (3)

| Niveau | Description | Icône |
|--------|-------------|-------|
| **haute** | Critique, impact fort, à ne pas rater | 🔴 |
| **moyenne** | Utile, bon à savoir | 🟡 |
| **basse** | Contexte, référence future (ex: numéros, coordonnées) | ⚪ |

### ❌ NE PAS EXTRAIRE
- Formules de politesse, confirmations simples
- Détails logistiques temporaires
- Informations déjà connues (dans le contexte)

## FORMAT RÉPONSE

```json
{
  "extractions": [
    {
      "info": "Description concise de l'information",
      "type": "decision|engagement|fait|deadline|evenement|relation|coordonnees|montant|reference|demande|citation|objectif|competence|preference",
      "importance": "haute|moyenne|basse",
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
    type: str  # 14 types: decision, engagement, fait, deadline, evenement,
               #          relation, coordonnees, montant, reference, demande,
               #          citation, objectif, competence, preference
    importance: str  # haute, moyenne, basse
    note_cible: str
    note_action: str  # enrichir, creer
    omnifocus: bool  # créer tâche OmniFocus ?
    calendar: bool  # créer événement calendrier ?
    date: str | None  # YYYY-MM-DD
    time: str | None  # HH:MM
    # v2.1.2: Nouveaux champs
    timezone: str | None  # HF, HM, Maurice, UTC, Paris
    duration: int | None  # minutes (défaut 60)
    has_attachments: bool  # pièces jointes importantes
    priority: str | None  # OmniFocus: haute, normale, basse
    project: str | None  # OmniFocus: projet cible

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
    events_created = []  # v2.1.2

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
                note=f"Source: {event.subject}",
                due_date=extraction.date,
                priority=extraction.priority,  # v2.1.2
                project=extraction.project  # v2.1.2
            )
            tasks_created.append(task_id)

        # 4. Créer événement calendrier si demandé (v2.1.2)
        if extraction.calendar and extraction.date:
            event_id = await calendar.create_event(
                title=extraction.info,
                date=extraction.date,
                time=extraction.time,
                timezone=extraction.timezone,  # HF, HM, Maurice, UTC
                duration=extraction.duration or 60  # minutes
            )
            events_created.append(event_id)

    return EnrichmentResult(
        notes_updated=notes_updated,
        notes_created=notes_created,
        tasks_created=tasks_created,
        events_created=events_created  # v2.1.2
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

---

## 11. Décisions de Conception

### 11.1 Structure des Notes (Hybride)

```markdown
# Marc Dupont

## Résumé
Tech Lead Projet Alpha depuis janvier 2026. Budget 50k€ validé.

## Historique récent
- **2026-01-11** : Budget validé 50k€ — [source](scapin://email/123)
- **2026-01-10** : Rejoint Projet Alpha — [source](scapin://email/118)

## Historique archivé
<!-- Entrées > 3 mois déplacées ici automatiquement -->
```

### 11.2 Création de Notes

**Toujours demander confirmation** avant de créer une nouvelle note.

```python
if note_action == "creer":
    # Ne pas créer automatiquement, mettre en queue
    queue.add(QueueItem(
        type="create_note",
        title=extraction.note_cible,
        content=extraction.info,
        source_event=event_id
    ))
```

### 11.3 Notes Longues (Auto-archivage)

Quand une note dépasse 100 entrées dans "Historique récent" :
- Déplacer les entrées > 3 mois vers "Historique archivé"
- Garder le résumé à jour

### 11.4 OmniFocus (Matching Projet)

```python
async def create_task(self, extraction: Extraction) -> str:
    # 1. Essayer de matcher avec projet existant
    projects = await self.omnifocus.list_projects()
    matched = find_best_match(extraction.note_cible, projects)

    if matched and matched.score > 0.8:
        project = matched.name
    else:
        project = "Inbox"  # Fallback

    return await self.omnifocus.create_task(
        title=extraction.info,
        project=project
    )
```

### 11.5 Bootstrap (Création Agressive)

Au début (PKM < 50 notes), être plus agressif :
- Proposer plus de créations de notes
- Seuils de création plus bas

```python
def should_propose_creation(self, pkm_size: int) -> bool:
    if pkm_size < 50:
        return True  # Bootstrap mode
    return self.confidence > 0.7
```

### 11.6 Granularité : Petites Notes

**Philosophie** : 1 note = 1 entité (personne, projet, concept)

```
notes/
├── personnes/
│   ├── Marc Dupont.md
│   ├── Sophie Martin.md
│   └── Marie Durand.md
├── projets/
│   ├── Projet Alpha.md
│   └── Budget 2026.md
├── concepts/
│   ├── Architecture Microservices.md
│   └── RGPD.md
└── organisations/
    ├── Acme Corp.md
    └── DGFIP.md
```

### 11.7 Récapitulatif des Décisions

| Question | Décision |
|----------|----------|
| Structure notes | Hybride (résumé + historique) |
| Création notes | Toujours confirmation |
| Notes longues | Auto-archivage > 3 mois |
| OmniFocus projet | Matcher existant, sinon Inbox |
| Bootstrap | Création agressive au début |
| Correction erreurs | Manuelle (v2.1) |
| Limite extractions | Pas de limite |
| Granularité | Beaucoup de petites notes |

---

*Document simplifié le 11 janvier 2026*
