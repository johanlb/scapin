# Spécification Workflow v2 : "Extraction de Connaissance"

**Version** : 2.0.0-draft
**Date** : 11 janvier 2026
**Auteur** : Johan + Claude
**Statut** : En cours de rédaction

---

## Table des Matières

1. [Vision et Objectifs](#1-vision-et-objectifs)
2. [Principes Fondamentaux](#2-principes-fondamentaux)
3. [Architecture Générale](#3-architecture-générale)
4. [Phase 1 : Perception + Extraction](#4-phase-1--perception--extraction)
5. [Phase 2 : Matching + Contexte](#5-phase-2--matching--contexte)
6. [Phase 3 : Analyse Sémantique](#6-phase-3--analyse-sémantique)
7. [Phase 4 : Enrichissement PKM](#7-phase-4--enrichissement-pkm)
8. [Phase 5 : Action](#8-phase-5--action)
9. [Phase 6 : Maintenance PKM](#9-phase-6--maintenance-pkm)
10. [Modèles de Données](#10-modèles-de-données)
11. [Configuration](#11-configuration)
12. [Migration depuis v1](#12-migration-depuis-v1)
13. [Métriques de Succès](#13-métriques-de-succès)
14. [Annexes](#14-annexes)

---

## 1. Vision et Objectifs

### 1.1 Changement de Paradigme

**Workflow v1 (actuel)** : Centré sur le **triage**
```
Événement → "Que dois-je FAIRE ?" → Action → (optionnel) Note
```

**Workflow v2 (nouveau)** : Centré sur l'**extraction de connaissance**
```
Événement → "Quelles INFORMATIONS extraire ?" → Enrichissement PKM → Action
```

### 1.2 Objectifs Primaires

| Priorité | Objectif | Mesure de Succès |
|----------|----------|------------------|
| **1** | Qualité d'extraction | Pertinence des infos extraites > 90% |
| **2** | Enrichissement PKM continu | Notes enrichies/jour, liens créés/jour |
| **3** | Inbox Zero | Temps moyen de traitement < 5s |
| **4** | Boucle vertueuse | Amélioration contexte mesurable |

### 1.3 Objectifs Secondaires

- **Réduction coût API** : -70% vs v1 (Fast Path + 1 appel vs 3-5)
- **Latence** : < 3s pour Fast Path, < 10s pour analyse complète
- **Fiabilité** : Fonctionnement dégradé possible si API indisponible

### 1.4 Non-Objectifs (hors scope v2)

- Confidentialité totale (IA 100% locale) — Phase 3 requiert toujours API
- Génération de réponses email automatiques — Reste manuel
- Intégration multi-utilisateurs — Scapin reste personnel

---

## 2. Principes Fondamentaux

### 2.1 Information en Couches

Chaque information extraite a une **importance** et une **destination** :

| Type Information | Importance | Destination Primaire | Destination Secondaire |
|-----------------|------------|---------------------|----------------------|
| **Décision** | Haute | Note Projet/Sujet | Note Personnes impliquées |
| **Engagement** | Haute | Note Personne | Action OmniFocus (suivi) |
| **Fait** | Moyenne | Note Sujet concerné | — |
| **Opinion** | Moyenne | Note Personne | Note Sujet si pertinent |
| **Date/Deadline** | Haute | Action OmniFocus | Note Projet |
| **Relation** | Basse | Lien entre notes | — |
| **Bruit** | Nulle | Aucune | — |

### 2.2 Structure PKM "Neurale"

Le PKM est un **graphe de connaissances** où :

```
┌─────────────────────────────────────────────────────────────────┐
│                      GRAPHE DE CONNAISSANCES                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         travaille sur         ┌─────────────┐ │
│  │    Marc     │ ─────────────────────────────▶│   Projet    │ │
│  │   Dupont    │◀──────────────────────────────│    Alpha    │ │
│  │  (Personne) │         tech lead             │   (Projet)  │ │
│  └──────┬──────┘                               └──────┬──────┘ │
│         │                                             │        │
│         │ collègue de                                 │ budget │
│         │                                             │        │
│         ▼                                             ▼        │
│  ┌─────────────┐                               ┌─────────────┐ │
│  │   Sophie    │                               │   Budget    │ │
│  │   Martin    │                               │    2026     │ │
│  │  (Personne) │                               │  (Finance)  │ │
│  └─────────────┘                               └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Règles de liaison** :
- Chaque note peut avoir N liens sortants et N liens entrants
- Chaque lien a un **type** (relation sémantique)
- Les liens sont **bidirectionnels** en affichage mais stockés unidirectionnellement

### 2.3 Boucle Vertueuse

```
┌─────────────────────────────────────────────────────────────────┐
│                       BOUCLE VERTUEUSE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Événement entrant                                              │
│        │                                                        │
│        ▼                                                        │
│  ┌─────────────┐    contexte     ┌─────────────┐               │
│  │  Analyse    │◀───────────────│    Notes    │               │
│  │  enrichie   │                │  existantes │               │
│  └──────┬──────┘                └──────▲──────┘               │
│         │                              │                       │
│         │ extraction                   │ enrichissement        │
│         │                              │                       │
│         ▼                              │                       │
│  ┌─────────────┐                       │                       │
│  │ Informations│───────────────────────┘                       │
│  │  nouvelles  │                                               │
│  └─────────────┘                                               │
│                                                                 │
│  Plus de notes → Meilleur contexte → Meilleure analyse         │
│  Meilleure analyse → Plus d'extraction → Plus de notes         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Fast Path vs Full Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                    DÉCISION FAST PATH                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Événement → Pattern Sganarelle ?                               │
│                    │                                            │
│         ┌─────────┴─────────┐                                   │
│         │                   │                                   │
│         ▼                   ▼                                   │
│  ┌─────────────┐     ┌─────────────┐                           │
│  │  FAST PATH  │     │FULL ANALYSIS│                           │
│  │             │     │             │                           │
│  │ Confiance   │     │ Confiance   │                           │
│  │   > 95%     │     │   < 95%     │                           │
│  │             │     │     OU      │                           │
│  │ Pattern     │     │ Pas de      │                           │
│  │ success_rate│     │ pattern     │                           │
│  │   > 90%     │     │             │                           │
│  └──────┬──────┘     └──────┬──────┘                           │
│         │                   │                                   │
│         ▼                   ▼                                   │
│  Action directe       Phase 3 (API)                            │
│  0 appel API          1 appel API                              │
│  < 500ms              5-10s                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Exemples Fast Path** :
- Newsletter connue → Archive (pattern: sender + subject contains "newsletter")
- Facture récurrente → Archive + Tag "Finance" (pattern: sender = comptabilité)
- Notification automatique → Archive (pattern: sender contains "noreply")
- Message Teams court sans @mention → Ignore (pattern: length < 50, no mention)

---

## 3. Architecture Générale

### 3.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WORKFLOW V2 - VUE GLOBALE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SOURCES D'ÉVÉNEMENTS                        │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │   │
│  │  │  Email  │  │  Teams  │  │ Calendar│  │ Fichiers│  │  Notes  │   │   │
│  │  │  IMAP   │  │  Graph  │  │  Graph  │  │  Local  │  │ (révision)│  │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   │   │
│  └───────┼────────────┼───────────┼───────────┼───────────┼──────────┘   │
│          │            │           │           │           │               │
│          └────────────┴─────┬─────┴───────────┴───────────┘               │
│                             │                                              │
│                             ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 1 : PERCEPTION + EXTRACTION                    [LOCAL]       │   │
│  │  Trivelin + NER local + Classification + Embeddings                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                              │
│                             ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 2 : MATCHING + CONTEXTE                        [LOCAL]       │   │
│  │  Passepartout + Sganarelle patterns + FAISS                         │   │
│  │                                                                     │   │
│  │  ──────────────── FAST PATH ? ────────────────                      │   │
│  │         │ OUI                        │ NON                          │   │
│  │         ▼                            ▼                              │   │
│  │  ┌─────────────┐            ┌─────────────────┐                     │   │
│  │  │ Skip Phase 3│            │ Continue Phase 3│                     │   │
│  │  │ Action direct│            │                 │                     │   │
│  │  └──────┬──────┘            └────────┬────────┘                     │   │
│  └─────────┼───────────────────────────┼───────────────────────────────┘   │
│            │                           │                                   │
│            │                           ▼                                   │
│            │  ┌─────────────────────────────────────────────────────────┐  │
│            │  │  PHASE 3 : ANALYSE SÉMANTIQUE               [API CLOUD] │  │
│            │  │  Sancho (1 appel Claude Sonnet)                         │  │
│            │  └─────────────────────────────────────────────────────────┘  │
│            │                           │                                   │
│            └───────────┬───────────────┘                                   │
│                        │                                                   │
│                        ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 4 : ENRICHISSEMENT PKM                         [LOCAL]       │   │
│  │  Passepartout (CRUD notes + liens + indexation)                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                        │                                                   │
│                        ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 5 : ACTION                                     [LOCAL]       │   │
│  │  Figaro (IMAP, OmniFocus, notifications)                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                        │                                                   │
│                        ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 6 : MAINTENANCE PKM                  [LOCAL + API BATCH]     │   │
│  │  Background: Linking, Refactoring, Synthèse, Nettoyage              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Mapping Modules Existants

| Phase | Module Principal | Modules Secondaires | Modifications |
|-------|-----------------|---------------------|---------------|
| **1** | Trivelin | — | + NER local, + classification locale |
| **2** | Passepartout | Sganarelle | + Fast Path logic |
| **3** | Sancho | — | Refonte prompt, 1 appel au lieu de 5 |
| **4** | Passepartout | Figaro (notes) | + Gestion liens, + routing info |
| **5** | Figaro | — | Inchangé |
| **6** | Passepartout | Sancho (batch) | **NOUVEAU** |

### 3.3 Flux de Données

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUX DE DONNÉES DÉTAILLÉ                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EmailMetadata/TeamsMessage/CalendarEvent/FileEvent                         │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PerceivedEvent (existant, inchangé)                                │   │
│  │  + extracted_entities: list[Entity]     ← Phase 1 NER               │   │
│  │  + info_type: InfoType                  ← Phase 1 Classification    │   │
│  │  + embedding: list[float]               ← Phase 1 (existant)        │   │
│  │  + importance_score: float              ← Phase 1                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  EnrichedEvent (NOUVEAU)                                            │   │
│  │  - event: PerceivedEvent                                            │   │
│  │  - matched_notes: list[NoteReference]   ← Phase 2                   │   │
│  │  - matched_patterns: list[Pattern]      ← Phase 2                   │   │
│  │  - context_summary: str                 ← Phase 2                   │   │
│  │  - fast_path_eligible: bool             ← Phase 2                   │   │
│  │  - fast_path_action: Optional[Action]   ← Phase 2                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  AnalysisResult (NOUVEAU - remplace EmailAnalysis)                  │   │
│  │  - extracted_info: list[ExtractedInfo]  ← Phase 3                   │   │
│  │  - proposed_links: list[NoteLink]       ← Phase 3                   │   │
│  │  - recommended_action: Action           ← Phase 3                   │   │
│  │  - confidence: float                    ← Phase 3                   │   │
│  │  - reasoning: str                       ← Phase 3                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  EnrichmentResult (NOUVEAU)                                         │   │
│  │  - notes_created: list[NoteId]          ← Phase 4                   │   │
│  │  - notes_updated: list[NoteId]          ← Phase 4                   │   │
│  │  - links_created: list[NoteLink]        ← Phase 4                   │   │
│  │  - omnifocus_tasks: list[TaskId]        ← Phase 4                   │   │
│  │  - queued_for_review: list[QueueItem]   ← Phase 4                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ExecutionResult (existant, inchangé)                               │   │
│  │  - success: bool                        ← Phase 5                   │   │
│  │  - executed_actions: list[Action]       ← Phase 5                   │   │
│  │  - errors: list[str]                    ← Phase 5                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Phase 1 : Perception + Extraction

### 4.1 Objectif

Transformer un événement brut en événement enrichi avec :
- Entités extraites (personnes, projets, dates, lieux, organisations)
- Type d'information (décision, engagement, fait, bruit)
- Embedding vectoriel pour recherche sémantique
- Score d'importance préliminaire

### 4.2 Composants

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1 : DÉTAIL DES COMPOSANTS                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Événement brut                                                             │
│       │                                                                     │
│       ├────────────────┬────────────────┬────────────────┐                 │
│       │                │                │                │                 │
│       ▼                ▼                ▼                ▼                 │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│  │Normalizer│     │   NER   │     │ Classif │     │Embedding│              │
│  │(existant)│     │  Local  │     │  Local  │     │(existant)│             │
│  └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘              │
│       │                │                │                │                 │
│       │          ┌─────┴─────┐    ┌─────┴─────┐         │                 │
│       │          │  GLiNER   │    │  FastText │         │                 │
│       │          │    ou     │    │    ou     │         │                 │
│       │          │  spaCy    │    │ SetFit    │         │                 │
│       │          └─────┬─────┘    └─────┬─────┘         │                 │
│       │                │                │                │                 │
│       └────────────────┴────────┬───────┴────────────────┘                 │
│                                 │                                          │
│                                 ▼                                          │
│                        PerceivedEvent enrichi                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 NER Local

**Option recommandée** : GLiNER (Generalist and Lightweight Named Entity Recognition)

| Critère | GLiNER | spaCy | Transformers |
|---------|--------|-------|--------------|
| **Taille modèle** | ~400MB | ~50MB | ~500MB+ |
| **Latence** | ~100ms | ~20ms | ~200ms |
| **Qualité** | Excellente | Bonne | Excellente |
| **Entités custom** | ✅ Zero-shot | ❌ Entraînement | ✅ Fine-tuning |
| **M1 optimisé** | ✅ MPS | ✅ | ✅ MPS |

**Entités à extraire** :

```python
ENTITY_TYPES = [
    "PERSON",           # Marc Dupont, Sophie
    "ORGANIZATION",     # Acme Corp, DGFIP
    "PROJECT",          # Projet Alpha, Sprint 5
    "DATE",             # 15 janvier, lundi prochain, S12
    "MONEY",            # 50k€, 1.2M$
    "LOCATION",         # Paris, Salle A, Bureau 302
    "PRODUCT",          # iPhone, Scapin, Salesforce
    "EVENT",            # Réunion budget, Conf annuelle
    "DEADLINE",         # Livraison S12, Date limite 15/02
]
```

**Interface** :

```python
# src/core/extractors/ner_local.py

class LocalNERExtractor:
    """
    Extracteur d'entités nommées local (GLiNER)
    """

    def __init__(self, model_name: str = "urchade/gliner_medium-v2.1"):
        self.model = GLiNER.from_pretrained(model_name)
        self.entity_types = ENTITY_TYPES

    def extract(self, text: str) -> list[Entity]:
        """
        Extrait les entités d'un texte

        Args:
            text: Texte à analyser

        Returns:
            Liste d'Entity avec type, valeur, position, confidence
        """
        entities = self.model.predict_entities(
            text,
            self.entity_types,
            threshold=0.5
        )

        return [
            Entity(
                type=e["label"],
                value=e["text"],
                confidence=e["score"],
                start=e["start"],
                end=e["end"]
            )
            for e in entities
        ]
```

### 4.4 Classification Locale

**Option recommandée** : SetFit (Sentence Transformer Fine-tuning)

| Type Information | Exemples | Action PKM typique |
|-----------------|----------|-------------------|
| `DECISION` | "On valide le budget", "Décision prise de..." | Note projet + historique |
| `ENGAGEMENT` | "Je t'envoie demain", "Marc s'occupe de..." | Note personne + OmniFocus |
| `INFORMATION` | "Le projet avance bien", "Nouveau client signé" | Note sujet |
| `QUESTION` | "Peux-tu confirmer ?", "Quelle est la deadline ?" | Flag + potentiel OmniFocus |
| `ACTION_REQUEST` | "Merci de valider", "À faire pour lundi" | OmniFocus |
| `NOISE` | "OK", "Merci !", "Bien reçu" | Aucune |

**Interface** :

```python
# src/core/extractors/info_classifier.py

class LocalInfoClassifier:
    """
    Classificateur de type d'information local (SetFit)
    """

    def __init__(self, model_path: str = "models/info_classifier"):
        self.model = SetFitModel.from_pretrained(model_path)
        self.labels = [
            "DECISION", "ENGAGEMENT", "INFORMATION",
            "QUESTION", "ACTION_REQUEST", "NOISE"
        ]

    def classify(self, text: str) -> tuple[str, float]:
        """
        Classifie le type d'information

        Returns:
            (label, confidence)
        """
        prediction = self.model.predict([text])[0]
        probabilities = self.model.predict_proba([text])[0]
        confidence = max(probabilities)

        return prediction, confidence
```

### 4.5 Score d'Importance

Calcul heuristique combinant plusieurs signaux :

```python
def calculate_importance_score(
    event: PerceivedEvent,
    entities: list[Entity],
    info_type: str,
    info_confidence: float
) -> float:
    """
    Calcule un score d'importance 0-1
    """
    score = 0.0

    # Base par type d'info
    type_weights = {
        "DECISION": 0.9,
        "ENGAGEMENT": 0.8,
        "ACTION_REQUEST": 0.85,
        "QUESTION": 0.6,
        "INFORMATION": 0.5,
        "NOISE": 0.1,
    }
    score = type_weights.get(info_type, 0.5) * info_confidence

    # Boost si entités importantes
    vip_entities = get_vip_entities()  # Depuis config ou patterns
    for entity in entities:
        if entity.value in vip_entities:
            score += 0.1

    # Boost si deadline proche
    for entity in entities:
        if entity.type == "DEADLINE":
            days_until = parse_deadline(entity.value)
            if days_until and days_until < 7:
                score += 0.15

    # Boost selon source
    source_weights = {
        "email_direct": 0.1,    # Email où je suis en To:
        "email_cc": 0.0,        # Email où je suis en Cc:
        "teams_mention": 0.15,  # Teams avec @mention
        "teams_dm": 0.1,        # Teams message direct
        "calendar_organizer": 0.1,  # Événement dont je suis organisateur
    }
    score += source_weights.get(event.metadata.get("interaction_type", ""), 0)

    return min(1.0, score)
```

### 4.6 Sortie Phase 1

```python
@dataclass
class Phase1Result:
    """Résultat de la Phase 1 : Perception + Extraction"""

    # Événement normalisé (existant)
    event: PerceivedEvent

    # Nouvelles extractions
    entities: list[Entity]
    info_type: str
    info_type_confidence: float
    importance_score: float

    # Embedding (existant, calculé par sentence-transformers)
    embedding: list[float]

    # Métadonnées de traitement
    extraction_duration_ms: float
    ner_model: str
    classifier_model: str
```

---

## 5. Phase 2 : Matching + Contexte

### 5.1 Objectif

- Trouver les notes existantes liées à l'événement
- Récupérer les patterns Sganarelle applicables
- Construire le contexte pour l'analyse
- Décider si Fast Path applicable

### 5.2 Composants

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2 : MATCHING + CONTEXTE                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase1Result                                                               │
│       │                                                                     │
│       ├────────────────┬────────────────┬────────────────┐                 │
│       │                │                │                │                 │
│       ▼                ▼                ▼                ▼                 │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│  │ Entity  │     │Semantic │     │ Pattern │     │ History │              │
│  │ Matcher │     │ Search  │     │ Matcher │     │ Lookup  │              │
│  └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘              │
│       │                │                │                │                 │
│       │   Notes par    │   Notes par    │   Patterns     │   Interactions │
│       │   entité       │   similarité   │   Sganarelle   │   passées      │
│       │                │                │                │                 │
│       └────────────────┴────────┬───────┴────────────────┘                 │
│                                 │                                          │
│                                 ▼                                          │
│                       ┌─────────────────┐                                  │
│                       │ Context Builder │                                  │
│                       │                 │                                  │
│                       │ • Rank notes    │                                  │
│                       │ • Merge context │                                  │
│                       │ • Check FastPath│                                  │
│                       └────────┬────────┘                                  │
│                                │                                           │
│                                ▼                                           │
│                        EnrichedEvent                                       │
│                                │                                           │
│                    ┌───────────┴───────────┐                               │
│                    │                       │                               │
│                    ▼                       ▼                               │
│             Fast Path ?              Full Analysis                         │
│                    │                       │                               │
│                    ▼                       ▼                               │
│              Phase 5                 Phase 3                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Entity Matcher

Trouve les notes mentionnant les entités extraites :

```python
class EntityMatcher:
    """
    Trouve les notes liées aux entités extraites
    """

    def __init__(self, note_manager: NoteManager):
        self.note_manager = note_manager

    def match(
        self,
        entities: list[Entity],
        top_k_per_entity: int = 3
    ) -> list[NoteMatch]:
        """
        Pour chaque entité, trouve les notes les plus pertinentes
        """
        matches = []

        for entity in entities:
            # Recherche par nom de note (exact ou fuzzy)
            note_by_title = self.note_manager.get_note_by_title(entity.value)
            if note_by_title:
                matches.append(NoteMatch(
                    note=note_by_title,
                    match_type="title_exact",
                    entity=entity,
                    relevance=1.0
                ))
                continue

            # Recherche dans le contenu des notes
            notes = self.note_manager.search_by_content(
                entity.value,
                top_k=top_k_per_entity
            )
            for note, score in notes:
                matches.append(NoteMatch(
                    note=note,
                    match_type="content",
                    entity=entity,
                    relevance=score * entity.confidence
                ))

        # Déduplique et trie par relevance
        return self._deduplicate_and_rank(matches)
```

### 5.4 Pattern Matcher (Sganarelle)

```python
class PatternMatcher:
    """
    Trouve les patterns Sganarelle applicables
    """

    def __init__(self, pattern_store: PatternStore):
        self.pattern_store = pattern_store

    def match(
        self,
        event: PerceivedEvent,
        entities: list[Entity],
        info_type: str
    ) -> list[PatternMatch]:
        """
        Trouve les patterns applicables à cet événement
        """
        matches = []

        # Patterns par expéditeur
        sender = event.metadata.get("from_address", "")
        sender_patterns = self.pattern_store.get_by_sender(sender)
        matches.extend(sender_patterns)

        # Patterns par type d'info + entités
        entity_values = [e.value for e in entities]
        context_patterns = self.pattern_store.get_by_context(
            info_type=info_type,
            entities=entity_values
        )
        matches.extend(context_patterns)

        # Patterns par subject/title
        title_patterns = self.pattern_store.get_by_title_keywords(
            event.title
        )
        matches.extend(title_patterns)

        # Filtre et trie par confidence + success_rate
        return self._filter_and_rank(matches)
```

### 5.5 Fast Path Decision

```python
class FastPathDecider:
    """
    Détermine si un événement peut être traité sans API
    """

    def __init__(
        self,
        min_pattern_confidence: float = 0.95,
        min_pattern_success_rate: float = 0.90,
        min_pattern_occurrences: int = 5
    ):
        self.min_confidence = min_pattern_confidence
        self.min_success_rate = min_pattern_success_rate
        self.min_occurrences = min_pattern_occurrences

    def decide(
        self,
        event: PerceivedEvent,
        patterns: list[PatternMatch],
        info_type: str
    ) -> FastPathDecision:
        """
        Décide si Fast Path applicable
        """
        # Condition 1: Pattern fort existe
        strong_patterns = [
            p for p in patterns
            if p.confidence >= self.min_confidence
            and p.success_rate >= self.min_success_rate
            and p.occurrences >= self.min_occurrences
        ]

        if not strong_patterns:
            return FastPathDecision(
                eligible=False,
                reason="no_strong_pattern"
            )

        # Condition 2: Type d'info compatible (pas de décision/engagement)
        if info_type in ["DECISION", "ENGAGEMENT", "ACTION_REQUEST"]:
            return FastPathDecision(
                eligible=False,
                reason="high_value_info_type"
            )

        # Condition 3: Pas d'entités VIP non connues
        best_pattern = strong_patterns[0]

        return FastPathDecision(
            eligible=True,
            reason="pattern_match",
            pattern=best_pattern,
            suggested_action=best_pattern.suggested_action
        )
```

### 5.6 Sortie Phase 2

```python
@dataclass
class EnrichedEvent:
    """Événement enrichi avec contexte (sortie Phase 2)"""

    # Phase 1
    phase1: Phase1Result

    # Notes liées
    matched_notes: list[NoteMatch]

    # Patterns applicables
    matched_patterns: list[PatternMatch]

    # Contexte compilé pour le prompt
    context_summary: str

    # Décision Fast Path
    fast_path: FastPathDecision

    # Métadonnées
    matching_duration_ms: float
```

---

## 6. Phase 3 : Analyse Sémantique

### 6.1 Objectif

Analyser l'événement en profondeur pour :
- Extraire toutes les informations utiles
- Déterminer leurs destinations (notes, OmniFocus)
- Détecter les liens entre entités/notes
- Recommander l'action sur l'événement source

### 6.2 Différences vs v1

| Aspect | v1 (actuel) | v2 (nouveau) |
|--------|-------------|--------------|
| **Nombre d'appels** | 3-5 (multi-pass) | 1 |
| **Focus** | "Quelle action ?" | "Quelles informations ?" |
| **Sortie** | EmailAnalysis | AnalysisResult (plus riche) |
| **Contexte** | Récupéré pendant | Pré-calculé (Phase 2) |
| **Modèle** | Haiku → Sonnet → Sonnet | Sonnet (1 appel) |

### 6.3 Prompt Template

```jinja2
{# src/sancho/templates/ai/extraction_analysis.j2 #}

Tu es Sancho, l'assistant cognitif de Johan. Ta mission est d'extraire
les informations importantes et de les router vers les bonnes destinations.

## ÉVÉNEMENT À ANALYSER

**Type**: {{ event.event_type }}
**Source**: {{ event.source }}
**Date**: {{ event.timestamp | format_date }}
**De**: {{ event.metadata.from_address | default("N/A") }}
**Sujet**: {{ event.title }}

**Contenu**:
```
{{ event.content | truncate(3000) }}
```

## ENTITÉS DÉTECTÉES (Phase 1)

{% for entity in entities %}
- {{ entity.type }}: "{{ entity.value }}" (confiance: {{ entity.confidence | percent }})
{% endfor %}

## TYPE D'INFORMATION DÉTECTÉ

{{ info_type }} (confiance: {{ info_type_confidence | percent }})

## NOTES EXISTANTES PERTINENTES

{% for note in matched_notes[:5] %}
### {{ note.note.title }}
Pertinence: {{ note.relevance | percent }}
Extrait:
```
{{ note.note.content | truncate(500) }}
```
{% endfor %}

## PATTERNS CONNUS

{% for pattern in matched_patterns[:3] %}
- Pattern "{{ pattern.name }}": {{ pattern.description }}
  Action suggérée: {{ pattern.suggested_action }}
  Confiance: {{ pattern.confidence | percent }}
{% endfor %}

---

## TA TÂCHE

Analyse cet événement et extrais TOUTES les informations utiles.

Pour chaque information, détermine:
1. Son type (décision, engagement, fait, opinion, date/deadline, relation)
2. Son importance (haute, moyenne, basse)
3. Sa destination:
   - Note(s) à enrichir (titre exact ou à créer)
   - Action OmniFocus si suivi nécessaire
   - Aucune si bruit

Détecte aussi les relations entre personnes/projets/organisations.

## FORMAT DE RÉPONSE (JSON strict)

```json
{
  "informations": [
    {
      "type": "decision|engagement|fait|opinion|deadline|relation",
      "contenu": "Description concise de l'information",
      "importance": "haute|moyenne|basse",
      "confiance": 0.0-1.0,
      "source_excerpt": "Citation exacte du texte source",
      "destinations": {
        "notes": [
          {
            "titre": "Titre de la note (existante ou à créer)",
            "action": "enrichir|creer",
            "section": "Section où ajouter (optionnel)",
            "contenu_a_ajouter": "Texte à ajouter à la note"
          }
        ],
        "omnifocus": {
          "creer": true|false,
          "titre": "Titre de la tâche",
          "projet": "Projet OmniFocus (optionnel)",
          "due_date": "YYYY-MM-DD (optionnel)",
          "defer_date": "YYYY-MM-DD (optionnel)",
          "note": "Contexte pour la tâche"
        }
      }
    }
  ],
  "liens_detectes": [
    {
      "source": "Titre note source",
      "cible": "Titre note cible",
      "relation": "travaille_sur|responsable_de|collegue_de|appartient_a|..."
    }
  ],
  "action_evenement": {
    "type": "archive|flag|queue|delete|rien",
    "confiance": 0.0-1.0,
    "raison": "Explication courte"
  },
  "resume_extraction": "Résumé en 1-2 phrases de ce qui a été extrait"
}
```

IMPORTANT:
- Ne propose que des informations NOUVELLES (pas ce qui est déjà dans les notes)
- Sois précis sur les titres de notes (utilise les existants si pertinents)
- Pour les engagements, crée TOUJOURS une tâche OmniFocus de suivi
- Les dates doivent être au format YYYY-MM-DD
- La confiance reflète ta certitude sur l'information extraite
```

### 6.4 Interface

```python
class SemanticAnalyzer:
    """
    Analyse sémantique via API Claude (Phase 3)
    """

    def __init__(
        self,
        ai_router: AIRouter,
        template_manager: TemplateManager
    ):
        self.ai_router = ai_router
        self.template_manager = template_manager

    async def analyze(
        self,
        enriched_event: EnrichedEvent
    ) -> AnalysisResult:
        """
        Analyse complète en 1 appel API
        """
        # Prépare le prompt
        prompt = self.template_manager.render(
            "ai/extraction_analysis",
            event=enriched_event.phase1.event,
            entities=enriched_event.phase1.entities,
            info_type=enriched_event.phase1.info_type,
            info_type_confidence=enriched_event.phase1.info_type_confidence,
            matched_notes=enriched_event.matched_notes,
            matched_patterns=enriched_event.matched_patterns
        )

        # Appel API
        response, usage = await self.ai_router.analyze_with_prompt(
            prompt=prompt,
            model=AIModel.CLAUDE_SONNET,
            system_prompt="Tu es Sancho, assistant cognitif expert en extraction d'information.",
            response_format="json"
        )

        # Parse la réponse
        return self._parse_response(response, usage)

    def _parse_response(
        self,
        response: str,
        usage: dict
    ) -> AnalysisResult:
        """Parse et valide la réponse JSON"""
        data = json.loads(response)

        return AnalysisResult(
            informations=[
                ExtractedInfo(**info)
                for info in data["informations"]
            ],
            liens_detectes=[
                NoteLink(**lien)
                for lien in data["liens_detectes"]
            ],
            action_evenement=EventAction(**data["action_evenement"]),
            resume=data["resume_extraction"],
            api_usage=usage
        )
```

### 6.5 Sortie Phase 3

```python
@dataclass
class ExtractedInfo:
    """Une information extraite"""
    type: str  # decision, engagement, fait, opinion, deadline, relation
    contenu: str
    importance: str  # haute, moyenne, basse
    confiance: float
    source_excerpt: str
    destinations: InfoDestinations

@dataclass
class InfoDestinations:
    """Destinations d'une information"""
    notes: list[NoteDestination]
    omnifocus: Optional[OmniFocusTask]

@dataclass
class NoteDestination:
    """Destination vers une note"""
    titre: str
    action: str  # enrichir, creer
    section: Optional[str]
    contenu_a_ajouter: str

@dataclass
class NoteLink:
    """Lien entre deux notes"""
    source: str
    cible: str
    relation: str

@dataclass
class EventAction:
    """Action sur l'événement source"""
    type: str  # archive, flag, queue, delete, rien
    confiance: float
    raison: str

@dataclass
class AnalysisResult:
    """Résultat complet de l'analyse sémantique (Phase 3)"""
    informations: list[ExtractedInfo]
    liens_detectes: list[NoteLink]
    action_evenement: EventAction
    resume: str
    api_usage: dict
```

---

## 7. Phase 4 : Enrichissement PKM

### 7.1 Objectif

Appliquer les résultats de l'analyse au PKM :
- Créer/enrichir les notes
- Créer les liens entre notes
- Créer les tâches OmniFocus
- Mettre en queue ce qui nécessite validation

### 7.2 Seuils d'Auto-application

```python
class EnrichmentPolicy:
    """Politique d'enrichissement automatique"""

    # Seuils de confiance pour auto-apply
    AUTO_APPLY_NOTE_THRESHOLD = 0.90
    AUTO_APPLY_LINK_THRESHOLD = 0.85
    AUTO_APPLY_TASK_THRESHOLD = 0.88

    # Exceptions : toujours demander validation
    ALWAYS_REVIEW = [
        "delete_note",      # Suppression
        "merge_notes",      # Fusion
        "high_importance",  # Info haute importance
    ]
```

### 7.3 Workflow d'Enrichissement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 4 : ENRICHISSEMENT PKM                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AnalysisResult                                                             │
│       │                                                                     │
│       ├───────────────────────────────────────────────────────┐             │
│       │                                                       │             │
│       ▼                                                       ▼             │
│  ┌─────────────────────────────────┐     ┌─────────────────────────────┐   │
│  │  Pour chaque ExtractedInfo      │     │  Pour chaque NoteLink       │   │
│  │                                 │     │                             │   │
│  │  ┌─────────────────────────┐   │     │  ┌─────────────────────┐   │   │
│  │  │ Confiance >= 0.90 ?     │   │     │  │ Confiance >= 0.85 ? │   │   │
│  │  └───────────┬─────────────┘   │     │  └───────────┬─────────┘   │   │
│  │       OUI    │      NON        │     │       OUI    │    NON      │   │
│  │        │     │       │         │     │        │     │      │      │   │
│  │        ▼     │       ▼         │     │        ▼     │      ▼      │   │
│  │  ┌─────────┐ │ ┌─────────┐     │     │  ┌─────────┐ │ ┌─────────┐ │   │
│  │  │Auto-    │ │ │ Queue   │     │     │  │ Créer   │ │ │ Queue   │ │   │
│  │  │apply    │ │ │ review  │     │     │  │ lien    │ │ │ review  │ │   │
│  │  └────┬────┘ │ └────┬────┘     │     │  └────┬────┘ │ └────┬────┘ │   │
│  │       │      │      │          │     │       │      │      │      │   │
│  └───────┼──────┴──────┼──────────┘     └───────┼──────┴──────┼──────┘   │
│          │             │                        │             │           │
│          ▼             ▼                        ▼             ▼           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        NOTE MANAGER                                  │ │
│  │  • create_note()      • update_note()      • create_link()          │ │
│  │  • reindex()          • version (Git)                               │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│          │                                                               │
│          ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                      OMNIFOCUS CLIENT                                │ │
│  │  • create_task()      • assign_project()   • set_dates()            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│          │                                                               │
│          ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                       QUEUE STORAGE                                  │ │
│  │  • Items en attente de validation                                   │ │
│  │  • Présentés dans UI Flux                                           │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Gestion des Liens

```python
class NoteLinkManager:
    """
    Gère les liens entre notes
    """

    def create_link(
        self,
        source_note: str,
        target_note: str,
        relation: str
    ) -> bool:
        """
        Crée un lien bidirectionnel entre deux notes

        Stockage:
        - Dans le frontmatter YAML de chaque note
        - Dans un index SQLite pour recherche rapide
        """
        # Ajoute dans la note source
        source = self.note_manager.get_note(source_note)
        if not source:
            return False

        source.add_link(
            target=target_note,
            relation=relation,
            direction="outgoing"
        )

        # Ajoute dans la note cible (lien inverse)
        target = self.note_manager.get_note(target_note)
        if target:
            target.add_link(
                target=source_note,
                relation=self._inverse_relation(relation),
                direction="incoming"
            )

        # Indexe pour recherche
        self._index_link(source_note, target_note, relation)

        return True

    def _inverse_relation(self, relation: str) -> str:
        """Retourne la relation inverse"""
        inverses = {
            "travaille_sur": "a_pour_membre",
            "responsable_de": "supervisé_par",
            "appartient_a": "contient",
            "collegue_de": "collegue_de",  # symétrique
            "mentionne": "mentionné_par",
        }
        return inverses.get(relation, f"lié_à")
```

### 7.5 Format Note avec Liens

```yaml
---
title: Marc Dupont
type: personne
created: 2026-01-10T10:00:00
updated: 2026-01-11T15:30:00
tags:
  - equipe
  - tech
links:
  outgoing:
    - target: Projet Alpha
      relation: travaille_sur
      since: 2026-01-05
    - target: Sophie Martin
      relation: collegue_de
      since: 2025-12-01
  incoming:
    - source: Projet Alpha
      relation: a_pour_membre
    - source: Réunion Budget 2026
      relation: participant
---

# Marc Dupont

## Rôle
Tech Lead sur le Projet Alpha depuis janvier 2026.

## Historique des interactions

### 2026-01-11
- Engagement: Envoyer les specs techniques lundi 13/01
- Source: Email "Re: Specs Projet Alpha"

### 2026-01-10
- Décision validée: Budget Projet Alpha à 50k€
- Source: Teams - Canal Projet Alpha
```

### 7.6 Sortie Phase 4

```python
@dataclass
class EnrichmentResult:
    """Résultat de l'enrichissement PKM (Phase 4)"""

    # Notes modifiées
    notes_created: list[str]  # IDs des notes créées
    notes_updated: list[str]  # IDs des notes mises à jour

    # Liens créés
    links_created: list[NoteLink]

    # Tâches OmniFocus
    tasks_created: list[str]  # IDs OmniFocus

    # En attente de validation
    queued_items: list[QueueItem]

    # Métriques
    auto_applied_count: int
    queued_count: int
    enrichment_duration_ms: float
```

---

## 8. Phase 5 : Action

### 8.1 Objectif

Exécuter l'action recommandée sur l'événement source (email, message Teams, etc.)

### 8.2 Actions Supportées

| Action | Email | Teams | Calendar | Fichier |
|--------|-------|-------|----------|---------|
| `archive` | ✅ Move to folder | ✅ Mark read | — | ✅ Move to archive |
| `flag` | ✅ IMAP flag | ✅ Pin message | — | ✅ Tag file |
| `queue` | ✅ Keep in queue | ✅ Keep in queue | — | ✅ Keep in queue |
| `delete` | ✅ Move to trash | — | — | ✅ Move to trash |
| `rien` | ✅ Mark processed | ✅ Mark read | ✅ Mark seen | — |

### 8.3 Interface

```python
class ActionExecutor:
    """
    Exécute les actions sur les événements source (Phase 5)
    """

    def __init__(
        self,
        imap_client: IMAPClient,
        teams_client: TeamsClient,
        file_manager: FileManager
    ):
        self.imap = imap_client
        self.teams = teams_client
        self.files = file_manager

    async def execute(
        self,
        event: PerceivedEvent,
        action: EventAction
    ) -> ExecutionResult:
        """
        Exécute l'action sur l'événement source
        """
        if event.source == "email":
            return await self._execute_email_action(event, action)
        elif event.source == "teams":
            return await self._execute_teams_action(event, action)
        elif event.source == "file":
            return await self._execute_file_action(event, action)
        else:
            return ExecutionResult(success=True, action="none")

    async def _execute_email_action(
        self,
        event: PerceivedEvent,
        action: EventAction
    ) -> ExecutionResult:
        """Exécute action sur email"""
        email_id = event.metadata["message_id"]

        if action.type == "archive":
            folder = self._determine_archive_folder(event)
            success = await self.imap.move_email(email_id, folder)
        elif action.type == "flag":
            success = await self.imap.flag_email(email_id)
        elif action.type == "delete":
            success = await self.imap.move_to_trash(email_id)
        else:
            success = await self.imap.mark_processed(email_id)

        return ExecutionResult(
            success=success,
            action=action.type,
            event_id=event.event_id
        )
```

---

## 9. Phase 6 : Maintenance PKM

### 9.1 Objectif

Maintenir la qualité du PKM à travers des tâches de fond :
- Détection et création de liens manquants
- Fusion/réorganisation de notes similaires
- Génération de synthèses
- Nettoyage des informations obsolètes

### 9.2 Scheduling

```python
class PKMMaintenanceScheduler:
    """
    Planifie les tâches de maintenance PKM
    """

    # Fréquences par défaut
    SCHEDULE = {
        "linking": "every_hour",       # Détection liens
        "similarity_check": "daily",   # Détection doublons
        "synthesis": "weekly",         # Notes de synthèse
        "cleanup": "daily",            # Nettoyage
        "sm2_review": "continuous",    # Révision SM-2
    }
```

### 9.3 Linking Automatique

```python
class AutoLinker:
    """
    Détecte et propose des liens entre notes existantes
    """

    def detect_missing_links(
        self,
        min_similarity: float = 0.7
    ) -> list[ProposedLink]:
        """
        Trouve les notes qui devraient être liées
        """
        proposed = []

        # Pour chaque note
        for note in self.note_manager.get_all_notes():
            # Trouve les notes similaires
            similar = self.note_manager.search_similar(
                note.embedding,
                top_k=10,
                exclude=[note.note_id]
            )

            for sim_note, score in similar:
                if score < min_similarity:
                    continue

                # Vérifie si lien existe déjà
                if self.link_exists(note, sim_note):
                    continue

                # Propose le lien
                proposed.append(ProposedLink(
                    source=note.title,
                    target=sim_note.title,
                    similarity=score,
                    reason=self._explain_similarity(note, sim_note)
                ))

        return proposed
```

### 9.4 Fusion de Notes

```python
class NoteMerger:
    """
    Détecte et propose des fusions de notes similaires
    """

    def detect_duplicates(
        self,
        similarity_threshold: float = 0.85
    ) -> list[MergeProposal]:
        """
        Trouve les notes candidates à la fusion
        """
        proposals = []

        # Clustering par similarité
        clusters = self._cluster_similar_notes(similarity_threshold)

        for cluster in clusters:
            if len(cluster) < 2:
                continue

            # La note la plus complète devient la cible
            target = max(cluster, key=lambda n: len(n.content))
            sources = [n for n in cluster if n != target]

            proposals.append(MergeProposal(
                target=target,
                sources=sources,
                similarity=self._cluster_similarity(cluster)
            ))

        return proposals
```

### 9.5 Synthèses Automatiques

```python
class SynthesisGenerator:
    """
    Génère des notes de synthèse automatiquement
    """

    async def generate_weekly_synthesis(
        self,
        week_start: datetime
    ) -> Note:
        """
        Génère une synthèse hebdomadaire
        """
        # Collecte les informations de la semaine
        week_events = self._get_week_events(week_start)
        new_notes = self._get_new_notes(week_start)
        updated_notes = self._get_updated_notes(week_start)

        # Appel API pour synthèse
        prompt = self.template_manager.render(
            "ai/weekly_synthesis",
            events=week_events,
            new_notes=new_notes,
            updated_notes=updated_notes
        )

        synthesis = await self.ai_router.generate(prompt)

        # Crée la note de synthèse
        return self.note_manager.create_note(
            title=f"Synthèse Semaine {week_start.isocalendar()[1]}",
            content=synthesis,
            type="synthesis",
            tags=["synthese", "hebdomadaire"]
        )
```

### 9.6 Nettoyage

```python
class PKMCleaner:
    """
    Nettoie les informations obsolètes
    """

    def identify_obsolete_info(self) -> list[ObsoleteInfo]:
        """
        Identifie les informations potentiellement obsolètes
        """
        obsolete = []

        for note in self.note_manager.get_all_notes():
            # Dates passées
            past_dates = self._find_past_dates(note.content)
            for date_info in past_dates:
                if date_info.is_actionable:  # Deadline, événement...
                    obsolete.append(ObsoleteInfo(
                        note=note,
                        type="past_date",
                        excerpt=date_info.context
                    ))

            # Projets clos
            if note.type == "project":
                if self._is_project_closed(note):
                    obsolete.append(ObsoleteInfo(
                        note=note,
                        type="closed_project",
                        excerpt=note.title
                    ))

        return obsolete
```

---

## 10. Modèles de Données

### 10.1 Nouveaux Modèles

```python
# src/core/models/extraction.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class InfoType(Enum):
    """Types d'information"""
    DECISION = "decision"
    ENGAGEMENT = "engagement"
    INFORMATION = "information"
    QUESTION = "question"
    ACTION_REQUEST = "action_request"
    NOISE = "noise"

class Importance(Enum):
    """Niveaux d'importance"""
    HIGH = "haute"
    MEDIUM = "moyenne"
    LOW = "basse"

@dataclass
class ExtractedInfo:
    """Information extraite d'un événement"""
    type: InfoType
    contenu: str
    importance: Importance
    confiance: float
    source_excerpt: str
    destinations: "InfoDestinations"

    def should_auto_apply(self, threshold: float = 0.90) -> bool:
        """Détermine si l'info peut être auto-appliquée"""
        return (
            self.confiance >= threshold
            and self.importance != Importance.HIGH
        )

@dataclass
class NoteDestination:
    """Destination d'une info vers une note"""
    titre: str
    action: str  # "enrichir" | "creer"
    section: Optional[str] = None
    contenu_a_ajouter: str = ""

@dataclass
class OmniFocusTask:
    """Tâche OmniFocus à créer"""
    titre: str
    projet: Optional[str] = None
    due_date: Optional[datetime] = None
    defer_date: Optional[datetime] = None
    note: str = ""
    tags: list[str] = None

@dataclass
class InfoDestinations:
    """Destinations d'une information"""
    notes: list[NoteDestination]
    omnifocus: Optional[OmniFocusTask] = None

@dataclass
class NoteLink:
    """Lien entre deux notes"""
    source: str
    cible: str
    relation: str
    confiance: float = 1.0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class EventAction:
    """Action sur l'événement source"""
    type: str  # archive, flag, queue, delete, rien
    confiance: float
    raison: str
```

### 10.2 Modèles de Phase

```python
# src/core/models/workflow.py

@dataclass
class Phase1Result:
    """Résultat Phase 1: Perception + Extraction"""
    event: PerceivedEvent
    entities: list[Entity]
    info_type: InfoType
    info_type_confidence: float
    importance_score: float
    embedding: list[float]
    extraction_duration_ms: float

@dataclass
class NoteMatch:
    """Note matchée avec une entité"""
    note: Note
    match_type: str  # title_exact, title_fuzzy, content
    entity: Optional[Entity]
    relevance: float

@dataclass
class PatternMatch:
    """Pattern Sganarelle matché"""
    pattern_id: str
    name: str
    confidence: float
    success_rate: float
    occurrences: int
    suggested_action: str

@dataclass
class FastPathDecision:
    """Décision Fast Path"""
    eligible: bool
    reason: str
    pattern: Optional[PatternMatch] = None
    suggested_action: Optional[str] = None

@dataclass
class EnrichedEvent:
    """Événement enrichi (sortie Phase 2)"""
    phase1: Phase1Result
    matched_notes: list[NoteMatch]
    matched_patterns: list[PatternMatch]
    context_summary: str
    fast_path: FastPathDecision
    matching_duration_ms: float

@dataclass
class AnalysisResult:
    """Résultat analyse sémantique (sortie Phase 3)"""
    informations: list[ExtractedInfo]
    liens_detectes: list[NoteLink]
    action_evenement: EventAction
    resume: str
    api_usage: dict
    analysis_duration_ms: float

@dataclass
class EnrichmentResult:
    """Résultat enrichissement (sortie Phase 4)"""
    notes_created: list[str]
    notes_updated: list[str]
    links_created: list[NoteLink]
    tasks_created: list[str]
    queued_items: list[QueueItem]
    auto_applied_count: int
    queued_count: int
    enrichment_duration_ms: float

@dataclass
class WorkflowResult:
    """Résultat complet du workflow v2"""
    event_id: str
    fast_path_used: bool
    phase1: Phase1Result
    phase2: EnrichedEvent
    phase3: Optional[AnalysisResult]  # None si Fast Path
    phase4: EnrichmentResult
    phase5: ExecutionResult
    total_duration_ms: float
    api_calls: int
    api_cost_estimate: float
```

---

## 11. Configuration

### 11.1 Nouvelles Options

```yaml
# config/scapin.yaml

workflow:
  version: 2

  # Phase 1: Extraction
  extraction:
    ner_model: "urchade/gliner_medium-v2.1"
    classifier_model: "models/info_classifier"
    entity_types:
      - PERSON
      - ORGANIZATION
      - PROJECT
      - DATE
      - MONEY
      - LOCATION
      - DEADLINE
    min_entity_confidence: 0.5

  # Phase 2: Matching
  matching:
    max_notes_per_entity: 3
    max_patterns_to_check: 10
    min_note_relevance: 0.3

  # Fast Path
  fast_path:
    enabled: true
    min_pattern_confidence: 0.95
    min_pattern_success_rate: 0.90
    min_pattern_occurrences: 5
    excluded_info_types:
      - DECISION
      - ENGAGEMENT
      - ACTION_REQUEST

  # Phase 3: Analyse
  analysis:
    model: "claude-sonnet"
    max_context_tokens: 4000
    max_response_tokens: 2000

  # Phase 4: Enrichissement
  enrichment:
    auto_apply_threshold: 0.90
    auto_link_threshold: 0.85
    auto_task_threshold: 0.88
    always_review:
      - delete_note
      - merge_notes
      - high_importance

  # Phase 6: Maintenance
  maintenance:
    linking:
      enabled: true
      schedule: "0 * * * *"  # Every hour
      min_similarity: 0.7
    similarity_check:
      enabled: true
      schedule: "0 3 * * *"  # Daily at 3 AM
      merge_threshold: 0.85
    synthesis:
      enabled: true
      schedule: "0 8 * * 1"  # Weekly Monday 8 AM
      types:
        - weekly
        - project_status
    cleanup:
      enabled: true
      schedule: "0 4 * * *"  # Daily at 4 AM
      archive_after_days: 90
```

### 11.2 Variables d'Environnement

```bash
# .env

# Phase 1 - NER Local
NER_MODEL_PATH=models/gliner
NER_DEVICE=mps  # mps pour M1, cuda pour GPU, cpu sinon

# Phase 1 - Classifier Local
CLASSIFIER_MODEL_PATH=models/info_classifier

# Phase 3 - API
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-3-5-sonnet-20241022

# Phase 4 - OmniFocus
OMNIFOCUS_ENABLED=true

# Phase 6 - Maintenance
MAINTENANCE_ENABLED=true
```

---

## 12. Migration depuis v1

### 12.1 Stratégie

1. **Phase 1** : Déployer en parallèle (v1 actif, v2 en shadow mode)
2. **Phase 2** : Comparer les résultats v1 vs v2 sur 1 semaine
3. **Phase 3** : Basculer progressivement (10% → 50% → 100%)
4. **Phase 4** : Désactiver v1

### 12.2 Compatibilité

| Composant | Changement | Migration |
|-----------|-----------|-----------|
| `PerceivedEvent` | Étendu (nouveaux champs) | Backward compatible |
| `EmailAnalysis` | Remplacé par `AnalysisResult` | Adapter layer |
| `WorkingMemory` | Simplifié | Non utilisé en v2 |
| `ReasoningEngine` | Refactoré | Nouveau `SemanticAnalyzer` |
| `CognitivePipeline` | Refactoré | Nouveau `WorkflowOrchestrator` |
| Notes format | Liens ajoutés | Migration script |

### 12.3 Script de Migration Notes

```python
async def migrate_notes_to_v2():
    """
    Ajoute la structure de liens aux notes existantes
    """
    for note in note_manager.get_all_notes():
        # Ajoute section links si absente
        if "links" not in note.frontmatter:
            note.frontmatter["links"] = {
                "outgoing": [],
                "incoming": []
            }
            note.save()

    # Détecte les liens implicites (wikilinks dans le contenu)
    for note in note_manager.get_all_notes():
        wikilinks = extract_wikilinks(note.content)
        for link_target in wikilinks:
            target_note = note_manager.get_by_title(link_target)
            if target_note:
                link_manager.create_link(
                    source=note.title,
                    target=target_note.title,
                    relation="mentionne"
                )
```

---

## 13. Métriques de Succès

### 13.1 KPIs Primaires

| Métrique | Objectif | Mesure |
|----------|----------|--------|
| **Qualité extraction** | > 90% pertinence | User feedback sur infos extraites |
| **Enrichissement/jour** | > 50 notes enrichies | Compteur auto |
| **Liens créés/jour** | > 20 liens | Compteur auto |
| **Temps traitement** | < 5s moyenne | Logs |
| **Fast Path ratio** | > 40% | Compteur auto |
| **Coût API/jour** | < $5 | Usage tracking |

### 13.2 KPIs Secondaires

| Métrique | Objectif | Mesure |
|----------|----------|--------|
| **Inbox Zero atteint** | Quotidien | État queue fin de journée |
| **Tâches OmniFocus créées** | Pertinentes à 85%+ | User feedback |
| **Notes de synthèse utiles** | Score 4+/5 | User rating |
| **Faux positifs Fast Path** | < 5% | User corrections |

### 13.3 Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SCAPIN - MÉTRIQUES WORKFLOW V2                          2026-01-11        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AUJOURD'HUI                                                                │
│  ───────────                                                                │
│  Événements traités:     342 / 460 (74%)                                   │
│  Fast Path:              156 (46%)  ████████████░░░░░░░░                   │
│  Full Analysis:          186 (54%)  ██████████████████░░                   │
│                                                                             │
│  PKM ENRICHISSEMENT                                                         │
│  ──────────────────                                                         │
│  Notes créées:           12                                                 │
│  Notes enrichies:        67                                                 │
│  Liens créés:            34                                                 │
│  Tâches OmniFocus:       8                                                  │
│                                                                             │
│  PERFORMANCE                                                                │
│  ───────────                                                                │
│  Temps moyen:            3.2s (Fast: 0.4s, Full: 5.8s)                     │
│  Appels API:             186                                                │
│  Coût estimé:            $2.79                                              │
│                                                                             │
│  QUALITÉ                                                                    │
│  ───────                                                                    │
│  Auto-applied:           71%                                                │
│  En queue:               29%                                                │
│  Corrections user:       3 (0.9%)                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Annexes

### 14.1 Glossaire

| Terme | Définition |
|-------|------------|
| **Fast Path** | Traitement sans appel API (pattern connu) |
| **Full Analysis** | Traitement complet avec API Claude |
| **Enrichissement** | Ajout d'information à une note existante |
| **Linking** | Création de liens entre notes |
| **PKM** | Personal Knowledge Management |
| **NER** | Named Entity Recognition |

### 14.2 Références

- [GLiNER](https://github.com/urchade/GLiNER) - NER zero-shot
- [SetFit](https://github.com/huggingface/setfit) - Few-shot classification
- [Sentence Transformers](https://www.sbert.net/) - Embeddings
- [SM-2 Algorithm](https://www.supermemo.com/en/archives1990-2015/english/ol/sm2) - Spaced repetition

### 14.3 Historique des Versions

| Version | Date | Changements |
|---------|------|-------------|
| 2.0.0-draft | 2026-01-11 | Version initiale |

---

*Document généré le 11 janvier 2026*
