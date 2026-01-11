# Spécification Multi-Pass Extraction v2.2

**Version** : 2.2.0
**Date** : 12 janvier 2026
**Statut** : Approuvé
**Auteur** : Johan + Claude

---

## 1. Vue d'Ensemble

### 1.1 Philosophie

> **"Extraire d'abord, contextualiser ensuite, raffiner jusqu'à confiance."**

L'architecture Multi-Pass inverse l'approche traditionnelle :
- **Avant (v2.1)** : Contexte → Extraction (recherche floue sur texte brut)
- **Maintenant (v2.2)** : Extraction → Contexte → Raffinement (recherche précise par entités)

### 1.2 Principes Clés

| Principe | Description |
|----------|-------------|
| **Extraction aveugle** | Pass 1 sans contexte pour éviter les biais |
| **Contexte ciblé** | Recherche par entités extraites, pas sémantique floue |
| **Convergence** | S'arrêter dès que confiant, pas de passes inutiles |
| **Escalade progressive** | Haiku → Sonnet → Opus selon complexité |
| **Coût maîtrisé** | Optimiser pour ~85% en 2 passes Haiku |

### 1.3 Flux Résumé

```
Email → Pass 1 (Haiku, aveugle)
            ↓
      Confident? → OUI → Application
            ↓ NON
      Recherche contexte par entités
            ↓
      Pass 2 (Haiku, contexte)
            ↓
      Confident? → OUI → Application
            ↓ NON
      Pass 3-5 (escalade si besoin)
            ↓
      Application ou Clarification humaine
```

---

## 2. Architecture Détaillée

