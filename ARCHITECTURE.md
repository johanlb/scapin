# Scapin - Cognitive Architecture

**Version**: 2.2.1 (Workflow v2.2: Multi-Pass Extraction + Atomic Transactions)
**Date**: 2026-01-12
**Status**: ✅ v1.0.0-rc.1 RELEASED — All features implemented

> Named after Scapin, Molière's cunning and resourceful valet - the perfect metaphor for an intelligent assistant that works tirelessly on your behalf.

---

## 📋 Table of Contents

- [Vision](#vision)
- [Workflow v2: Knowledge Extraction](#workflow-v2-knowledge-extraction) ⭐ NEW
- [Core Principles](#core-principles)
- [Architecture Overview](#architecture-overview)
- [Component Specifications](#component-specifications)
- [Reasoning Flow Examples](#reasoning-flow-examples)
- [Technical Decisions](#technical-decisions)
- [Implementation Roadmap](#implementation-roadmap)
- [Future Extensions](#future-extensions)

---

## 🎯 Vision

**From**: Email processor with AI classification
**To**: Personal AI Assistant with genuine cognitive capabilities

Scapin is evolving from a specialized email tool into a **universal personal assistant** that:
- Processes diverse inputs (emails, files, questions, documents)
- Reasons about them with full context awareness
- Makes intelligent decisions through iterative multi-step reasoning
- Learns continuously from outcomes and user feedback
- Acts as a true "second brain"

### Core Insight

The system follows a universal cognitive model:

```
Event → Perception → Reasoning (iterative) → Planning → Action → Learning
         ↑                                                        ↓
         └────────────────── Feedback Loop ──────────────────────┘
```

**Key**: This is NOT a linear pipeline. It's an **iterative cognitive loop** with:
- Working memory (short-term understanding)
- Long-term memory (knowledge base)
- Multi-pass reasoning until confidence threshold met
- Continuous learning and adaptation

---

## 🌟 Workflow v2: Knowledge Extraction

> **Paradigm Shift**: From "What action should I take?" to "What information can I extract?"
>
> **Spec Multi-Pass (v2.2)**: [docs/specs/archive/MULTI_PASS_SPEC.md](docs/specs/archive/MULTI_PASS_SPEC.md)
> **Spec simplifiée (v2.2)**: [docs/specs/archive/WORKFLOW_V2_SIMPLIFIED.md](docs/specs/archive/WORKFLOW_V2_SIMPLIFIED.md)
> **Plan d'implémentation**: [docs/specs/archive/WORKFLOW_V2_IMPLEMENTATION.md](docs/specs/archive/WORKFLOW_V2_IMPLEMENTATION.md)

### Vision

Le workflow v1 ("Triage") se concentrait sur la classification et les actions. Le workflow v2 ("Knowledge Extraction") inverse la priorité : **l'objectif principal est d'enrichir en permanence le PKM** (Personal Knowledge Management), avec les actions comme effet secondaire.

```
Workflow v1 (Triage)           Workflow v2 (Knowledge Extraction)
─────────────────────          ──────────────────────────────────
Event → Classification          Event → Extraction d'information
      → Action suggérée               → Enrichissement PKM
      → (optionnel) Note              → Graphe de connaissances
                                      → Actions (side effect)
```

### Architecture Multi-Pass (v2.2)

**Innovation clé** : Inversion du flux Contexte/Extraction
- v2.1 : Contexte → Extraction (recherche floue sémantique)
- v2.2 : Extraction → Contexte → Raffinement (recherche précise par entités)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW V2.2 MULTI-PASS                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PERCEPTION                                            [LOCAL]    │   │
│  │  Email → PerceivedEvent (normalisation + embedding)               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PASS 1: EXTRACTION AVEUGLE                            [HAIKU]    │   │
│  │  • Prompt SANS contexte (évite biais)                             │   │
│  │  • Extraction entités + action suggérée                           │   │
│  │  • Confiance typique: 60-80% | Coût: ~$0.0013                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 95%? │──→ OUI ──→ COHÉRENCE                          │
│            └──────┬──────┘                                              │
│                   ↓ NON                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  RECHERCHE CONTEXTUELLE (CrossSourceEngine)         [LOCAL+API]   │   │
│  │  Pour chaque entité extraite: Notes PKM, Calendar, OmniFocus,     │   │
│  │  Email archive → recherche PRÉCISE par nom d'entité               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PASS 2-3: RAFFINEMENT                                 [HAIKU]    │   │
│  │  • Extraction + Contexte trouvé                                   │   │
│  │  • Corrections: "Marc" → "Marc Dupont (CFO)"                      │   │
│  │  • Doublons: "info déjà dans note X"                              │   │
│  │  • Confiance typique: 80-95% | Coût: ~$0.0013/pass                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 90%? │──→ OUI ──→ COHÉRENCE                          │
│            └──────┬──────┘                                              │
│                   ↓ NON (conf < 80%)                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PASS 4: ESCALADE SONNET                              [SONNET]    │   │
│  │  • Raisonnement plus profond                                      │   │
│  │  • Résolution ambiguïtés complexes                                │   │
│  │  • Coût: ~$0.015                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                    │                                                     │
│            ┌──────┴──────┐                                              │
│            │ conf ≥ 90%? │──→ OUI ──→ COHÉRENCE                          │
│            └──────┬──────┘                                              │
│                   ↓ NON (conf < 75% OU high-stakes)                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PASS 5: ESCALADE OPUS                                 [OPUS]     │   │
│  │  • Raisonnement expert (ambiguïtés irréductibles)                 │   │
│  │  • High-stakes: montant > 10k€, deadline < 48h, VIP               │   │
│  │  • Si incertain: génère question clarification                    │   │
│  │  • Coût: ~$0.075                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  COHÉRENCE & VALIDATION                                [HAIKU]    │   │
│  │  • Charge contenu COMPLET des notes cibles                        │   │
│  │  • Préfère "Enrichir" si note existante                           │   │
│  │  • Détecte doublons cross-notes                                   │   │
│  │  • Identifie la section appropriée (## Header)                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  APPLICATION                                          [LOCAL]     │   │
│  │  • Enrichir notes PKM • Créer tâches/événements                   │   │
│  │  • Exécuter action (archive/flag/queue) • Apprentissage           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  DISTRIBUTION: 15% P1 | 70% P2 | 10% P3 | 4% P4 | 1% P5                 │
│  COÛT MOYEN: ~$0.0043/événement | TOTAL: ~$59/mois (13,800 emails)     │
│  CONFIANCE MOYENNE: 92%+ (vs 75% en v2.1)                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Modèle d'Escalade Haiku → Sonnet → Opus

| Pass | Modèle | Condition | Confiance attendue | Coût |
|------|--------|-----------|-------------------|------|
| 1-3 | Haiku | Par défaut | 60% → 95% | $0.0013 |
| 4 | Sonnet | conf < 80% à P3 | 80% → 95% | $0.015 |
| 5 | Opus | conf < 75% OU high-stakes | 90% → 99% | $0.075 |

**High-Stakes Detection** : Escalade automatique vers Opus si :
- Montant financier > 10,000€
- Deadline < 48 heures
- Expéditeur VIP (CEO, partenaire clé)
- Implications légales/contractuelles

### Pourquoi Pas de Fast Path ?

Haiku coûte ~$0.03/événement. La complexité d'un Fast Path ne vaut pas l'économie :

| Approche | Coût/mois | Complexité | Qualité extraction |
|----------|-----------|------------|-------------------|
| Fast Path (40% skip) | ~$22 | Haute | Variable |
| Tout Haiku | ~$36 | Basse | Constante |

**Décision** : Analyser TOUT avec Haiku, escalader vers Sonnet si incertain.

### Types d'Information Extraits

| Type | Destinations | Exemple |
|------|--------------|---------|
| **Fait** | Note personne/projet | "Marie est promue directrice" |
| **Décision** | Note projet + OmniFocus | "Budget approuvé: 50K€" |
| **Engagement** | Note personne + OmniFocus | "Marc s'engage à livrer lundi" |
| **Deadline** | OmniFocus + Note projet | "Livrer AVANT le 15 mars" |
| **Événement** | Note projet + Calendar | "Réunion Q2 le 15 janvier" |
| **Relation** | Note personne | "Marc rejoint le projet Alpha" |
| **Coordonnées** | Note personne | "Nouveau tel: 06..." |
| **Montant** | Note entreprise/projet | "Contrat de 50k€/an" |
| **Référence** | Note concept + Lien | "Voir doc technique v2" |
| **Demande** | OmniFocus (si deadline) | "Peux-tu m'envoyer le rapport ?" |
| **Citation** | Note personne | "Le CEO a dit : on double le budget" |
| **Objectif** | Note projet | "Objectif Q1 : 100k utilisateurs" |
| **Compétence** | Note personne | "Marie maîtrise React et Node.js" |
| **Préférence** | Note personne | "Marc préfère les réunions le matin" |

### Champs d'Extraction v2.1.2

Chaque extraction inclut les champs suivants :

| Champ | Type | Description |
|-------|------|-------------|
| `info` | string | Description concise (1-2 phrases) |
| `type` | enum | Type d'extraction (voir ci-dessus) |
| `importance` | enum | haute, moyenne, basse |
| `note_cible` | string | Titre de la note cible |
| `note_action` | enum | enrichir, creer |
| `omnifocus` | bool | Créer tâche OmniFocus |
| `calendar` | bool | Créer événement calendrier |
| `date` | string? | Date ISO YYYY-MM-DD |
| `time` | string? | Heure HH:MM |
| `timezone` | string? | HF (France), HM (Madagascar), Maurice, UTC, Paris |
| `duration` | int? | Durée en minutes (défaut 60) |
| `has_attachments` | bool | Pièces jointes importantes |
| `priority` | string? | Priorité OmniFocus (haute, normale, basse) |
| `project` | string? | Projet OmniFocus cible |

### Fuseaux Horaires Supportés

| Indicateur | Zone | UTC Offset |
|------------|------|------------|
| `Paris`, `HF` | Europe/Paris | +1/+2 (été) |
| `HM` | Indian/Antananarivo | +3 |
| `Maurice`, `Mauritius` | Indian/Mauritius | +4 |
| `UTC`, `GMT` | UTC | +0 |

**Règle** : Sans indication explicite, le fuseau est déduit du contexte de l'expéditeur. Par défaut Europe/Paris.

### Graphe de Connaissances

Le PKM devient un **graphe neural** avec liens bidirectionnels :

```
┌────────────────┐         ┌────────────────┐
│   Marie        │◄───────►│  Projet Alpha  │
│   (personne)   │mentions │   (projet)     │
└───────┬────────┘         └───────┬────────┘
        │                          │
        │ travaille_sur            │ deadline
        │                          │
        ▼                          ▼
┌────────────────┐         ┌────────────────┐
│  Budget Q2     │◄───────►│   15 janvier   │
│  (concept)     │         │   (date)       │
└────────────────┘         └────────────────┘
```

### Métriques de Succès

| Métrique | Objectif | Mesure |
|----------|----------|--------|
| **Coût API** | -70% | Appels API / événement |
| **Latence** | <1s (fast path), <4s (full) | Temps moyen |
| **Qualité PKM** | +50% liens | Liens créés / semaine |
| **Réponse questions** | 90% | Questions answerable depuis PKM |
| **Bruit filtré** | 95% | Infos non pertinentes ignorées |

### Migration

La migration se fait en 3 phases progressives :

1. **Phase A** : Nouveau pipeline coexiste avec l'ancien (feature flag)
2. **Phase B** : Fast Path activé, API call comme fallback
3. **Phase C** : Pipeline v2 par défaut, v1 deprecated

---

## 🎭 The Valet Team - Module Architecture

Scapin's architecture follows a valet-themed design, where each module represents a skilled servant with specific expertise:

| Module | Valet | Origin | Responsibility |
|--------|-------|--------|----------------|
| **Trivelin** | Triage & Classification | Marivaux's *L'Île des esclaves* | Perception layer - sorts and classifies events |
| **Sancho** | Wisdom & Reasoning | Cervantes' *Don Quixote* | Multi-pass reasoning engine - the wise counselor |
| **Planchet** | Planning & Scheduling | Dumas' *The Three Musketeers* | Planning engine - D'Artagnan's resourceful servant |
| **Figaro** | Orchestration | Beaumarchais' *The Barber of Seville* | Action execution - the master of coordination |
| **Sganarelle** | Learning & Adaptation | Molière's recurring character | Learning engine - adapts from experience |
| **Passepartout** | Navigation & Search | Verne's *Around the World in 80 Days* | Knowledge management - finds anything |
| **Jeeves** | Service & API | Wodehouse's stories | API layer - the perfect butler interface |

---

## 🧭 Core Principles

### 1. Quality Over Speed ⭐
**Decision**: Accept 10-20 second reasoning time for superior decisions.

**Rationale**:
- An assistant that takes 15 seconds but makes the RIGHT decision is infinitely better than one that's instant but wrong
- Users can wait for quality; they can't recover from bad decisions
- Complex reasoning REQUIRES time

### 2. Iterative Reasoning 🔄
**Decision**: Multi-pass reasoning (up to 5 iterations) until 95% confidence.

**Rationale**:
- Real intelligence isn't one-shot
- Initial analysis may be incomplete
- Context retrieval guides deeper understanding
- Each pass refines understanding

### 3. Context-Aware Intelligence 🧠
**Decision**: Semantic search with embeddings for knowledge base context retrieval.

**Rationale**:
- Keywords miss semantic relationships
- Embeddings capture meaning
- Context transforms basic AI into expert assistant
- "What you know" determines "how you decide"

### 4. Adaptive Continuity 🔗
**Decision**: Auto-detect conversation/thread continuity for Working Memory persistence.

**Rationale**:
- Email threads are conversations
- Related events need shared context
- Reset for truly independent events
- Best of stateful + stateless

### 5. Continuous Learning 📈
**Decision**: Every decision updates models, patterns, and knowledge base.

**Rationale**:
- Static assistant = stale assistant
- Learn from corrections
- Improve provider accuracy scores
- Evolve with user preferences

---

## 🏗️ Architecture Overview

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     EVENT SOURCES                           │
│  Email • Files • Questions • Documents • Calendar • Web     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              TRIVELIN - PERCEPTION LAYER                    │
│  (Triage & Classification - Marivaux's clever valet)       │
│  • Event normalization                                      │
│  • Initial classification                                   │
│  • Entity extraction                                        │
│  Output: PerceivedEvent                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              WORKING MEMORY (Central Hub)                   │
│  ┌───────────────────────────────────────────────────┐     │
│  │ Short-Term Understanding:                         │     │
│  │ • Current event state                             │     │
│  │ • Retrieved context (from Knowledge Base)         │     │
│  │ • Reasoning trace (all passes)                    │     │
│  │ • Hypotheses & inferences                         │     │
│  │ • Confidence scores per hypothesis                │     │
│  │ • Open questions / uncertainties                  │     │
│  │ • Conversation history (if continuous)            │     │
│  └───────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
              ↓ ↑ ↓ ↑ ↓ ↑  (BIDIRECTIONAL)
┌─────────────────────────────────────────────────────────────┐
│   SANCHO - REASONING ENGINE (Iterative Loop)               │
│   (Wisdom & Reasoning - Don Quixote's wise squire)         │
│  ┌───────────────────────────────────────────────────┐     │
│  │ LOOP (max 5 iterations):                          │     │
│  │                                                    │     │
│  │ Pass 1: Initial Analysis                          │     │
│  │   • What is this event?                           │     │
│  │   • Extract entities (people, dates, topics)      │     │
│  │   • Initial classification                        │     │
│  │   • Confidence: ~60-70%                          │     │
│  │                                                    │     │
│  │ IF confidence < 95%:                              │     │
│  │   Pass 2: Context Enrichment                      │     │
│  │     • Query Passepartout (semantic search)        │     │
│  │     • Retrieve related notes                      │     │
│  │     • Understand relationships                    │     │
│  │     • Re-analyze with context                     │     │
│  │     • Confidence: ~75-85%                        │     │
│  │                                                    │     │
│  │ IF confidence < 95%:                              │     │
│  │   Pass 3: Deep Reasoning                          │     │
│  │     • Multi-step inference                        │     │
│  │     • "If X then Y" chains                        │     │
│  │     • Check contradictions                        │     │
│  │     • Explore alternatives                        │     │
│  │     • Confidence: ~85-92%                        │     │
│  │                                                    │     │
│  │ IF confidence < 95%:                              │     │
│  │   Pass 4: Validation & Consensus                  │     │
│  │     • Query second AI provider (Phase 2.5)        │     │
│  │     • Compare analyses                            │     │
│  │     • Resolve discrepancies                       │     │
│  │     • Confidence: ~90-96%                        │     │
│  │                                                    │     │
│  │ IF confidence < 95%:                              │     │
│  │   Pass 5: User Clarification                      │     │
│  │     • Generate clarifying question                │     │
│  │     • Present to user (Review Queue)              │     │
│  │     • Incorporate answer                          │     │
│  │     • Final analysis                              │     │
│  │     • Confidence: ~95-99%                        │     │
│  │                                                    │     │
│  │ IF confidence >= 95% OR max_iterations:           │     │
│  │   BREAK → Proceed to Planning                     │     │
│  │                                                    │     │
│  └───────────────────────────────────────────────────┘     │
│  Output: Understanding + ConfidenceScore + Trace           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSEPARTOUT - LONG-TERM MEMORY - Bidirectional            │
│ (Navigation & Search - Verne's resourceful traveler)       │
│  ┌─────────────┐         ┌─────────────┐                   │
│  │   READ      │         │   WRITE     │                   │
│  │ • Notes     │         │ • New notes │                   │
│  │ • Entities  │ ←────→  │ • Updates   │                   │
│  │ • Relations │         │ • Relations │                   │
│  │ • History   │         │ • Learning  │                   │
│  └─────────────┘         └─────────────┘                   │
│                                                            │
│  STRATÉGIE DE PERSISTANCE ATOMIQUE :                       │
│  • Content: Markdown files (Human-readable, Git-friendly)   │
│  • Metadata: SQLite (Spaced Repetition, AI History)         │
│  • Sync: Apple Notes (Bidirectional + Smart Merge)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│    PLANCHET - PLANNING & DECISION ENGINE                    │
│    (Planning & Scheduling - D'Artagnan's servant)           │
│  1. Generate Action Candidates                              │
│     • Based on understanding + context                      │
│     • Multiple possible action plans                        │
│                                                              │
│  2. Simulate Outcomes                                        │
│     • "What if I do action A?"                              │
│     • Predict consequences                                  │
│     • Check rules/preferences                               │
│                                                              │
│  3. Risk Assessment                                          │
│     • Impact score per action                               │
│     • Reversibility (can we undo?)                          │
│     • User approval needed?                                 │
│                                                              │
│  4. Dependency Resolution                                    │
│     • Order actions (A before B)                            │
│     • Parallel vs Sequential                                │
│     • Build execution DAG                                   │
│                                                              │
│  5. Approval Logic                                           │
│     • IF high_risk OR low_confidence:                       │
│     •   → Queue for user review                             │
│     • ELSE:                                                  │
│     •   → Auto-execute (if enabled)                         │
│                                                              │
│  Output: ActionPlan (ordered, validated, approved/queued)  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         FIGARO - ACTION EXECUTION LAYER                     │
│         (Orchestration - The Barber of Seville)             │
│  • Execute actions in dependency order                      │
│  • Transaction support (atomic operations)                  │
│  • Rollback on failure                                      │
│  • Monitor execution results                                │
│  • Handle errors gracefully                                 │
│  • Track execution time & success rate                      │
│  Output: ExecutionResult (success/failure + details)       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│   SGANARELLE - LEARNING & MEMORY UPDATE LAYER               │
│   (Learning & Adaptation - Molière's recurring character)   │
│  1. Update Knowledge Base (via Passepartout)                │
│     • Create/update notes with new information              │
│     • Add entities (people, projects, concepts)             │
│     • Create relationships (links)                          │
│     • Tag and categorize                                    │
│                                                              │
│  2. Learn from Outcome                                       │
│     • Was the decision good? (implicit/explicit feedback)   │
│     • Update provider accuracy scores                       │
│     • Adjust confidence calibration                         │
│     • Learn user preferences                                │
│                                                              │
│  3. Store Decision Trace                                     │
│     • Full reasoning path (for explainability)              │
│     • Context used                                          │
│     • Confidence evolution across passes                    │
│     • Final decision rationale                              │
│                                                              │
│  4. Update Statistical Models                                │
│     • Sender importance scores                              │
│     • Category patterns                                     │
│     • Time-of-day preferences                               │
│     • Action success rates                                  │
│                                                              │
│  Output: Updated knowledge base + improved models           │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    FEEDBACK LOOP
              (Influences future events)
```

---

## 🔧 Component Specifications

### 1. Trivelin - Perception Layer

**Valet**: Trivelin (from Marivaux's *L'Île des esclaves*) - The clever valet who excels at sorting and classification
**Module**: `src/trivelin/`
**Purpose**: Normalize diverse inputs into universal `PerceivedEvent` format.

**Interface**:
```python
class Normalizer:
    def normalize(self, raw_data: Any) -> PerceivedEvent:
        """
        Convert raw source-specific data into standardized PerceivedEvent.

        Implementations: EmailNormalizer, CalendarNormalizer, TeamsNormalizer.
        """
        pass
```

**Responsibilities**:
- **Standardization**: Map source fields (subject, body, sender) to universal fields.
- **Initial Triage**: Heuristic detection of `EventType` and `UrgencyLevel`.
- **Entity Extraction**: Clean up people, locations, and dates for reasoning.
- **Traceability**: Link back to original source IDs.

**Technologies**:
- Email: IMAP parsing (existing)
- Files: MIME type detection, content extraction
- Questions: NLP preprocessing
- Documents: OCR, PDF parsing, image analysis

---

### 2. V2 Working Memory

**Purpose**: Cumulative state container for the reasoning pipeline.
**Module**: `src/core/models/v2_models.py`

**Composition (`V2WorkingMemory`):**
```python
@dataclass
class V2WorkingMemory:
    """Short-term understanding accumulator for Workflow v2"""

    event_id: str
    state: V2MemoryState  # INITIALIZED -> ANALYZING -> etc.
    
    # Context (The "Retrieval" pass)
    context_notes: List[ContextNote]
    cross_source_context: List[CrossSourceContext]

    # Validation (The "Sganarelle" pass)
    pattern_matches: List[PatternMatch]

    # Analysis (The "Reasoning" pass)
    analysis: Optional[AnalysisResult]

    # Interaction
    clarification_questions: List[ClarificationQuestion]
```

**Cycle of Life**:
1. **Initialize** with a `PerceivedEvent`.
2. **Context Enrichment**: Retrieve relevant notes and recent history.
3. **Reasoning**: Multi-pass analysis using the LLM.
4. **Validation**: Check against known patterns or historical precedents.
5. **Finalization**: Either apply results or queue for user clarification.

**Persistence Strategy**:
- **Default**: Reset for each new event
- **Continuous Mode**: Detect conversation/thread continuity
  - Email threads: Same subject, related participants
  - File series: Same project, sequential naming
  - Question chains: Related topics, short time gap
- **Auto-detection**: Heuristics + ML to identify continuity

---

### 3. Sancho - Reasoning Layer

**Valet**: Sancho (from Cervantes' *Don Quixote*) - The wise and practical squire who provides sound counsel and grounding.
**Module**: `src/sancho/`
**Purpose**: Multi-pass reasoning and extraction with intelligent model escalation.

**Key Components**:
- **MultiPassAnalyzer**: Orchestrates the reasoning flow through multiple passes (Haiku → Sonnet → Opus).
- **CoherenceValidator**: Validates extractions against existing notes (Enrichir > Créer) to prevent duplicates.
- **ContextSearcher**: Bridges Trivelin and Passepartout, providing a `StructuredContext` for reasoning.
- **DecomposedConfidence**: Evaluates understanding across four dimensions (Entity, Action, Extraction, Completeness).

**The Reasoning Flow (v2.2)**:
- **Pass 1 (Blind)**: Fast, initial extraction using Haiku without external context.
- **Pass 2-3 (Refinement)**: Context-aware refinement using Haiku + retrieved notes/entities.
- **Pass 4 (Deep)**: Escalation to Sonnet if confidence < 90% or "high-stakes" content is detected.
- **Pass 5 (Expert)**: Escalation to Opus for final consensus on complex or conflicting information.
- **Coherence Pass**: Final structural validation before committing extractions to the Knowledge Base. Operates in three modes: Extraction (validate enrichment vs creation), Maintenance (note refactoring), and Batch (duplicate detection).

**Convergence Strategy**:
Instead of fixed passes, Sancho stops when:
1. All confidence dimensions are >= 90%.
2. Analysis has converged (no significant changes between passes).
3. Maximum passes (5) are reached.

### Note Granularity: "Project-First"
Scapin prioritizes meaningful context over atomic isolation.
- **Principle**: Information is extracted into the most relevant "Project" or "Asset" note rather than creating separate notes for every person or entity.
- **Categories**:
  - **Projects (Temporaires)**: Notes with a clear start and end (e.g., "Projet Vente Nautil 6").
  - **Domaines/Actifs (Permanents)**: Ongoing context (e.g., "Nautil 6", "Santé").
  - **Contacts Stratégiques**: Individual notes only for people appearing across multiple contexts.
- **Benefit**: Reduces PKM fragmentation and preserves the "Why" behind data points.

---

### 4. Passepartout - Knowledge Foundation

**Valet**: Passepartout (from Verne's *Around the World in 80 Days*) - The resourceful valet who manages the tools and environment.
**Module**: `src/passepartout/`
**Purpose**: Long-term memory, context retrieval, and PKM maintenance.

**Key Components**:
- **ContextEngine**: Multi-strategy retrieval (Entity, Semantic, Thread, Graph).
- **NoteManager**: Managed file persistence (Markdown + Frontmatter) and vector indexing.
- **NoteReviewer**: Automated hygiene and enrichment using SM-2 spaced repetition.
- **NoteScheduler**: SM-2 algorithm implementation for adaptive review intervals.
- **NoteMetadataStore**: SQLite persistence for review states and enrichment history.

**Retrieval Strategies**:
| Strategy | Description | Innovation |
| :--- | :--- | :--- |
| **Entity** | Exact alias matching + semantic entity search | Multi-stage discovery |
| **Semantic** | FAISS-based vector search on note embeddings | 1536-dim accuracy |
| **Thread** | Relationship tracking for email/chat threads | Continuity support |
| **Graph** | Outgoing link expansion (2nd degree context) | Deep context discovery |

**Note Hygiene (SM-2)**:
Notes are scored (0-5) during review, determining their next appearance:
- **Quality 5**: Perfect, long interval.
- **Quality < 3**: Failed, reset to base interval.
- **Interval Formula**: `I(n) = I(n-1) * EF` (where EF is the Easiness Factor).
- **Auto-Apply**: High-confidence hygiene fixes (formatting, links) are applied automatically.

**Example Note Format**:
```markdown
---
id: note_20251230_143022
title: "Meeting with Marie - Q2 Budget"
created: 2025-12-30T14:30:22Z
updated: 2025-12-30T14:35:10Z
tags: [budget, q2, finance, meetings]
entities:
  - id: person_marie
    name: Marie Dupont
    role: Accountant
  - id: project_q2_budget
    name: Q2 Budget Planning
category: work
confidence: 95
source: email
source_id: email_12345
---

# Meeting Notes: Q2 Budget Discussion

Marie sent the preliminary Q2 budget spreadsheet...

## Key Points
- Revenue target: $500K
- Cost reduction: 15%
- Deadline: Jan 15

## Action Items
- [ ] Review spreadsheet by Friday
- [ ] Schedule follow-up meeting
- [ ] Get approval from director

## Related
- [[Q1 Budget Review]]
- [[Annual Financial Plan]]
```

### Metadata & Persistence Strategy

Scapin uses a **hybrid storage model** that balances human readability with machine efficiency:

1. **Markdown Payload** (`.md` files):
   - Stores the actual content and primary tags.
   - Versioned via Git for auditability and safety.
   - Uses YAML frontmatter for core properties (title, type, importance).

2. **Atomic Metadata Store** (SQLite):
   - Stores time-sensitive or high-frequency data.
   - **Scheduling**: SM-2 algorithm state (interval, easiness factor).
   - **Enrichment History**: Tracks every AI-suggested change (add, update, link) and its confidence level.
   - **Performance**: NoteManager uses an LRU cache (default 2000 notes) and SQLite WAL mode for fast concurrent access.

3. **Vector Store** (FAISS):
   - Stores embeddings for semantic search.
   - Indexed on-the-fly or loaded from `.scapin_index` cache.

### Enrichment History Schema

Each note's metadata includes an `enrichment_history` (list of `EnrichmentRecord`):
- `timestamp`: When the action was suggested.
- `action_type`: `add`, `update`, `link`, `refactor`.
- `target`: Specific section or field targeted.
- `content`: The proposed content.
- `confidence`: AI confidence score.
- `applied`: Boolean flag for auto-application.
- `reasoning`: AI explanation for the change.

---

### 5. Planchet - Planning & Decision Engine

**Valet**: Planchet (from Dumas' *The Three Musketeers*) - D'Artagnan's resourceful servant, skilled at planning and timing
**Module**: `src/planchet/`
**Purpose**: Convert understanding into executable action plan.

**Interface**:
```python
class PlanningEngine:
    def plan(
        self,
        understanding: Understanding,
        context: ContextBundle
    ) -> ActionPlan:
        """
        Generate validated action plan.

        Steps:
        1. Generate action candidates
        2. Simulate outcomes
        3. Assess risks
        4. Resolve dependencies
        5. Apply rules/preferences
        6. Determine approval strategy
        """

        # 1. Generate candidates
        candidates = self._generate_action_candidates(
            understanding,
            context
        )

        # 2. Simulate outcomes
        simulations = [
            self._simulate(action, context)
            for action in candidates
        ]

        # 3. Risk assessment
        risks = [
            self._assess_risk(action, sim)
            for action, sim in zip(candidates, simulations)
        ]

        # 4. Filter by rules
        filtered = self._apply_rules(candidates, context)

        # 5. Resolve dependencies
        ordered = self._resolve_dependencies(filtered)

        # 6. Approval strategy
        mode = self._determine_mode(ordered, risks)

        return ActionPlan(
            actions=ordered,
            mode=mode,  # auto | review | manual
            risks=risks,
            rationale=self._generate_rationale(ordered)
        )
```

**Decision Logic**:
```python
def _determine_mode(self, actions, risks):
    # High risk actions → user review
    if any(risk.level == "high" for risk in risks):
        return ExecutionMode.REVIEW

    # Low confidence → user review
    if self.confidence.overall < 0.95:
        return ExecutionMode.REVIEW

    # Irreversible actions → user review
    if any(not action.can_undo() for action in actions):
        return ExecutionMode.REVIEW

    # User preference: manual mode
    if self.user_prefs.auto_execute == False:
        return ExecutionMode.MANUAL

    # All good → auto execute
    return ExecutionMode.AUTO
```

---

### 6. Figaro - Action Execution Layer

**Valet**: Figaro (from Beaumarchais' *The Barber of Seville*) - The master of orchestration and coordination
**Module**: `src/figaro/`
**Purpose**: Execute actions with transaction support.

**Interface**:
```python
class ActionExecutor:
    def execute(self, plan: ActionPlan) -> ExecutionResult:
        """
        Execute action plan with rollback support.

        Features:
        - Dependency-aware ordering
        - Parallel execution where possible
        - Transaction support (atomic)
        - Rollback on failure
        - Error handling
        - Execution monitoring
        """

        executed = []

        try:
            # Build execution DAG
            dag = self._build_dag(plan.actions)

            # Execute in topological order
            for level in dag.levels():
                # Parallel execution within level
                results = self._execute_parallel(level)
                executed.extend(results)

            return ExecutionResult(
                success=True,
                executed=executed,
                time_taken=self.timer.elapsed()
            )

        except ActionExecutionError as e:
            # Rollback in reverse order
            self._rollback(executed)

            return ExecutionResult(
                success=False,
                error=e,
                partial_execution=executed
            )
```

**Action Interface**:
```python
from abc import ABC, abstractmethod

class Action(ABC):
    """Base class for all actions"""

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Pre-execution validation"""
        pass

    @abstractmethod
    def execute(self) -> ActionResult:
        """Execute the action"""
        pass

    @abstractmethod
    def can_undo(self) -> bool:
        """Check if action is reversible"""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Undo the action (if possible)"""
        pass

    @abstractmethod
    def estimate_impact(self) -> ImpactScore:
        """Estimate impact (for risk assessment)"""
        pass

    @abstractmethod
    def dependencies(self) -> List[str]:
        """Actions that must complete before this one"""
        pass
```

**Concrete Actions**:
```python
class UpdateContactAction(Action):
    """Update Apple Contacts"""
    pass

class CreateTaskAction(Action):
    """Create OmniFocus task"""
    pass

class UpdateNoteAction(Action):
    """Create/update knowledge base note (via Passepartout)"""
    pass

class PrepareEmailReplyAction(Action):
    """Draft email response"""
    pass

class ArchiveEmailAction(Action):
    """Move email to folder"""
    pass

class CreateCalendarEventAction(Action):
    """Create calendar event"""
    pass

class SendNotificationAction(Action):
    """Alert user"""
    pass
```

### Atomic Transaction Logic (v2.2.1)

**Module**: `src/jeeves/api/services/queue_service.py`
**Purpose**: Ensure email actions and enrichments are treated as one atomic unit.

**Problem Statement**:
Before v2.2.1, email actions (archive, flag) and enrichments (note updates) were treated as separate operations. This could lead to data loss:
- If enrichments failed after email was archived, extracted information was lost
- User had no visibility into which enrichments were critical vs optional

**Solution**: Atomic Transaction Model

```
┌─────────────────────────────────────────────────────────────────┐
│                   ATOMIC APPROVAL FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Classify Enrichments                                         │
│     ├── Required: Info would be lost if extraction fails        │
│     │   • Deadlines (toujours requis)                           │
│     │   • Haute importance: décisions, engagements, demandes    │
│     │   • Moyenne importance: engagements, demandes             │
│     └── Optional: Nice-to-have, best-effort                     │
│                                                                  │
│  2. Calculate Global Confidence                                  │
│     global_conf = min(action_conf, min(required_extraction_confs))
│                                                                  │
│  3. Execute Required Enrichments (First)                         │
│     ├── All must succeed → Continue                             │
│     └── Any failure → ABORT (don't archive, keep in queue)      │
│                                                                  │
│  4. Execute Email Action (After enrichments succeed)             │
│     • Archive/Flag/Delete only after enrichments are safe       │
│                                                                  │
│  5. Execute Optional Enrichments (Best-effort)                   │
│     • Run in background                                          │
│     • Failures logged but don't block                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Required vs Optional Classification**:

| Type Extraction | Haute Importance | Moyenne Importance | Basse Importance |
|-----------------|------------------|--------------------|--------------------|
| **Deadline** | ✅ Required | ✅ Required | ✅ Required |
| **Decision** | ✅ Required | ❌ Optional | ❌ Optional |
| **Engagement** | ✅ Required | ✅ Required | ❌ Optional |
| **Demande** | ✅ Required | ✅ Required | ❌ Optional |
| **Montant** | ✅ Required | ❌ Optional | ❌ Optional |
| **Fait** | ✅ Required | ❌ Optional | ❌ Optional |
| **Événement** | ✅ Required | ❌ Optional | ❌ Optional |
| **Autres** | ❌ Optional | ❌ Optional | ❌ Optional |

**Action Downgrade Logic**:

If required enrichments have low confidence but email action has high confidence:
- Archive → Flag (keep visible for manual review)
- This prevents data loss while still organizing inbox

**API Response Fields**:

```python
class ProposedNoteResponse(BaseModel):
    # ... existing fields ...
    required: bool = False  # Whether enrichment is required for safe archiving
    importance: str = "moyenne"  # haute, moyenne, basse
```

**UI Indication**:

Required enrichments display a "Requis" badge in the Flux interface, allowing users to understand which extractions are critical before approving.

---

### 7. Sganarelle - Learning & Memory Update Layer

**Valet**: Sganarelle (from Molière's plays) - The recurring character who learns and adapts through experience
**Module**: `src/sganarelle/`
**Purpose**: Continuous improvement through feedback.

**Interface**:
```python
class LearningEngine:
    def learn(
        self,
        event: PerceivedEvent,
        reasoning_trace: List[ReasoningPass],
        actions: List[Action],
        execution_result: ExecutionResult,
        user_feedback: Optional[UserFeedback] = None
    ) -> LearningResult:
        """
        Learn from decision outcome.

        Updates:
        1. PKM (new notes, entities, relationships)
        2. Provider accuracy scores
        3. Confidence calibration
        4. User preference models
        5. Statistical patterns
        """

        # 1. Update Knowledge Base
        kb_updates = self._update_knowledge_base(
            event,
            reasoning_trace,
            actions
        )

        # 2. Learn from feedback
        if user_feedback:
            self._learn_from_correction(
                reasoning_trace,
                user_feedback
            )

        # 3. Update provider scores
        self._update_provider_scores(
            reasoning_trace,
            execution_result,
            user_feedback
        )

        # 4. Calibrate confidence
        self._calibrate_confidence(
            reasoning_trace.confidence,
            execution_result.success,
            user_feedback
        )

        # 5. Learn patterns
        self._update_statistical_models(
            event,
            actions,
            execution_result
        )

        return LearningResult(
            knowledge_updates=kb_updates,
            model_improvements=self.improvements
        )
```

**Feedback Types**:
```python
class UserFeedback:
    """User feedback on decision"""

    # Explicit feedback
    approval: bool  # User approved/rejected
    correction: Optional[str]  # If rejected, what should have been done

    # Implicit feedback
    action_executed: bool  # Did user follow through?
    time_to_action: float  # How quickly?
    modification: Optional[Action]  # Did user modify?

    # Meta feedback
    rating: Optional[int]  # 1-5 stars
    comment: Optional[str]
```

---

### 8. Email Integration Infrastructure

**Module**: `src/integrations/email/`
**Purpose**: Robust email fetching and tracking with iCloud IMAP workarounds.

**Components**:

#### ProcessedEmailTracker (`processed_tracker.py`)

SQLite-based tracker for processed emails, necessary because iCloud IMAP doesn't support KEYWORD/UNKEYWORD search for custom flags.

```python
class ProcessedEmailTracker:
    """Track processed emails using local SQLite database."""

    def is_processed(self, message_id: str) -> bool:
        """Check if email was already processed."""

    def mark_processed(self, message_id: str, account_id: str,
                       subject: str, from_address: str) -> bool:
        """Mark email as processed in local database."""

    def get_unprocessed_message_ids(self, all_ids: list[str]) -> list[str]:
        """Filter to only unprocessed emails."""
```

**Key Design Decisions**:
- IMAP flags still added for visual feedback in email clients
- SQLite provides reliable local persistence
- Thread-safe with `check_same_thread=False`
- Batch processing with early stop for performance (1s vs 43s for 16k+ emails)

#### Folder Strategy: Single Archive Folder
**Decision**: Scapin follows a "Flat Archive" strategy to minimize organizational friction.
- **Rule**: ALL archived emails go to the root "Archive" folder (no sub-folders like "Archive/2026/Work").
- **Classification**: Emails are categorized via the `category` field (work, personal, finance, etc.) in metadata, NOT via folder hierarchy.
- **Rationale**: Search and AI-powered retrieval make deep hierarchies obsolete and counter-productive for automated systems.

#### JSON Repair Strategy (`src/sancho/router.py`)

Multi-level repair strategy for malformed LLM JSON responses:

```
Level 1: Direct parse (ideal case, fast)
    ↓ (on failure)
Level 2: json-repair library (handles complex cases)
    ↓ (on failure)
Level 3: Regex cleaning + json-repair (last resort)
```

**Technologies**:
- `json-repair` library: Robust handling of missing commas, unquoted strings, etc.
- Regex patterns: Trailing commas, markdown code blocks, comments

---

## 📝 Reasoning Flow Examples

### Example 1: Simple Email (1-2 passes)

```
EVENT: Email from "newsletter@techcrunch.com"
Subject: "TechCrunch Daily Digest - Dec 30"

─────────────────────────────────────────────────────

PASS 1: Initial Analysis (~2s)
├─ Analysis: Newsletter from TechCrunch
├─ Confidence: 85%
├─ Suggested Action: Archive to "Newsletters" folder
└─ Decision: Confidence sufficient, proceed

─────────────────────────────────────────────────────

PLANNING:
├─ Action: ArchiveEmailAction(folder="Newsletters")
├─ Risk: Low (reversible)
├─ Mode: AUTO
└─ Execute immediately

─────────────────────────────────────────────────────

EXECUTION:
├─ Archive email → Success
└─ Total time: 2.3s

─────────────────────────────────────────────────────

LEARNING:
└─ Pattern reinforced: "newsletter@techcrunch.com" → Archive
```

---

### Example 2: Complex Email (4-5 passes)

```
EVENT: Email from "marie.dupont@email.com"
Subject: "Re: Q2 Budget - Updated spreadsheet attached"
Attachment: "Q2_Budget_Final_v3.xlsx"

─────────────────────────────────────────────────────

PASS 1: Initial Analysis (~3s)
├─ Analysis: Email from Marie Dupont
│   └─ Contains: Budget spreadsheet attachment
│   └─ Seems work-related
├─ Confidence: 65%
├─ Uncertainties:
│   • Who is Marie Dupont?
│   • What project is this for?
│   • What action is expected?
└─ Decision: Need context, continue

─────────────────────────────────────────────────────

PASS 2: Context Enrichment (~4s)
├─ Passepartout Query: "Marie Dupont" + "budget" + "Q2"
├─ Retrieved Context:
│   • Entity: Marie Dupont (Accountant, Company XYZ)
│   • Note: "Q2 Budget Planning" (created last week)
│   • Relationship: Marie → Project "Q2 Financial Plan"
│   • History: 3 previous emails with Marie about budget
│
├─ Re-analysis with Context:
│   • This is follow-up to ongoing Q2 budget discussion
│   • Marie is my accountant
│   • I requested this spreadsheet last week
│   • Attachment is the updated budget I asked for
│
├─ Confidence: 82%
├─ Uncertainties:
│   • Should I review now or later?
│   • Any urgent deadline?
│   • Need to create task or just note?
└─ Decision: Still uncertain, continue

─────────────────────────────────────────────────────

PASS 3: Deep Reasoning (~3s)
├─ Multi-step Inference:
│   1. Marie sent updated spreadsheet
│   2. This means she completed her action item
│   3. Now it's my turn to review
│   4. Previous note says deadline is Jan 15
│   5. Today is Dec 30, so I have 2 weeks
│   6. This is important but not urgent
│
├─ Reasoning:
│   • Action needed: Review spreadsheet
│   • Priority: Medium (deadline in 2 weeks)
│   • Should create OmniFocus task
│   • Should update PKM note with new info
│   • Should save attachment to project folder
│
├─ Confidence: 89%
├─ Uncertainties:
│   • What folder to save attachment to?
│   • Exact task due date?
└─ Decision: Getting closer, but check with another AI

─────────────────────────────────────────────────────

PASS 4: Validation & Consensus (~4s)
├─ Query GPT-4o for second opinion
├─ GPT-4o Analysis:
│   • Agrees: Review task needed
│   • Suggests: Due date = Jan 10 (buffer before deadline)
│   • Suggests: Attachment → "Finance/Q2" folder
│   • Adds: Should acknowledge receipt to Marie
│
├─ Consensus:
│   • Both AIs agree on core understanding
│   • GPT-4o provided helpful specifics
│   • Incorporate suggestions
│
├─ Final Understanding:
│   • Create task: "Review Q2 budget spreadsheet"
│   • Due: Jan 10
│   • Save attachment: ~/Documents/Finance/Q2/
│   • Update PKM note: "Q2 Budget Planning"
│   • Prepare reply: "Thanks, will review by Jan 10"
│   • Archive email: "Finance" folder
│
├─ Confidence: 94.5%
├─ Uncertainties:
│   • Should task be flagged?
└─ Decision: Almost there, but < 95%, one more pass

─────────────────────────────────────────────────────

PASS 5: User Clarification (~user-dependent)
├─ Question to User:
│   "Should I flag the task 'Review Q2 budget' as high priority?"
│
├─ User Answer: "No, normal priority is fine"
│
├─ Final Analysis:
│   • All actions confirmed
│   • All uncertainties resolved
│
└─ Confidence: 97%

─────────────────────────────────────────────────────

PLANNING:
├─ Actions (ordered by dependencies):
│   1. SaveAttachmentAction(
│        file="Q2_Budget_Final_v3.xlsx",
│        destination="~/Documents/Finance/Q2/"
│      )
│      Dependencies: []
│
│   2. CreateTaskAction(
│        title="Review Q2 budget spreadsheet",
│        due_date="2026-01-10",
│        project="Finance",
│        note="Spreadsheet at ~/Documents/Finance/Q2/Q2_Budget_Final_v3.xlsx"
│      )
│      Dependencies: [SaveAttachmentAction]
│
│   3. UpdateNoteAction(
│        note_id="note_q2_budget_planning",
│        updates={
│          "status": "spreadsheet received",
│          "next_action": "review by Jan 10",
│          "file_location": "~/Documents/Finance/Q2/Q2_Budget_Final_v3.xlsx"
│        }
│      )
│      Dependencies: []
│
│   4. PrepareEmailReplyAction(
│        to="marie.dupont@email.com",
│        subject="Re: Q2 Budget - Updated spreadsheet",
│        body="Thanks Marie! I've received the updated spreadsheet. I'll review it and send my feedback by January 10th."
│      )
│      Dependencies: []
│
│   5. ArchiveEmailAction(
│        folder="Finance"
│      )
│      Dependencies: [All above]
│
├─ Execution DAG:
│   Level 0: SaveAttachmentAction, UpdatePKMNoteAction, PrepareEmailReplyAction
│            (can run in parallel)
│   Level 1: CreateTaskAction (depends on SaveAttachment)
│   Level 2: ArchiveEmailAction (depends on all)
│
├─ Risk Assessment:
│   • SaveAttachment: Low (reversible)
│   • CreateTask: Low (reversible via OmniFocus)
│   • UpdateNote: Low (Git versioned)
│   • PrepareReply: Low (draft, not sent)
│   • Archive: Low (reversible)
│
├─ Mode: AUTO (all low risk, high confidence)
└─ User notification: "Processing email from Marie..."

─────────────────────────────────────────────────────

EXECUTION:
├─ [Level 0 - Parallel]
│   ├─ SaveAttachmentAction → Success (0.2s)
│   ├─ UpdateNoteAction → Success (0.3s)
│   └─ PrepareEmailReplyAction → Success (0.5s)
│
├─ [Level 1]
│   └─ CreateTaskAction → Success (0.8s)
│
├─ [Level 2]
│   └─ ArchiveEmailAction → Success (0.1s)
│
└─ Total execution time: 1.9s

─────────────────────────────────────────────────────

LEARNING:
├─ Knowledge Base Updates (via Sganarelle):
│   • Note "Q2 Budget Planning" updated
│   • New attachment reference added
│   • Timeline entry: "Spreadsheet received Dec 30"
│
├─ Pattern Learning:
│   • "marie.dupont@email.com" → work contact (Accountant)
│   • Budget emails → Finance category
│   • Spreadsheet attachments → save to Documents/Finance
│
├─ Provider Scores:
│   • Claude Sonnet: Good performance (Pass 1-3)
│   • GPT-4o: Helpful specifics (Pass 4)
│   • Both get positive feedback
│
└─ Confidence Calibration:
    • 97% confidence → Success
    • Reinforces: 95%+ threshold is good

─────────────────────────────────────────────────────

TOTAL TIME: ~18s (5 passes + execution)
RESULT: ✅ Success - Email fully processed, all actions completed
```

---

## ⚙️ Technical Decisions

### Decision Log

| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| 1 | **Max 5 reasoning iterations** | Balance depth vs time (10-20s target) | ✅ Approved |
| 2 | **95% confidence threshold** | Quality-first approach, accept longer processing | ✅ Approved |
| 3 | **Embeddings for semantic search** | Best context retrieval quality | ✅ Approved |
| 4 | **Hybrid continuity detection** | Auto-detect conversation threads | ✅ Approved |
| 5 | **Bidirectional Knowledge Base** | Enable learning and knowledge growth | ✅ Approved |
| 6 | **Multi-provider consensus (Pass 4)** | Improve accuracy for uncertain cases | ✅ Approved |
| 7 | **Git for PKM version control** | Safety + auditability | ✅ Approved |
| 8 | **Transaction-based execution** | Atomic operations with rollback | ✅ Approved |
| 9 | **Local SQLite for email tracking** | iCloud IMAP doesn't support KEYWORD search | ✅ Approved |
| 10 | **Multi-level JSON repair** | LLM responses often have syntax errors | ✅ Approved |

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Fast, good quality, local |
| **Vector DB** | FAISS (initial) → ChromaDB (scale) | FAISS for simplicity, ChromaDB when needed |
| **AI Providers** | Claude (primary), GPT-4o (consensus), Mistral, Gemini | Multi-provider flexibility |
| **Knowledge Storage** | Markdown + YAML frontmatter | Human-readable, Git-friendly |
| **Version Control** | Git | Industry standard, reliable |
| **Graph** | NetworkX | Python-native, flexible |
| **Actions** | Plugin-based (ABC classes) | Extensibility |
| **Event Bus** | Existing (Phase 1.5) | Already implemented |
| **Config** | Pydantic Settings | Type-safe, validated |
| **Email Tracking** | SQLite (processed_tracker.py) | Local persistence, iCloud IMAP workaround |
| **JSON Repair** | json-repair library | Robust handling of malformed LLM responses |

### Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Reasoning Time** | 10-20s (typical) | Acceptable for quality |
| **Max Time** | 30s (worst case) | Hard limit to prevent hangs |
| **Confidence Target** | 95% | High quality decisions |
| **Pass 1 Time** | < 3s | Quick initial analysis |
| **Embedding Search** | < 1s | Fast context retrieval |
| **Action Execution** | < 2s | Quick execution |
| **Total Throughput** | 3-5 events/minute | Realistic for careful processing |

---

## 🗺️ Implementation Roadmap

### Phase 0.5: Cognitive Architecture Foundation ✅

**Timeline**: Q1 2026 (4-5 weeks)
**Priority**: 🔴 CRITICAL
**Complexity**: 🔴 HIGH
**Status**: ✅ COMPLETE (2026-01-02)

**Objective**: Implement the cognitive architecture as foundation for all future development.

#### Week 1: Core Infrastructure ✅ COMPLETE

**Deliverables**:
- [x] Universal Event Model
  - `PerceivedEvent` dataclass (IMMUTABLE - `frozen=True`)
  - `EventSource` enum
  - Event normalizers (Email, File, Question)
  - **Breaking Change**: Events are now immutable. Use `dataclasses.replace()` for modifications.

- [x] Working Memory
  - `WorkingMemory` class
  - Continuity detection logic
  - Memory persistence strategy

- [x] Tests
  - Unit tests for event model (92 tests passing)
  - Working memory tests
  - Continuity detection tests

**Files to Create**:
```
src/trivelin/                 # Perception & Triage
├── __init__.py
├── perception.py
└── normalizers/
    ├── __init__.py
    ├── email_normalizer.py
    ├── file_normalizer.py
    └── question_normalizer.py

src/core/events/              # Shared event infrastructure
├── __init__.py
├── universal_event.py
└── event_sources.py

src/core/memory/
├── __init__.py
├── working_memory.py
└── continuity_detector.py
```

#### Week 2: Reasoning Engine

**Deliverables**:
- [ ] Reasoning Engine Core
  - Iterative loop (5 passes)
  - Pass 1: Initial Analysis
  - Pass 2: Context Enrichment
  - Pass 3: Deep Reasoning

- [ ] Confidence Tracking
  - Confidence scoring
  - Threshold checking
  - Convergence detection

- [ ] Tests
  - Reasoning loop tests
  - Confidence calculation tests
  - Mock AI provider for testing

**Files to Create**:
```
src/sancho/                   # Reasoning & Wisdom
├── __init__.py
├── reasoning_engine.py
├── passes/
│   ├── __init__.py
│   ├── initial_analysis.py
│   ├── context_enrichment.py
│   ├── deep_reasoning.py
│   ├── validation_consensus.py
│   └── user_clarification.py
└── confidence.py
```

#### Week 3: Context & Memory Integration

**Deliverables**:
- [ ] PKM Context Engine
  - Semantic search (embeddings)
  - Entity retrieval
  - Relationship queries
  - History retrieval

- [ ] PKM Write Operations
  - Note creation/update
  - Entity management
  - Relationship creation
  - Git integration

- [ ] Vector Store Setup
  - FAISS initialization
  - Embedding generation
  - Index management

- [ ] Tests
  - Context query tests
  - PKM write tests
  - Vector search tests

**Files to Create**:
```
src/passepartout/             # Navigation & Search
├── __init__.py
├── knowledge_manager.py      # Main interface
├── context_engine.py         # Context retrieval for Sancho
├── note_manager.py           # Note CRUD operations
├── entity_manager.py         # Entity management
├── relationship_manager.py   # Relationship tracking
├── embeddings.py             # Vector embeddings
└── vector_store.py           # FAISS/ChromaDB integration
```

#### Week 4: Planning & Execution

**Deliverables**:
- [ ] Planning Engine
  - Action candidate generation
  - Outcome simulation
  - Risk assessment
  - Dependency resolution

- [ ] Action Framework
  - `Action` base class
  - Concrete action implementations
  - Action registry
  - Transaction support

- [ ] Execution Engine
  - DAG-based execution
  - Parallel execution
  - Rollback mechanism
  - Error handling

- [ ] Tests
  - Planning engine tests
  - Action execution tests
  - Rollback tests

**Files to Create**:
```
src/planchet/                 # Planning & Scheduling
├── __init__.py
├── planning_engine.py
├── risk_assessment.py
├── dependency_resolver.py
└── simulation.py

src/figaro/                   # Orchestration & Execution
├── __init__.py
├── orchestrator.py           # Main execution coordinator
├── action_executor.py        # DAG-based execution
└── actions/                  # Action implementations
    ├── __init__.py
    ├── base.py
    ├── registry.py
    ├── contacts.py
    ├── tasks.py
    ├── notes.py
    ├── email.py
    └── calendar.py
```

#### Week 5: Learning & Integration

**Deliverables**:
- [ ] Learning Engine
  - Feedback processing
  - Provider score updates
  - Confidence calibration
  - Pattern learning

- [ ] End-to-End Integration
  - Wire all components together
  - Full flow: Event → Learning
  - Integration tests

- [ ] POC Validation
  - Test with real emails
  - Measure performance
  - Validate convergence
  - Tune thresholds

- [ ] Documentation
  - API documentation
  - Usage examples
  - Architecture diagrams

**Files to Create**:
```
src/sganarelle/               # Learning & Adaptation
├── __init__.py
├── learning_engine.py
├── feedback_processor.py
├── calibration.py
└── pattern_learner.py

src/core/
└── scapin.py                 # Main cognitive assistant orchestrator
```

#### Success Criteria

- [ ] All unit tests pass (>90% coverage)
- [ ] Integration tests pass
- [ ] POC processes 10 diverse events successfully
- [ ] Average reasoning time: 10-20s
- [ ] Confidence convergence: >90% of cases
- [ ] No infinite loops or hangs
- [ ] Documentation complete

---

### Integration with Existing Phases

**Phase 2** (Interactive Menu) → Event source + UI for review (via Jeeves)
**Phase 0.7** (Jeeves API) → Web/Mobile interface to cognitive architecture
**Phase 3** (Knowledge System) → ✅ COMPLETE (2026-01-15)
**Phase 4** (Integration & Sync) → ✅ COMPLETE (2026-01-17)
**Phase 5** (Interaction) → In Progress
**Phase 6** (Integrations) → Additional actions for Figaro to orchestrate

### Valet Module Integration Map

```
Jeeves (API Layer)
    ↓
Trivelin (Perception) → Working Memory ← Passepartout (Knowledge)
    ↓                         ↓
Sancho (Reasoning) ←──────────┘
    ↓
Planchet (Planning)
    ↓
Figaro (Execution)
    ↓
Sganarelle (Learning) → Passepartout (Knowledge Update)
```

---

---

## 🔗 Phase 4: Integration & Sync

### Overview
Phase 4 focuses on bridging the Perception layer with External Systems, ensuring high-fidelity data flow and state synchronization. This includes the upgrade of the Email Pipeline to v2.2 and bidirectional Apple Notes synchronization.

### 📧 V2 Email Processing (Trivelin V2)
The `V2EmailProcessor` implements the full cognitive iteration loop for emails.

**Key Components**:
- **Working Memory (V2)**: Maintains state across the analysis iterations, storing intermediate reasoning and context.
- **Multi-Source Context**: Integrates `ContextEngine` (Semantic) and `CrossSourceEngine` (Entities/Patterns) for holistic understanding.
- **Pattern Validation (Sganarelle)**: Validates extracted information against learned user patterns and historical preferences.
- **Cognitive Reasoning (Sancho)**: Multi-pass extraction with model escalation (Haiku -> Sonnet) based on task complexity.

**Pipeline Flow**:
1. **Perception**: IMAP fetching/normalization.
2. **Context Enrichment**: Retrieval of relevant notes and cross-source patterns.
3. **Analysis**: Multi-pass reasoning via `MultiPassAnalyzer`.
4. **Validation**: Coherence check and pattern verification.
5. **Decision**: Auto-execution of high-confidence extractions or queuing for user review.

### 🍏 Apple Notes Synchronization
Bidirectional sync between local Scapin Markdown notes and Apple Notes via AppleScript.

**Smart Merge Strategy**:
To preserve Scapin's knowledge graph integrity, the sync engine distinguishes between "System" and "Scapin" fields.

| Category | Fields | Logic |
|----------|--------|-------|
| 🍎 **Apple System** | title, folder, created, modified | Overwritten by Apple Notes (Source of Truth for metadata) |
| 🛡️ **Scapin Protected** | type, importance, aliases, relation, pending_updates, linked_sources | **Preserved** during sync. Never overwritten by external data. |
| 📝 **Content** | Note Body | Merged using "Newer Wins" logic at the paragraph level. |

**Conflict Resolution**:
- **Newer Wins**: Changes in Apple Notes or Scapin are compared by modification date.
- **Frontmatter Preservation**: Scapin-specific YAML fields are merged carefully to prevent data loss of AI-enriched metadata.

---

## 🚀 Future Extensions

### Extension 1: Multi-Step Planning

**Enhancement**: Plan complex multi-step workflows.

**Example**:
```
Event: "Plan team offsite for Q1"

Planning:
1. Check calendar for available dates
2. Survey team preferences
3. Research venue options
4. Book venue
5. Send calendar invites
6. Create agenda document
7. Share with team
```

**Architecture Support**: Already designed for this (dependency DAG).

---

### Extension 2: Proactive Assistance

**Enhancement**: System proactively suggests actions without event trigger.

**Example**:
```
System detects:
- You have meeting with Client X tomorrow
- You haven't reviewed their proposal yet
- Proposal is in email from last week

Proactive suggestion:
"You have a meeting with Client X tomorrow at 2pm.
Would you like me to retrieve and summarize their proposal
from last week's email?"
```

**Architecture Support**:
- Working Memory can persist across sessions
- Reasoning Engine can be triggered by time/patterns

---

### Extension 3: Conversational Interface

**Enhancement**: Natural conversation with assistant.

**Example**:
```
User: "What did Marie say about the Q2 budget?"

System (using cognitive architecture):
Pass 1: Understand question (who=Marie, topic=Q2 budget)
Pass 2: Query PKM for Marie + budget
Pass 3: Retrieve relevant emails/notes
Pass 4: Synthesize answer

Response: "Marie sent the updated Q2 budget spreadsheet
on Dec 30. She confirmed the revenue target of $500K and
15% cost reduction. The deadline for your review is Jan 15."
```

**Architecture Support**: Question events already designed for this. Jeeves API (Phase 0.7) will provide the conversational interface.

#### Feature: Re-analysis (Autre)
The "Other" option in the Review Queue allows users to provide explicit instructions (e.g., "Classify in Archive/Taxes"). 
- **Workflow**: Instruction → `/reanalyze` API → Multi-pass loop with `user_instruction` injected → Updated proposal.
- **Modes**: Immediate (synchronous) or Background (queued).

---

### Extension 4: Learning from Mistakes

**Enhancement**: Explicit error correction and learning.

**Example**:
```
User correction:
"You shouldn't have archived that email from John.
He's an important client."

Learning:
- Update entity: John → importance=high, role=client
- Create rule: Emails from important clients → never auto-archive
- Adjust provider confidence for similar future cases
- Flag for review instead
```

**Architecture Support**: Learning Engine already designed for this.

---

### Extension 5: Note Hygiene Review (Planned)

**Enhancement**: Treat note review as a PerceivedEvent to leverage the entire cognitive pipeline.

**Spec complète** : [docs/specs/NOTE_HYGIENE_SPEC.md](docs/specs/NOTE_HYGIENE_SPEC.md)

**Principle**: A note review is just another event source, like email or Teams.

```
Email         → PerceivedEvent(source=email)       → Pipeline Cognitif
Teams Message → PerceivedEvent(source=teams)       → Pipeline Cognitif
Calendar      → PerceivedEvent(source=calendar)    → Pipeline Cognitif
───────────────────────────────────────────────────────────────────────
Note Review   → PerceivedEvent(source=note_review) → Pipeline Cognitif
```

**Workflow**:
```
User clicks 🧹 on note
      │
      ▼
PerceivedEvent(type=NOTE_REVIEW)
      │
      ▼
ContextEngine.retrieve_context()
  • Resolve wikilinks
  • Semantic search (FAISS)
  • Cross-source (Calendar, Teams...)
      │
      ▼
Multi-Pass Analysis (Sancho)
  • Prompt: note_review.j2
  • Detect: broken links, duplicates, inconsistencies
  • Suggest: field updates, merges, new links
      │
      ▼
Auto-apply (confidence ≥ 0.9) | Queue (confidence < 0.9)
```

**Key Architectural Decision**:
- **Reuses**: ContextEngine, EmbeddingGenerator, ReasoningEngine, CognitivePipeline, Queue
- **New**: EventType.NOTE_REVIEW, template note_review.j2, Figaro actions for notes

**Architecture Support**: Full reuse of existing cognitive architecture. Only a new event type, prompt template, and note-specific actions needed.

---

### Extension 6: Cognitive Robustness (Judge-Jury v3.0)

**Enhancement**: Diversify reasoning via consensus to achieve "critical" reliability.

**Strategies**:
- **Consensus Multi-Modèles (Judge-Jury)**: Pass 4 uses a "Devil's Advocate" model (e.g., GPT-4o) to critique the primary model's decision. If a major flaw is found, the system escalates or prompts for clarification.
- **Hallucination Detection**: Perform double-blind extractions for critical facts (dates, amounts) using a fast model (Haiku) and comparing with the primary reasoning result.

---

### Extension 7: Performance Optimization (Speculative Execution)

**Enhancement**: Reduce perceived latencies in the multi-pass pipeline.

**Strategies**:
- **Exécution Spéculative**: Launch context retrieval (Passepartout) in parallel with Pass 1 (Blind Extraction). If the pass confirms the need for context, results are already pre-fetched.
- **Contextual Pre-warming**: When a high-priority contact (VIP) is detected at the triage level, pre-load their relationship and project history into cache before analysis begins.

---

### Extension 8: Privacy Firewall

**Enhancement**: Protect sensitive data before it leaves the local environment.

**Strategies**:
- **Redaction Layer (PII Sanitization)**: Local regex or small-model filters to mask sensitive identifiers (SSN, banking info) irrelevant to the analysis.
- **Local-First Classification**: Use local models (e.g., Ollama/Llama) for trivial triage (spam, notifications) to keep 80% of low-value traffic entirely private and off-cloud.

---

### Extension 9: Technical Scalability & Quality

**Enhancement**: Ensure Scapin scales to massive knowledge bases.

**Strategies**:
- **Vector Store Abstraction**: Formalize the semantic interface to allow transparent migration from FAISS to distributed stores (ChromaDB, Qdrant) as the vault exceeds 10k+ notes.
- **Simulated User Testing (Virtual Johan)**: Automated LLM personas that send diverse email traffic to stress-test reasoning stability and detect prompt regressions.

---

## 📚 References

**Cognitive Architectures**:
- ACT-R (Adaptive Control of Thought-Rational)
- SOAR (State, Operator, And Result)
- CLARION (Connectionist Learning with Adaptive Rule Induction)

**AI Reasoning**:
- ReAct: Reasoning and Acting in Language Models (Yao et al., 2023)
- Chain-of-Thought Prompting (Wei et al., 2022)
- Tree of Thoughts (Yao et al., 2023)

**Decision Making**:
- OODA Loop (Boyd, 1976)
- Recognition-Primed Decision Model (Klein, 1993)

**Knowledge Management**:
- Zettelkasten Method
- Building a Second Brain (Forte, 2022)
- How to Take Smart Notes (Ahrens, 2017)

---

## 📞 Questions & Discussion

**This architecture represents a major evolution**. It transforms Scapin from a specialized tool into a true cognitive assistant with a team of skilled "valets" working in concert.

**Key Questions for Ongoing Discussion**:
1. Performance tuning: Adjust thresholds based on real usage?
2. Embeddings model: Upgrade to larger model for better accuracy?
3. User interface: How to visualize reasoning process?
4. Explainability: How much detail to show users?

**This is a living document**. As we implement and learn, this architecture will evolve.

---

## 🎭 Summary: The Valet Team at Work

When an event arrives (email, file, question), here's how Scapin's team responds:

1. **Trivelin** receives the event and performs initial triage
2. **Sancho** reasons about it iteratively, consulting **Passepartout** for context
3. **Planchet** devises an action plan based on Sancho's understanding
4. **Figaro** orchestrates the execution of actions in proper order
5. **Sganarelle** learns from the outcome, updating **Passepartout's** knowledge
6. **Jeeves** provides the elegant API interface for web/mobile clients

Each valet excels at their specialty, working together like a well-trained household staff.

---

**Status**: ✅ v1.0.0-rc.1 RELEASED
**Repository**: https://github.com/johanlb/scapin
**Version**: 2.2.0
**Release**: [v1.0.0-rc.1](https://github.com/johanlb/scapin/releases/tag/v1.0.0-rc.1)
**Last Updated**: 2026-01-12

🎭 *"The valet who can do anything is worth more than the master who can do nothing."* - Molière
