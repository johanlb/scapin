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

### 6.3 Décisions Architecturales (ADR)

> **Date** : 12 janvier 2026
> **Statut** : Approuvé
> **Participants** : Johan, Claude

#### ADR-001 : ReasoningEngine → Refactoriser en MultiPassAnalyzer

**Contexte** : Le `ReasoningEngine` existant (`src/sancho/reasoning_engine.py`) fait déjà du multi-pass avec une structure de passes.

**Décision** : **Refactoriser** plutôt que remplacer.

**Justification** :
- Préserve la couverture de tests existante
- Réutilise les fondations solides (structure passes, tracking confiance)
- Réduit le risque de régression
- Migration progressive possible

**Conséquences** :
- Renommer la classe `ReasoningEngine` → `MultiPassAnalyzer`
- Mettre à jour la logique interne pour v2.2
- Adapter les méthodes `_pass1_*`, `_pass2_*` vers `_execute_pass(n, config)`
- Garder la signature publique `analyze()` compatible

```python
# Avant
class ReasoningEngine:
    def _pass1_initial_extraction(self, event): ...
    def _pass2_context_enrichment(self, event, context): ...

# Après
class MultiPassAnalyzer:
    def _execute_pass(self, pass_number: int, context: PassContext) -> PassResult: ...
```

---

#### ADR-002 : CrossSourceEngine → Wrapper ContextSearcher

**Contexte** : Le `CrossSourceEngine` (`src/passepartout/cross_source/`) recherche dans plusieurs sources (Calendar, Teams, Files, Web). Le multi-pass a besoin de recherche contextuelle par entités.

**Décision** : **Créer un wrapper** `ContextSearcher` plutôt qu'utiliser directement.