### 2.1 Diagramme de Flux

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-PASS EXTRACTION v2.2                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  PHASE 1: PERCEPTION                                                    │ │
│  │  Email → PerceivedEvent (inchangé)                                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 1: EXTRACTION AVEUGLE                              [HAIKU]       │ │
│  │  ══════════════════════════════════════════════════════════════════    │ │
│  │  • Prompt SANS contexte                                                │ │
│  │  • Input: email brut uniquement                                        │ │
│  │  • Output: RawExtractionResult                                         │ │
│  │    - extractions[] (entités, faits, actions)                          │ │
│  │    - action_suggested                                                  │ │
│  │    - confidence (typiquement 60-80%)                                  │ │
│  │    - entities_mentioned[] (pour recherche)                            │ │
│  │  • Coût: ~$0.0013                                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                         │
│                    ┌───────────────────────────────┐                        │
│                    │  confidence >= 95%            │                        │
│                    │  ET action simple (archive)?  │──→ APPLICATION         │
│                    └───────────────────────────────┘                        │
│                                    ↓ NON                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  RECHERCHE CONTEXTUELLE 1                                [LOCAL+API]   │ │
│  │  ══════════════════════════════════════════════════════════════════    │ │
│  │  Pour chaque entité extraite:                                          │ │
│  │  • Notes PKM: recherche par titre/type                                │ │
│  │  • Calendar: événements avec cette personne/ce projet                 │ │
│  │  • OmniFocus: tâches existantes liées                                 │ │
│  │  • Email archive: échanges précédents avec expéditeur                 │ │
│  │  → CrossSourceEngine.search(entities)                                  │ │
│  │  • Coût: ~0 (local) ou ~$0.001 (API web)                              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 2: RAFFINEMENT CONTEXTUEL                          [HAIKU]       │ │
│  │  ══════════════════════════════════════════════════════════════════    │ │
│  │  • Prompt avec:                                                        │ │
│  │    - Extraction initiale (Pass 1)                                     │ │
│  │    - Contexte trouvé (notes, calendar, tasks)                         │ │
│  │  • L'IA peut:                                                          │ │
│  │    - Corriger note_cible ("Marc" → "Marc Dupont")                     │ │
│  │    - Détecter doublons ("info déjà dans note X")                      │ │
│  │    - Enrichir ("Marc = Tech Lead Projet Alpha")                       │ │
│  │    - Ajuster actions ("tâche existe → skip omnifocus")                │ │
│  │  • Output: RefinedExtractionResult                                     │ │
│  │    - confidence (typiquement 80-95%)                                  │ │
│  │    - changes_made[] (traçabilité)                                     │ │
│  │    - new_entities_discovered[]                                        │ │
│  │  • Coût: ~$0.0015                                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                         │
│                    ┌───────────────────────────────┐                        │
│                    │  confidence >= 95%            │                        │
│                    │  OU pas de changement?        │──→ APPLICATION         │
│                    └───────────────────────────────┘                        │
│                                    ↓ NON                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  RECHERCHE CONTEXTUELLE 2 (si nouvelles entités)         [LOCAL+API]   │ │
│  │  ══════════════════════════════════════════════════════════════════    │ │
│  │  • Recherche pour entités nouvellement découvertes                    │ │
│  │  • Recherche thread email si "suite à..."                             │ │
│  │  • Détection conflits calendar                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 3: APPROFONDISSEMENT                               [HAIKU]       │ │
│  │  ══════════════════════════════════════════════════════════════════    │ │
│  │  • Contexte élargi (nouvelles entités, thread complet)                │ │
│  │  • Résolution de conflits détectés                                    │ │
│  │  • confidence cible: 85-95%                                           │ │
│  │  • Coût: ~$0.0015                                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                         │
│                    ┌───────────────────────────────┐                        │
│                    │  confidence >= 90%?           │──→ APPLICATION         │
│                    └───────────────────────────────┘                        │
│                                    ↓ NON (confidence < 80%)                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 4: ESCALADE SONNET                                 [SONNET]      │ │
│  │  ══════════════════════════════════════════════════════════════════    │ │
│  │  • Raisonnement plus profond                                          │ │
│  │  • Résolution ambiguïtés complexes                                    │ │
│  │  • confidence cible: 90-98%                                           │ │
│  │  • Coût: ~$0.015                                                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                         │
│                    ┌───────────────────────────────┐                        │
│                    │  confidence >= 90%?           │──→ APPLICATION         │
│                    └───────────────────────────────┘                        │
│                                    ↓ NON (confidence < 75% OU high-stakes)   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  PASS 5: ESCALADE OPUS                                   [OPUS]        │ │
│  │  ══════════════════════════════════════════════════════════════════    │ │
│  │  • Raisonnement expert                                                │ │
│  │  • Cas vraiment difficiles                                            │ │
│  │  • Si toujours incertain: génère question clarification              │ │
│  │  • confidence cible: 95-99%                                           │ │
│  │  • Coût: ~$0.075                                                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  APPLICATION OU CLARIFICATION                                          │ │
│  │  ══════════════════════════════════════════════════════════════════    │ │
│  │  Si confidence >= 85%:                                                │ │
│  │    → Enrichir notes, créer tâches/events, exécuter action            │ │
│  │  Sinon:                                                               │ │
│  │    → action: "queue" + question clarification pour humain            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Critères de Convergence

```python
@dataclass
class PassResult:
    """Résultat d'une passe d'extraction"""
    pass_number: int
    model_used: str  # haiku, sonnet, opus
    extractions: list[Extraction]
    action: str
    confidence: float
    entities_discovered: set[str]
    changes_made: list[str]
    reasoning: str
    tokens_used: int
    duration_ms: float

def should_stop(current: PassResult, previous: PassResult | None) -> bool:
    """Détermine si on doit arrêter les passes"""

    # Critère 1: Confiance suffisante
    if current.confidence >= 0.95:
        return True

    # Critère 2: Convergence (aucun changement)
    if previous and len(current.changes_made) == 0:
        return True

    # Critère 3: Pas de nouvelles entités à explorer
    if previous and current.entities_discovered == previous.entities_discovered:
        if current.confidence >= 0.90:
            return True

    # Critère 4: Max passes atteint
    if current.pass_number >= 5:
        return True

    # Critère 5: Action simple et confiance acceptable
    if current.action in ["archive", "rien"] and current.confidence >= 0.85:
        return True

    return False
```