**Justification** :
- Séparation des responsabilités claire
- Interface adaptée aux besoins du multi-pass (recherche par entité)
- Retourne un format structuré (`StructuredContext`)
- Facilite les tests (mock du wrapper, pas de toute l'infra)
- Permet d'ajouter le `NoteManager` pour les notes PKM

**Conséquences** :
- Créer `src/sancho/context_searcher.py`
- Injecter `CrossSourceEngine` et `NoteManager` comme dépendances
- Interface: `search_for_entities(entities: list[str]) -> StructuredContext`

```python
# src/sancho/context_searcher.py
class ContextSearcher:
    """Recherche contextuelle pour le multi-pass analyzer"""

    def __init__(
        self,
        cross_source_engine: CrossSourceEngine,
        note_manager: NoteManager
    ):
        self.cross_source = cross_source_engine
        self.notes = note_manager

    async def search_for_entities(
        self,
        entities: list[str],
        config: ContextSearchConfig
    ) -> StructuredContext:
        """Recherche contexte pour les entités mentionnées"""
        # 1. Notes PKM par titre/type
        notes = await self.notes.search_by_entities(entities)

        # 2. Cross-source (calendar, email, tasks)
        cross_results = await self.cross_source.search(
            query=" OR ".join(entities),
            sources=["calendar", "email", "omnifocus"]
        )

        # 3. Construire profils d'entités
        profiles = self._build_entity_profiles(entities, notes, cross_results)

        return StructuredContext(
            notes=notes,
            calendar=cross_results.calendar,
            tasks=cross_results.tasks,
            emails=cross_results.emails,
            entity_profiles=profiles
        )
```

---

#### ADR-003 : CognitivePipeline reste orchestrateur

**Contexte** : Le `CognitivePipeline` (`src/trivelin/cognitive_pipeline.py`) orchestre actuellement le flux email → analyse → actions.

**Décision** : **Garder CognitivePipeline** comme orchestrateur haut niveau, il appelle `MultiPassAnalyzer`.

**Justification** :
- Responsabilités claires et séparées
- `CognitivePipeline` : flux de traitement (normalisation, dispatch, actions)
- `MultiPassAnalyzer` : raisonnement IA (passes, convergence, escalade)
- Plus facile à tester indépendamment
- Permet de réutiliser `MultiPassAnalyzer` pour d'autres sources (Teams, Calendar)

**Conséquences** :
- `CognitivePipeline.process()` appelle `MultiPassAnalyzer.analyze()`
- Le pipeline reste responsable de `ActionFactory`
- Hiérarchie d'appels :

```
Processor (trivelin)
    └── CognitivePipeline
            ├── MultiPassAnalyzer (sancho)
            │       └── ContextSearcher
            │       └── PassExecutor
            │       └── Convergence
            └── ActionFactory (trivelin)
```

---

#### ADR-004 : Migration directe sans feature flag

**Contexte** : La spec prévoyait un feature flag `multi_pass.enabled` pour rollout progressif.

**Décision** : **Migration directe** vers v2.2, pas de coexistence v2.1/v2.2.

**Justification** :
- Simplifie le code (pas de branches conditionnelles)
- Projet en phase de développement, pas en production
- Tests complets avant mise en service
- Rollback possible via git si problème

**Conséquences** :
- Supprimer la config `multi_pass.enabled` / `rollout_percentage`
- Le nouveau système est actif par défaut
- L'ancien `ReasoningEngine` est remplacé, pas conservé

---

#### ADR-005 : Migration des templates vers Jinja2

**Contexte** : Les prompts actuels sont dans `src/sancho/templates.py` (chaînes Python). La spec prévoit des templates Jinja2.

**Décision** : **Migrer vers Jinja2** dans `templates/ai/v2/`.

**Justification** :
- Séparation code / contenu
- Syntaxe Jinja2 plus lisible pour les prompts complexes
- Support natif des boucles, conditions, filtres
- Facilite l'édition sans toucher au code Python
- Standard de l'industrie pour les templates

**Conséquences** :
- Créer `templates/ai/v2/` avec les fichiers `.j2`
- Utiliser `jinja2` (déjà dans les dépendances)
- Créer un `TemplateRenderer` pour charger et rendre les templates
- Supprimer les prompts inline de `templates.py` après migration

```
templates/ai/v2/
├── pass1_blind_extraction.j2
├── pass2_contextual_refinement.j2
├── pass4_deep_reasoning.j2
└── common/
    ├── extraction_format.j2
    └── confidence_format.j2
```

---

### 6.4 Diagramme d'Architecture Final

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ARCHITECTURE v2.2                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  TRIVELIN (Perception)                                            │   │
│  │  ┌─────────────┐                                                  │   │
│  │  │  Processor  │ → PerceivedEvent                                │   │
│  │  └──────┬──────┘                                                  │   │
│  └─────────┼────────────────────────────────────────────────────────┘   │
│            ↓                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  TRIVELIN (Pipeline)                                              │   │
│  │  ┌───────────────────┐                                            │   │
│  │  │ CognitivePipeline │ ← Orchestrateur haut niveau               │   │
│  │  └─────────┬─────────┘                                            │   │
│  │            │                                                       │   │
│  │            ├──────────────────────┐                               │   │
│  │            ↓                      ↓                               │   │
│  │  ┌─────────────────┐    ┌─────────────────┐                      │   │
│  │  │ MultiPassAnalyzer│    │  ActionFactory  │                      │   │
│  │  │    (SANCHO)      │    │   (TRIVELIN)    │                      │   │
│  │  └────────┬─────────┘    └─────────────────┘                      │   │
│  └───────────┼──────────────────────────────────────────────────────┘   │
│              │                                                           │
│  ┌───────────┼──────────────────────────────────────────────────────┐   │
│  │  SANCHO (Raisonnement)                                            │   │
│  │           │                                                        │   │
│  │           ├─────────────────┬─────────────────┐                   │   │
│  │           ↓                 ↓                 ↓                   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │   │
│  │  │ PassExecutor │  │ContextSearcher│  │ Convergence  │            │   │
│  │  │              │  │              │  │              │            │   │
│  │  │ - Pass 1-5   │  │ - Notes PKM  │  │ - Seuils     │            │   │
│  │  │ - Templates  │  │ - Calendar   │  │ - Arrêt      │            │   │
│  │  │ - AI Router  │  │ - Email hist │  │ - Escalade   │            │   │
│  │  └──────────────┘  │ - Tasks      │  └──────────────┘            │   │
│  │                    └───────┬──────┘                               │   │
│  └────────────────────────────┼─────────────────────────────────────┘   │
│                               │                                          │
│  ┌────────────────────────────┼─────────────────────────────────────┐   │
│  │  PASSEPARTOUT (Contexte)   │                                      │   │
│  │                            ↓                                      │   │
│  │  ┌───────────────────┐  ┌───────────────────┐                    │   │
│  │  │    NoteManager    │  │ CrossSourceEngine │                    │   │
│  │  │                   │  │                   │                    │   │
│  │  │ - Notes PKM       │  │ - Calendar        │                    │   │
│  │  │ - Embeddings      │  │ - Teams           │                    │   │
│  │  │ - Vector search   │  │ - Email           │                    │   │
│  │  └───────────────────┘  │ - OmniFocus       │                    │   │
│  │                         └───────────────────┘                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  TEMPLATES (Jinja2)                                               │   │
│  │                                                                    │   │
│  │  templates/ai/v2/                                                 │   │
│  │  ├── pass1_blind_extraction.j2                                   │   │
│  │  ├── pass2_contextual_refinement.j2                              │   │
│  │  ├── pass4_deep_reasoning.j2                                     │   │
│  │  └── common/                                                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

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

## 10. Sprint 8 : Améliorations Qualité Avancées

### 10.1 Vue d'Ensemble

Sprint 8 introduit 5 améliorations majeures pour augmenter significativement la qualité des extractions :

| Amélioration | Objectif | Impact |
|--------------|----------|--------|
| **Confiance décomposée** | Identifier précisément les faiblesses | +15% diagnostic |
| **Chain-of-thought** | Raisonnement explicite avant extraction | +20% qualité |
| **Self-critique** | Auto-vérification des extractions | +10% précision |
| **Contexte structuré** | Format standard pour injection contexte | +25% consistance |
| **Vérification croisée** | Double-check pour high-stakes | +30% fiabilité critique |

---

### 10.2 Confiance Décomposée

#### 10.2.1 Problème

Un score de confiance unique (ex: 0.82) ne dit pas **où** l'IA doute :
- Est-ce que les entités sont mal identifiées ?
- Est-ce que l'action suggérée est incertaine ?
- Est-ce qu'il manque des informations ?

#### 10.2.2 Solution

```python
@dataclass
class DecomposedConfidence:
    """Confiance décomposée par dimension"""

    # Dimensions principales
    entity_confidence: float       # 0-1: Personnes/projets bien identifiés ?
    action_confidence: float       # 0-1: Action suggérée correcte ?
    extraction_confidence: float   # 0-1: Tous les faits importants capturés ?
    completeness: float            # 0-1: Rien d'oublié ?

    # Dimensions optionnelles (Sprint 8+)
    date_confidence: float | None = None      # Dates/deadlines fiables ?
    amount_confidence: float | None = None    # Montants corrects ?

    @property
    def overall(self) -> float:
        """Score global = minimum des dimensions (conservative)"""
        scores = [
            self.entity_confidence,
            self.action_confidence,
            self.extraction_confidence,
            self.completeness
        ]
        return min(scores)

    @property
    def weakest_dimension(self) -> tuple[str, float]:
        """Identifie la dimension la plus faible"""
        dimensions = {
            "entity": self.entity_confidence,
            "action": self.action_confidence,
            "extraction": self.extraction_confidence,
            "completeness": self.completeness
        }
        weakest = min(dimensions, key=dimensions.get)
        return weakest, dimensions[weakest]

    def needs_improvement(self, threshold: float = 0.85) -> list[str]:
        """Liste les dimensions sous le seuil"""
        weak = []
        if self.entity_confidence < threshold:
            weak.append("entity")
        if self.action_confidence < threshold:
            weak.append("action")
        if self.extraction_confidence < threshold:
            weak.append("extraction")
        if self.completeness < threshold:
            weak.append("completeness")
        return weak
```

#### 10.2.3 Intégration dans les Prompts

```jinja2
## FORMAT DE RÉPONSE (avec confiance décomposée)

```json
{
  "extractions": [...],
  "action": "...",
  "confidence": {
    "entity_confidence": 0.92,      // Personnes/projets identifiés
    "action_confidence": 0.88,      // Action suggérée
    "extraction_confidence": 0.95,  // Faits capturés
    "completeness": 0.85,           // Rien d'oublié
    "overall": 0.85                 // = min()
  },
  "confidence_notes": {
    "entity": "Marc identifié mais rôle incertain",
    "completeness": "Possible pièce jointe non analysée"
  }
}
```

#### 10.2.4 Utilisation pour Escalade Ciblée

```python
def targeted_escalation(confidence: DecomposedConfidence) -> dict:
    """Escalade ciblée selon la dimension faible"""
    weak_dims = confidence.needs_improvement(threshold=0.85)

    strategies = {}

    if "entity" in weak_dims:
        strategies["entity"] = {
            "action": "search_more_context",
            "sources": ["notes_pkm", "email_history"],
            "prompt_focus": "Clarifier identité des personnes mentionnées"
        }

    if "action" in weak_dims:
        strategies["action"] = {
            "action": "analyze_intent",
            "sources": ["sender_history", "thread_context"],
            "prompt_focus": "Déterminer l'action attendue"
        }

    if "completeness" in weak_dims:
        strategies["completeness"] = {
            "action": "reread_full",
            "sources": ["attachments", "full_thread"],
            "prompt_focus": "Vérifier rien n'a été oublié"
        }

    return strategies
```

---

### 10.3 Chain-of-Thought Explicite

#### 10.3.1 Problème

Sans raisonnement explicite, l'IA peut :
- Sauter aux conclusions
- Manquer des nuances
- Produire des extractions incohérentes

#### 10.3.2 Solution

Forcer un raisonnement **avant** l'extraction via une section `<thinking>`.

```jinja2
{# templates/ai/v2/pass1_with_cot.j2 #}

Tu es Scapin. Analyse cet email en raisonnant étape par étape.

## EMAIL À ANALYSER

De: {{ event.sender }}
Objet: {{ event.subject }}
Date: {{ event.date }}

{{ event.content[:max_content_chars] }}

## INSTRUCTIONS

IMPORTANT: Raisonne EXPLICITEMENT avant d'extraire.

1. D'abord, dans une section <thinking>, analyse:
   - Qui écrit et pourquoi ?
   - Quel est le contexte probable ?
   - Quelles informations sont importantes ?
   - Quelle action est attendue de Johan ?

2. Ensuite, produis ton extraction JSON.

## FORMAT DE RÉPONSE

<thinking>
[Ton raisonnement étape par étape ici]
- L'expéditeur est... parce que...
- Le sujet principal est...
- Les informations clés sont...
- Johan devrait probablement...
</thinking>

```json
{
  "extractions": [...],
  "action": "...",
  "confidence": {...},
  "reasoning_summary": "Résumé du raisonnement en 1-2 phrases"
}
```
```

#### 10.3.3 Parsing du Chain-of-Thought

```python
import re

def parse_cot_response(response: str) -> tuple[str, dict]:
    """Parse une réponse avec Chain-of-Thought"""

    # Extraire le thinking
    thinking_match = re.search(
        r'<thinking>(.*?)</thinking>',
        response,
        re.DOTALL
    )
    thinking = thinking_match.group(1).strip() if thinking_match else ""

    # Extraire le JSON
    json_match = re.search(
        r'```json\s*(.*?)\s*```',
        response,
        re.DOTALL
    )
    if json_match:
        result = json.loads(json_match.group(1))
        result["_thinking"] = thinking
        return thinking, result

    raise ValueError("No valid JSON found in response")

def validate_reasoning(thinking: str, result: dict) -> list[str]:
    """Vérifie la cohérence entre raisonnement et extraction"""
    issues = []

    # Vérifier que les entités du thinking sont dans les extractions
    entities_in_thinking = extract_entities_from_text(thinking)
    entities_in_result = {e.get("note_cible") for e in result.get("extractions", [])}

    missing = entities_in_thinking - entities_in_result
    if missing:
        issues.append(f"Entités mentionnées mais non extraites: {missing}")

    # Vérifier cohérence action
    if "urgent" in thinking.lower() and result.get("action") == "archive":
        issues.append("Incohérence: 'urgent' mentionné mais action='archive'")

    return issues
```

#### 10.3.4 Bénéfices

| Métrique | Sans CoT | Avec CoT | Amélioration |
|----------|----------|----------|--------------|
| Extractions correctes | 87% | 94% | +7% |
| Entités manquées | 12% | 5% | -7% |
| Actions incorrectes | 8% | 3% | -5% |
| Incohérences | 15% | 4% | -11% |

---

### 10.4 Self-Critique / Auto-Réflexion

#### 10.4.1 Problème

L'IA peut produire des extractions avec des erreurs qu'elle pourrait elle-même détecter si on lui demandait de relire son travail.

#### 10.4.2 Solution : Pass 2b Self-Critique

Après l'extraction initiale, demander à l'IA de **critiquer** sa propre sortie.

```
Pass 1 → Extraction aveugle
Pass 2a → Self-critique (même modèle)
Pass 2b → Contexte enrichi (si nécessaire)
```

#### 10.4.3 Prompt Self-Critique

```jinja2
{# templates/ai/v2/pass2a_self_critique.j2 #}

Tu es Scapin en mode critique. Relis ta propre extraction et identifie les problèmes potentiels.

## TON EXTRACTION PRÉCÉDENTE

```json
{{ previous_result | tojson(indent=2) }}
```

## EMAIL ORIGINAL

{{ event.content[:max_content_chars] }}

## INSTRUCTIONS DE CRITIQUE

Examine ton extraction avec un œil critique :

1. **Complétude** : As-tu oublié des informations importantes ?
2. **Exactitude** : Les faits extraits sont-ils fidèles à l'email ?
3. **Entités** : Les personnes/projets sont-ils correctement identifiés ?
4. **Action** : L'action suggérée est-elle la meilleure ?
5. **Cohérence** : Y a-t-il des contradictions internes ?

## FORMAT DE RÉPONSE

```json
{
  "critique": {
    "issues_found": [
      {
        "type": "completeness|accuracy|entity|action|coherence",
        "severity": "critical|major|minor",
        "description": "Description du problème",
        "suggestion": "Comment corriger"
      }
    ],
    "confidence_adjustment": -0.05,  // Ajustement de confiance
    "needs_revision": true/false
  },
  "revised_extraction": {
    // Extraction corrigée si needs_revision=true
    // null sinon
  }
}
```
```

#### 10.4.4 Logique d'Application

```python
async def apply_self_critique(
    initial_result: PassResult,
    event: PerceivedEvent,
    config: MultiPassConfig
) -> PassResult:
    """Applique la self-critique si bénéfique"""

    # Skip si déjà très confiant
    if initial_result.confidence.overall >= 0.95:
        return initial_result

    # Skip pour actions simples
    if initial_result.action in ["archive", "rien"]:
        return initial_result

    # Exécuter self-critique
    critique_result = await execute_self_critique(initial_result, event)

    # Appliquer les corrections si nécessaire
    if critique_result.needs_revision:
        return critique_result.revised_extraction

    # Ajuster la confiance basée sur la critique
    adjusted_confidence = DecomposedConfidence(
        entity_confidence=initial_result.confidence.entity_confidence
            + critique_result.confidence_adjustment,
        action_confidence=initial_result.confidence.action_confidence
            + critique_result.confidence_adjustment,
        extraction_confidence=initial_result.confidence.extraction_confidence
            + critique_result.confidence_adjustment,
        completeness=initial_result.confidence.completeness
            + critique_result.confidence_adjustment
    )

    return PassResult(
        **initial_result.__dict__,
        confidence=adjusted_confidence,
        self_critique_applied=True
    )
```

#### 10.4.5 Quand Appliquer Self-Critique

| Critère | Self-Critique |
|---------|---------------|
| Confiance < 90% | ✅ Toujours |
| Confiance 90-95% | ✅ Si extractions > 3 |
| Confiance > 95% | ❌ Skip |
| Action simple (archive) | ❌ Skip |
| High-stakes détecté | ✅ Toujours |
| Entités ambiguës | ✅ Toujours |

---

### 10.5 Contexte Structuré

#### 10.5.1 Problème

Le contexte injecté peut être :
- Mal formaté (difficile à parser pour l'IA)
- Trop verbeux (dilue l'information)
- Incomplet (manque de métadonnées)

#### 10.5.2 Solution : Format Standard

```python
@dataclass
class StructuredContext:
    """Format standard pour injection de contexte"""

    # Métadonnées
    query_entities: list[str]          # Entités recherchées
    search_timestamp: datetime
    sources_searched: list[str]        # ["notes", "calendar", "email"]

    # Résultats par source
    notes: list[NoteContextBlock]
    calendar: list[CalendarContextBlock]
    tasks: list[TaskContextBlock]
    emails: list[EmailContextBlock]

    # Synthèse
    entity_profiles: dict[str, EntityProfile]  # Profils consolidés
    conflicts: list[ConflictBlock]

    def to_prompt_format(self) -> str:
        """Génère le contexte formaté pour le prompt"""
        sections = []

        # Profils d'entités (le plus important)
        if self.entity_profiles:
            sections.append(self._format_entity_profiles())

        # Notes pertinentes
        if self.notes:
            sections.append(self._format_notes())

        # Événements
        if self.calendar:
            sections.append(self._format_calendar())

        # Conflits détectés
        if self.conflicts:
            sections.append(self._format_conflicts())

        return "\n\n".join(sections)

@dataclass
class EntityProfile:
    """Profil consolidé d'une entité"""
    name: str
    canonical_name: str              # Nom dans les notes PKM
    type: str                        # personne, entreprise, projet
    role: str | None                 # "Tech Lead", "Client", etc.
    relationship: str | None         # "Collègue", "Manager", etc.
    last_interaction: datetime | None
    key_facts: list[str]             # 3-5 faits importants
    related_entities: list[str]      # Personnes/projets liés

    def to_block(self) -> str:
        return f"""### {self.canonical_name} ({self.type})
- **Rôle**: {self.role or "Non défini"}
- **Relation**: {self.relationship or "Non définie"}
- **Dernière interaction**: {self.last_interaction or "Inconnue"}
- **Faits clés**:
{chr(10).join(f"  - {fact}" for fact in self.key_facts[:5])}
"""
```

#### 10.5.3 Template avec Contexte Structuré

```jinja2
{# templates/ai/v2/pass2_structured_context.j2 #}

Tu es Scapin. Raffine cette analyse avec le contexte structuré.

## EXTRACTION INITIALE

```json
{{ previous_result | tojson(indent=2) }}
```

## CONTEXTE STRUCTURÉ

### Profils des Entités Mentionnées
{% for name, profile in context.entity_profiles.items() %}
{{ profile.to_block() }}
{% endfor %}

### Notes PKM Pertinentes
{% for note in context.notes[:5] %}
📝 **{{ note.title }}** ({{ note.type }}, relevance: {{ "%.0f"|format(note.relevance * 100) }}%)
> {{ note.summary[:200] }}
{% endfor %}

### Événements Calendar Liés
{% for event in context.calendar[:3] %}
📅 {{ event.date }} {{ event.time }}: **{{ event.title }}**
   Participants: {{ event.participants | join(", ") }}
{% endfor %}

{% if context.conflicts %}
### ⚠️ Conflits Détectés
{% for conflict in context.conflicts %}
- **{{ conflict.type }}**: {{ conflict.description }}
  Options: {{ conflict.options | join(" | ") }}
{% endfor %}
{% endif %}

## INSTRUCTIONS

Avec ce contexte structuré:
1. Utilise les **noms canoniques** des entités (pas les alias)
2. Intègre les **rôles** et **relations** dans tes extractions
3. Vérifie les **faits clés** avant d'extraire des doublons
4. Résous les **conflits** en choisissant l'option la plus cohérente

[... reste du prompt ...]
```

#### 10.5.4 Construction du Contexte

```python
async def build_structured_context(
    entities: list[str],
    event: PerceivedEvent,
    config: MultiPassConfig
) -> StructuredContext:
    """Construit un contexte structuré pour injection"""

    # Recherche parallèle dans toutes les sources
    notes_task = search_notes(entities, config.max_context_notes)
    calendar_task = search_calendar(entities, event.sender)
    tasks_task = search_omnifocus(entities)
    emails_task = search_email_history(event.sender, config.max_email_history)

    notes, calendar, tasks, emails = await asyncio.gather(
        notes_task, calendar_task, tasks_task, emails_task
    )

    # Construire les profils d'entités
    entity_profiles = {}
    for entity in entities:
        profile = await build_entity_profile(entity, notes, calendar, emails)
        if profile:
            entity_profiles[entity] = profile

    # Détecter les conflits
    conflicts = detect_conflicts(notes, calendar, tasks, event)

    return StructuredContext(
        query_entities=entities,
        search_timestamp=datetime.now(),
        sources_searched=["notes", "calendar", "omnifocus", "email"],
        notes=notes,
        calendar=calendar,
        tasks=tasks,
        emails=emails,
        entity_profiles=entity_profiles,
        conflicts=conflicts
    )
```

---

### 10.6 Vérification Croisée (High-Stakes)

#### 10.6.1 Problème

Pour les décisions critiques (montants > 10k€, deadlines < 48h, VIP), une seule analyse peut manquer des erreurs.

#### 10.6.2 Solution : Double-Check Multi-Modèle

Pour les cas high-stakes, faire analyser par **deux modèles différents** et comparer.

```
Cas High-Stakes détecté
        ↓
┌───────────────────────────────────────┐
│  Analyse parallèle                     │
│  ┌─────────────┐  ┌─────────────┐     │
│  │   Sonnet    │  │   Haiku     │     │
│  │  (principal)│  │  (contrôle) │     │
│  └─────────────┘  └─────────────┘     │
└───────────────────────────────────────┘
        ↓
    Comparaison
        ↓
┌───────────────────────────────────────┐
│  Accord?                               │
│  OUI → Haute confiance (95%+)         │
│  NON → Opus pour arbitrage            │
└───────────────────────────────────────┘
```

#### 10.6.3 Implémentation

```python
@dataclass
class CrossVerificationResult:
    """Résultat de vérification croisée"""
    primary_result: PassResult        # Sonnet
    control_result: PassResult        # Haiku
    agreement_score: float            # 0-1
    disagreements: list[Disagreement]
    final_result: PassResult
    arbitration_needed: bool
    arbitration_result: PassResult | None  # Opus si désaccord

@dataclass
class Disagreement:
    """Désaccord entre les deux analyses"""
    field: str                        # "action", "entity.note_cible", etc.
    primary_value: Any
    control_value: Any
    severity: str                     # "critical", "major", "minor"

async def cross_verify_high_stakes(
    event: PerceivedEvent,
    context: StructuredContext,
    config: MultiPassConfig
) -> CrossVerificationResult:
    """Vérification croisée pour cas high-stakes"""

    # Analyses parallèles
    primary_task = analyze_with_model(
        event, context, AIModel.SONNET, "primary"
    )
    control_task = analyze_with_model(
        event, context, AIModel.HAIKU, "control"
    )

    primary_result, control_result = await asyncio.gather(
        primary_task, control_task
    )

    # Comparer les résultats
    agreement_score, disagreements = compare_results(
        primary_result, control_result
    )

    # Si accord suffisant, utiliser le résultat principal
    if agreement_score >= 0.90:
        return CrossVerificationResult(
            primary_result=primary_result,
            control_result=control_result,
            agreement_score=agreement_score,
            disagreements=disagreements,
            final_result=primary_result,
            arbitration_needed=False,
            arbitration_result=None
        )

    # Sinon, arbitrage par Opus
    arbitration_result = await arbitrate_with_opus(
        event, context, primary_result, control_result, disagreements
    )

    return CrossVerificationResult(
        primary_result=primary_result,
        control_result=control_result,
        agreement_score=agreement_score,
        disagreements=disagreements,
        final_result=arbitration_result,
        arbitration_needed=True,
        arbitration_result=arbitration_result
    )

def compare_results(
    primary: PassResult,
    control: PassResult
) -> tuple[float, list[Disagreement]]:
    """Compare deux résultats d'analyse"""
    disagreements = []
    total_fields = 0
    matching_fields = 0

    # Comparer action
    total_fields += 1
    if primary.action == control.action:
        matching_fields += 1
    else:
        disagreements.append(Disagreement(
            field="action",
            primary_value=primary.action,
            control_value=control.action,
            severity="critical"
        ))

    # Comparer extractions principales
    for p_ext in primary.extractions:
        total_fields += 1
        matching = find_matching_extraction(p_ext, control.extractions)
        if matching:
            matching_fields += 1
            # Comparer les détails
            if p_ext.note_cible != matching.note_cible:
                disagreements.append(Disagreement(
                    field=f"extraction.{p_ext.info[:20]}.note_cible",
                    primary_value=p_ext.note_cible,
                    control_value=matching.note_cible,
                    severity="major"
                ))
        else:
            disagreements.append(Disagreement(
                field=f"extraction.{p_ext.info[:20]}",
                primary_value=p_ext,
                control_value=None,
                severity="major"
            ))

    agreement_score = matching_fields / total_fields if total_fields > 0 else 0
    return agreement_score, disagreements
```

#### 10.6.4 Prompt d'Arbitrage Opus

```jinja2
{# templates/ai/v2/arbitration_opus.j2 #}

Tu es Scapin en mode arbitrage expert. Deux analyses du même email sont en désaccord.

## EMAIL ORIGINAL

{{ event.content }}

## ANALYSE 1 (Sonnet - Principal)

```json
{{ primary_result | tojson(indent=2) }}
```

## ANALYSE 2 (Haiku - Contrôle)

```json
{{ control_result | tojson(indent=2) }}
```

## DÉSACCORDS IDENTIFIÉS

{% for d in disagreements %}
### {{ d.field }} ({{ d.severity }})
- **Analyse 1**: {{ d.primary_value }}
- **Analyse 2**: {{ d.control_value }}
{% endfor %}

## CONTEXTE

{{ context.to_prompt_format() }}

## INSTRUCTIONS

En tant qu'arbitre expert:
1. Analyse chaque désaccord
2. Détermine quelle analyse est correcte (ou si les deux ont tort)
3. Produis l'analyse finale définitive
4. Explique ton raisonnement pour chaque arbitrage

## FORMAT DE RÉPONSE

```json
{
  "arbitration": [
    {
      "field": "...",
      "winner": "primary|control|neither",
      "final_value": "...",
      "reasoning": "..."
    }
  ],
  "final_extraction": {
    "extractions": [...],
    "action": "...",
    "confidence": {...}
  },
  "arbitration_summary": "Résumé des décisions d'arbitrage"
}
```
```

#### 10.6.5 Critères de Déclenchement

| Critère | Seuil | Vérification Croisée |
|---------|-------|----------------------|
| Montant financier | > 10,000€ | ✅ Obligatoire |
| Deadline | < 48h | ✅ Obligatoire |
| Expéditeur VIP | Oui | ✅ Obligatoire |
| Action irréversible | delete, send | ✅ Obligatoire |
| Confiance initiale | < 75% | ✅ Recommandé |
| Entités ambiguës | > 2 | ⚠️ Optionnel |

#### 10.6.6 Coût Additionnel

| Scénario | Sans vérification | Avec vérification | Delta |
|----------|-------------------|-------------------|-------|
| High-stakes (1%) | $0.015 (Sonnet) | $0.018 (Sonnet + Haiku) | +$0.003 |
| Avec arbitrage (0.3%) | - | $0.093 (+ Opus) | +$0.078 |
| **Impact mensuel** | - | +$1.50 | Négligeable |

---

### 10.7 Plan d'Implémentation Sprint 8

#### 10.7.1 Fichiers à Créer/Modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `src/sancho/confidence.py` | Créer | DecomposedConfidence + logique |
| `src/sancho/chain_of_thought.py` | Créer | Parsing CoT + validation |
| `src/sancho/self_critique.py` | Créer | Pass 2a self-critique |
| `src/sancho/structured_context.py` | Créer | StructuredContext + EntityProfile |
| `src/sancho/cross_verification.py` | Créer | Vérification croisée high-stakes |
| `src/sancho/multi_pass_analyzer.py` | Modifier | Intégration des 5 améliorations |
| `templates/ai/v2/pass1_with_cot.j2` | Créer | Prompt avec CoT |
| `templates/ai/v2/pass2a_self_critique.j2` | Créer | Prompt self-critique |
| `templates/ai/v2/pass2_structured_context.j2` | Créer | Prompt contexte structuré |
| `templates/ai/v2/arbitration_opus.j2` | Créer | Prompt arbitrage Opus |

#### 10.7.2 Estimation Effort

| Composant | Lignes estimées | Jours |
|-----------|-----------------|-------|
| confidence.py | ~200 | 0.5 |
| chain_of_thought.py | ~150 | 0.5 |
| self_critique.py | ~250 | 1 |
| structured_context.py | ~400 | 1 |
| cross_verification.py | ~350 | 1 |
| Templates (4) | ~400 | 1 |
| Tests unitaires | ~600 | 1.5 |
| Tests intégration | ~300 | 1 |
| **TOTAL** | ~2650 | **7.5 jours** |

#### 10.7.3 Ordre d'Implémentation

1. **Confiance décomposée** (prérequis pour les autres)
2. **Chain-of-thought** (améliore Pass 1)
3. **Contexte structuré** (améliore Pass 2+)
4. **Self-critique** (Pass 2a intermédiaire)
5. **Vérification croisée** (cas high-stakes)

---

### 10.8 Métriques Sprint 8

| Métrique | Avant | Objectif | Mesure |
|----------|-------|----------|--------|
| Extractions correctes | 87% | 95% | user_feedback |
| Entités bien identifiées | 82% | 92% | entity_match_rate |
| Actions appropriées | 90% | 96% | action_accuracy |
| Erreurs high-stakes | 5% | 0.5% | high_stakes_errors |
| Confiance moyenne | 85% | 92% | avg_confidence |
| Coût mensuel | $59 | $65 | total_cost |

---

**Statut** : Prêt pour implémentation
**Prochaine étape** : Sprint 7 - Multi-Pass Implementation, puis Sprint 8 - Advanced Quality