### 2.3 Sélection du Modèle

```python
def select_model(
    pass_number: int,
    confidence: float,
    context: AnalysisContext
) -> tuple[AIModel, str]:
    """Sélectionne le modèle pour la passe suivante"""

    # Pass 1-3: Toujours Haiku (économique, suffisant avec contexte)
    if pass_number <= 3:
        return AIModel.HAIKU, "default"

    # Pass 4: Sonnet si Haiku n'a pas convergé
    if pass_number == 4:
        if confidence < 0.80:
            return AIModel.SONNET, "low_confidence"
        # Encore une chance à Haiku si proche
        if confidence < 0.90:
            return AIModel.HAIKU, "retry"
        return AIModel.HAIKU, "confident"

    # Pass 5: Opus pour les cas difficiles
    if pass_number == 5:
        # Toujours Opus si on arrive ici
        if confidence < 0.75:
            return AIModel.OPUS, "very_low_confidence"
        if context.has_conflicting_info:
            return AIModel.OPUS, "conflict_resolution"
        if context.high_stakes:
            return AIModel.OPUS, "high_stakes"
        return AIModel.SONNET, "fallback"

    # Sécurité
    return AIModel.OPUS, "max_passes"
```

### 2.4 Détection High-Stakes

```python
def is_high_stakes(extraction: Extraction, context: AnalysisContext) -> bool:
    """Détermine si une extraction est à fort enjeu"""

    # Montant financier important
    if extraction.type == "montant":
        amount = parse_amount(extraction.info)
        if amount and amount > 10000:  # > 10k€
            return True

    # Deadline critique (< 48h)
    if extraction.type in ["deadline", "engagement"]:
        if extraction.date:
            days_until = (parse_date(extraction.date) - date.today()).days
            if days_until <= 2:
                return True

    # Décision stratégique
    if extraction.type == "decision" and extraction.importance == "haute":
        return True

    # Expéditeur VIP
    if context.sender_importance == "vip":
        return True

    return False
```

---

## 3. Modèles de Données

### 3.1 Structures Principales

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class AIModel(Enum):
    HAIKU = "claude-3-5-haiku-20241022"
    SONNET = "claude-3-5-sonnet-20241022"
    OPUS = "claude-3-opus-20240229"

class PassType(Enum):
    BLIND_EXTRACTION = "blind"      # Pass 1
    CONTEXTUAL_REFINEMENT = "refine" # Pass 2-3
    DEEP_REASONING = "deep"          # Pass 4 (Sonnet)
    EXPERT_ANALYSIS = "expert"       # Pass 5 (Opus)

@dataclass
class ContextBundle:
    """Contexte récupéré entre les passes"""
    notes: list[NoteContext]           # Notes PKM pertinentes
    calendar_events: list[EventContext] # Événements liés
    omnifocus_tasks: list[TaskContext]  # Tâches existantes
    email_history: list[EmailContext]   # Échanges précédents
    conflicts: list[ConflictInfo]       # Conflits détectés

@dataclass
class NoteContext:
    note_id: str
    title: str
    note_type: str  # personne, projet, entreprise...
    summary: str
    relevance_score: float

@dataclass
class ConflictInfo:
    conflict_type: str  # "calendar_overlap", "duplicate_info", "ambiguous_entity"
    description: str
    options: list[str]

@dataclass
class MultiPassResult:
    """Résultat final après toutes les passes"""
    final_extractions: list[Extraction]
    final_action: str
    final_confidence: float

    # Traçabilité
    passes: list[PassResult]
    total_passes: int
    models_used: list[str]
    escalation_reasons: list[str]

    # Métriques
    total_tokens: int
    total_duration_ms: float
    estimated_cost: float

    # Clarification si besoin
    needs_clarification: bool
    clarification_question: Optional[str]
```

### 3.2 Configuration

```python
@dataclass
class MultiPassConfig:
    """Configuration du pipeline multi-pass"""

    # Seuils de confiance
    confidence_stop_threshold: float = 0.95      # Arrêt si atteint
    confidence_acceptable: float = 0.90          # Acceptable pour application
    confidence_escalate_sonnet: float = 0.80     # Escalade vers Sonnet
    confidence_escalate_opus: float = 0.75       # Escalade vers Opus
    confidence_minimum: float = 0.85             # Minimum pour application auto

    # Limites
    max_passes: int = 5
    max_context_notes: int = 5
    max_calendar_events: int = 10
    max_email_history: int = 5

    # Optimisations
    skip_context_for_simple: bool = True         # Skip si newsletter/spam
    skip_pass2_if_confident: bool = True         # Skip si Pass 1 > 95%

    # High-stakes
    high_stakes_amount_threshold: float = 10000  # €
    high_stakes_deadline_days: int = 2           # jours

    # Coûts (pour monitoring)
    cost_haiku_per_1k: float = 0.00025
    cost_sonnet_per_1k: float = 0.003
    cost_opus_per_1k: float = 0.015
```

---

## 4. Prompts par Pass

### 4.1 Pass 1: Extraction Aveugle

```jinja2
{# templates/ai/v2/pass1_blind_extraction.j2 #}

Tu es Scapin, assistant personnel de Johan. Analyse cet email et extrais les informations importantes.

## INSTRUCTIONS

Extrais TOUTES les informations pertinentes de cet email:
- Faits, décisions, engagements
- Personnes mentionnées
- Dates, deadlines, événements
- Montants, références
- Actions demandées à Johan

IMPORTANT: Tu n'as PAS de contexte sur les personnes/projets mentionnés. Fais de ton mieux pour identifier les entités.

## EMAIL À ANALYSER

De: {{ event.sender }}
Objet: {{ event.subject }}
Date: {{ event.date }}

{{ event.content[:max_content_chars] }}

## FORMAT DE RÉPONSE

Réponds en JSON:
```json
{
  "extractions": [
    {
      "info": "Description concise",
      "type": "fait|decision|engagement|deadline|evenement|relation|coordonnees|montant|reference|demande|citation|objectif|competence|preference",
      "importance": "haute|moyenne|basse",
      "note_cible": "Nom de la personne/projet (best guess)",
      "note_action": "enrichir|creer",
      "omnifocus": true/false,
      "calendar": true/false,
      "date": "YYYY-MM-DD ou null",
      "time": "HH:MM ou null",
      "timezone": "HF|HM|Maurice|UTC|Paris ou null",
      "duration": minutes ou null
    }
  ],
  "action": "archive|flag|queue|delete|rien",
  "confidence": 0.0-1.0,
  "entities_mentioned": ["Liste", "des", "entités", "pour", "recherche"],
  "raisonnement": "Explication courte"
}
```
```

### 4.2 Pass 2+: Raffinement Contextuel

```jinja2
{# templates/ai/v2/pass2_contextual_refinement.j2 #}

Tu es Scapin. Raffine cette analyse avec le contexte fourni.

## EXTRACTION INITIALE (Pass {{ previous_pass }})

```json
{{ previous_result | tojson(indent=2) }}
```

## CONTEXTE TROUVÉ

{% if context.notes %}
### Notes PKM existantes
{% for note in context.notes[:5] %}
- **{{ note.title }}** ({{ note.note_type }}): {{ note.summary[:200] }}
{% endfor %}
{% endif %}

{% if context.calendar_events %}
### Événements Calendar
{% for event in context.calendar_events[:5] %}
- {{ event.date }} {{ event.time }}: {{ event.title }} ({{ event.participants | join(", ") }})
{% endfor %}
{% endif %}

{% if context.omnifocus_tasks %}
### Tâches OmniFocus existantes
{% for task in context.omnifocus_tasks[:5] %}
- {{ task.title }} (due: {{ task.due_date }}, projet: {{ task.project }})
{% endfor %}
{% endif %}

{% if context.conflicts %}
### Conflits détectés
{% for conflict in context.conflicts %}
- ⚠️ {{ conflict.conflict_type }}: {{ conflict.description }}
{% endfor %}
{% endif %}

## INSTRUCTIONS

Avec ce contexte, tu peux maintenant:
1. **Corriger** les note_cible avec les titres exacts des notes existantes
2. **Détecter** les doublons (info déjà présente dans une note)
3. **Enrichir** les extractions avec le contexte (rôle des personnes, etc.)
4. **Ajuster** les actions (skip omnifocus si tâche existe déjà)
5. **Résoudre** les conflits détectés

## FORMAT DE RÉPONSE

```json
{
  "extractions": [...],  // Corrigées et enrichies
  "action": "...",
  "confidence": 0.0-1.0,  // Devrait augmenter avec le contexte
  "changes_made": [
    "note_cible 'Marc' → 'Marc Dupont'",
    "omnifocus désactivé: tâche existe",
    ...
  ],
  "new_entities_discovered": ["Sophie Martin", ...],
  "raisonnement": "..."
}
```
```

### 4.3 Pass 4-5: Raisonnement Profond

```jinja2
{# templates/ai/v2/pass4_deep_reasoning.j2 #}

Tu es Scapin utilisant ton raisonnement le plus profond.

## HISTORIQUE DES PASSES

{% for pass in passes %}
### Pass {{ pass.pass_number }} ({{ pass.model_used }}, confidence: {{ pass.confidence }})
{{ pass.reasoning }}
{% if pass.changes_made %}
Changements: {{ pass.changes_made | join(", ") }}
{% endif %}
{% endfor %}

## PROBLÈMES NON RÉSOLUS

{% for issue in unresolved_issues %}
- {{ issue }}
{% endfor %}

## CONTEXTE COMPLET

{{ full_context }}

## INSTRUCTIONS

Utilise ton raisonnement expert pour:
1. Résoudre les ambiguïtés restantes
2. Prendre une décision sur les conflits
3. Si vraiment impossible: formuler une question claire pour Johan

Tu dois atteindre une confidence >= 90% ou expliquer pourquoi c'est impossible.

## FORMAT DE RÉPONSE

```json
{
  "extractions": [...],
  "action": "...",
  "confidence": 0.0-1.0,
  "resolution_reasoning": "Explication détaillée de ton raisonnement",
  "needs_clarification": true/false,
  "clarification_question": "Question pour Johan si besoin"
}
```
```

---

## 5. Estimation des Coûts

### 5.1 Distribution des Passes

| Chemin | % emails | Description |
|--------|----------|-------------|
| Pass 1 seul | 15% | Newsletters, spam, très simple |
| Pass 1-2 | 70% | Emails standards |
| Pass 1-3 | 10% | Nouvelles entités, contexte élargi |
| Pass 1-4 (Sonnet) | 4% | Ambiguïtés complexes |
| Pass 1-5 (Opus) | 1% | Cas vraiment difficiles |

### 5.2 Coût Mensuel Estimé

Base: 460 emails/jour × 30 jours = 13,800 emails/mois

| Chemin | Emails | Coût/email | Total |
|--------|--------|------------|-------|
| Pass 1 | 2,070 | $0.0013 | $2.69 |
| Pass 1-2 | 9,660 | $0.0028 | $27.05 |
| Pass 1-3 | 1,380 | $0.0043 | $5.93 |
| Pass 1-4 | 552 | $0.019 | $10.49 |
| Pass 1-5 | 138 | $0.094 | $12.97 |
| **TOTAL** | 13,800 | ~$0.0043 | **~$59/mois** |

### 5.3 Comparaison

| Approche | Coût/mois | Qualité |
|----------|-----------|---------|
| v2.1 (1 pass + escalade) | ~$38 | Variable |
| v2.2 (multi-pass) | ~$59 | Excellente |
| Différence | +$21 | +50% qualité estimée |

---

## 6. Plan d'Implémentation

### 6.1 Fichiers à Créer/Modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `src/sancho/multi_pass_analyzer.py` | Créer | Orchestrateur multi-pass |
| `src/sancho/pass_executor.py` | Créer | Exécution d'une passe |
| `src/sancho/context_searcher.py` | Créer | Recherche contextuelle entre passes |
| `src/sancho/convergence.py` | Créer | Logique de convergence |
| `src/sancho/model_selector.py` | Modifier | Ajout escalade Opus |
| `src/core/models/v2_models.py` | Modifier | Nouveaux modèles |
| `src/core/config_manager.py` | Modifier | MultiPassConfig |
| `templates/ai/v2/pass1_*.j2` | Créer | Prompt Pass 1 |
| `templates/ai/v2/pass2_*.j2` | Créer | Prompt Pass 2+ |
| `templates/ai/v2/pass4_*.j2` | Créer | Prompt Sonnet/Opus |

### 6.2 Estimation Effort

| Composant | Lignes estimées | Jours |
|-----------|-----------------|-------|
| multi_pass_analyzer.py | ~400 | 1 |
| pass_executor.py | ~200 | 0.5 |
| context_searcher.py | ~300 | 1 |
| convergence.py | ~150 | 0.5 |
| Templates (3) | ~300 | 0.5 |
| Tests unitaires | ~500 | 1 |
| Tests intégration | ~200 | 0.5 |
| **TOTAL** | ~2050 | **5 jours** |

---

## 7. Métriques et Monitoring

### 7.1 Métriques à Tracker

```python
@dataclass
class MultiPassMetrics:
    """Métriques pour monitoring"""

    # Distribution
    emails_pass_1_only: int
    emails_pass_2: int
    emails_pass_3: int
    emails_pass_4_sonnet: int
    emails_pass_5_opus: int

    # Confiance
    avg_confidence_pass_1: float
    avg_confidence_final: float
    confidence_improvement: float

    # Coûts
    total_cost: float
    avg_cost_per_email: float
    cost_by_model: dict[str, float]

    # Performance
    avg_passes_per_email: float
    avg_duration_ms: float

    # Qualité
    clarifications_needed: int
    user_corrections: int
```

### 7.2 Alertes

| Alerte | Seuil | Action |
|--------|-------|--------|
| Coût journalier | > $3 | Notification |
| % Opus | > 3% | Investiguer |
| Clarifications | > 5/jour | Ajuster seuils |
| Confiance moyenne | < 85% | Revoir prompts |

---

## 8. Migration

### 8.1 Feature Flag

```python
# config/processing.yaml
processing:
  multi_pass:
    enabled: true  # false = v2.1, true = v2.2
    rollout_percentage: 100  # Pour rollout progressif
```

### 8.2 Rollback

Si problèmes détectés:
1. `multi_pass.enabled: false` → retour à v2.1
2. Les emails en cours continuent avec leur pipeline
3. Nouveaux emails utilisent v2.1

---

## 9. Critères de Succès

| Critère | Objectif | Mesure |
|---------|----------|--------|
| Confiance moyenne | > 92% | avg(final_confidence) |
| Clarifications | < 2% | clarifications / total |
| Coût mensuel | < $70 | sum(costs) |
| Latence P95 | < 5s | percentile(duration, 95) |
| Extractions correctes | > 95% | user_feedback |

---

**Statut** : Prêt pour implémentation
**Prochaine étape** : Sprint 7 - Multi-Pass Implementation
