# Scapin - Cognitive Architecture

**Version**: 2.1.0 (Workflow v2.1: Knowledge Extraction)
**Date**: 2026-01-11
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
> **Spec simplifiée (v2.1)**: [docs/specs/WORKFLOW_V2_SIMPLIFIED.md](docs/specs/WORKFLOW_V2_SIMPLIFIED.md)
> **Plan d'implémentation**: [docs/specs/WORKFLOW_V2_IMPLEMENTATION.md](docs/specs/WORKFLOW_V2_IMPLEMENTATION.md)

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

### Architecture 4 Phases (Simplifiée v2.1)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW V2.1 SIMPLIFIÉ                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 1: PERCEPTION                                [LOCAL]       │   │
│  │  • Normalisation → PerceivedEvent (existant)                      │   │
│  │  • Embedding sentence-transformers (existant)                     │   │
│  │  Temps: ~100ms                                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 2: CONTEXTE                                  [LOCAL]       │   │
│  │  • Recherche sémantique notes (FAISS)                             │   │
│  │  • Top 3-5 notes pertinentes comme contexte                       │   │
│  │  Temps: ~200ms                                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 3: ANALYSE                                   [API]         │   │
│  │  • 1 appel Haiku (défaut) — $0.03/événement                       │   │
│  │  • Escalade Sonnet si confidence < 0.7                            │   │
│  │  • Extraction entités + classification + action                   │   │
│  │  Temps: ~1-2s                                                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              ↓                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PHASE 4: APPLICATION                               [LOCAL]       │   │
│  │  • Enrichir notes PKM                                             │   │
│  │  • Créer tâches OmniFocus (si deadlines)                          │   │
│  │  • Exécuter action (archive/flag/queue)                           │   │
│  │  Temps: ~200ms                                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  TOTAL: ~2s par événement | COÛT: ~$36/mois (460 events/jour)           │
└─────────────────────────────────────────────────────────────────────────┘
```

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
| **Tâche** | OmniFocus + Note projet | "Envoyer rapport avant vendredi" |
| **Événement** | Note projet + Calendar | "Réunion Q2 le 15 janvier" |
| **Contact** | Note personne | "Nouveau tel: 06..." |
| **Référence** | Note concept + Lien | "Voir doc technique v2" |
| **Contexte** | Note thread | "Suite à la discussion de hier..." |

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
│  Technology: Markdown + Git + Vector DB (embeddings)       │
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
**Purpose**: Normalize diverse inputs into universal format.

**Interface**:
```python
class PerceptionLayer:
    def perceive(self, raw_event: Any) -> PerceivedEvent:
        """
        Convert raw event into standardized format.

        Args:
            raw_event: EmailMessage, File, Question, etc.

        Returns:
            PerceivedEvent with:
            - source: EventSource (email, file, question)
            - content: UniversalContent (normalized)
            - metadata: Dict[str, Any]
            - entities: List[Entity] (extracted)
            - timestamp: datetime
            - event_id: str (unique)
        """
        pass
```

**Responsibilities**:
- Event type detection
- Content extraction & normalization
- Initial entity extraction (people, dates, topics, locations)
- Metadata capture
- Event ID generation (for tracking)

**Technologies**:
- Email: IMAP parsing (existing)
- Files: MIME type detection, content extraction
- Questions: NLP preprocessing
- Documents: OCR, PDF parsing, image analysis

---

### 2. Working Memory

**Purpose**: Central hub for current reasoning state.

**Interface**:
```python
@dataclass
class WorkingMemory:
    """Short-term understanding accumulator"""

    # Event being processed
    event: PerceivedEvent

    # Current understanding (evolves across passes)
    understanding: Understanding

    # Retrieved context from PKM
    context: ContextBundle

    # Reasoning trace (all passes)
    reasoning_trace: List[ReasoningPass]

    # Hypotheses being considered
    hypotheses: List[Hypothesis]

    # Confidence scores
    confidence: ConfidenceScores

    # Open questions / uncertainties
    uncertainties: List[str]

    # Conversation history (if continuous)
    conversation_history: Optional[List[PerceivedEvent]]

    # Iteration count
    iteration: int = 0
    max_iterations: int = 5

    def is_confident(self) -> bool:
        """Check if confidence threshold met"""
        return self.confidence.overall >= 0.95

    def should_continue(self) -> bool:
        """Check if should continue reasoning"""
        return not self.is_confident() and self.iteration < self.max_iterations
```

**Persistence Strategy**:
- **Default**: Reset for each new event
- **Continuous Mode**: Detect conversation/thread continuity
  - Email threads: Same subject, related participants
  - File series: Same project, sequential naming
  - Question chains: Related topics, short time gap
- **Auto-detection**: Heuristics + ML to identify continuity

---

### 3. Sancho - Reasoning Engine

**Valet**: Sancho Panza (from Cervantes' *Don Quixote*) - The wise and practical squire who provides sound counsel
**Module**: `src/sancho/`
**Purpose**: Iterative multi-pass reasoning until confident.

**Algorithm**:
```python
class ReasoningEngine:
    def reason(self, working_memory: WorkingMemory) -> ReasoningResult:
        """
        Iterative reasoning loop.

        Max 5 passes:
        1. Initial Analysis (60-70% confidence)
        2. Context Enrichment (75-85% confidence)
        3. Deep Reasoning (85-92% confidence)
        4. Validation & Consensus (90-96% confidence)
        5. User Clarification (95-99% confidence)

        Stops when confidence >= 95% OR max iterations reached.
        """

        while working_memory.should_continue():
            pass_num = working_memory.iteration + 1

            # Execute reasoning pass
            if pass_num == 1:
                result = self._initial_analysis(working_memory)
            elif pass_num == 2:
                result = self._context_enrichment(working_memory)
            elif pass_num == 3:
                result = self._deep_reasoning(working_memory)
            elif pass_num == 4:
                result = self._validation_consensus(working_memory)
            else:  # pass_num == 5
                result = self._user_clarification(working_memory)

            # Update working memory
            working_memory.update(result)
            working_memory.iteration += 1

            # Check convergence
            if working_memory.is_confident():
                break

        return ReasoningResult(
            understanding=working_memory.understanding,
            confidence=working_memory.confidence,
            trace=working_memory.reasoning_trace
        )
```

**Pass Specifications**:

#### Pass 1: Initial Analysis
- **Input**: PerceivedEvent only
- **Process**:
  - AI analyzes raw event
  - Extracts key information
  - Generates initial hypotheses
  - No external context yet
- **Output**: Initial understanding (~60-70% confidence)
- **Time**: ~2-3 seconds

#### Pass 2: Context Enrichment
- **Input**: Initial understanding + PKM
- **Process**:
  - Identify key entities from Pass 1
  - Semantic search PKM for related notes
  - Retrieve context (notes, entities, relationships)
  - Re-analyze with full context
- **Output**: Context-aware understanding (~75-85% confidence)
- **Time**: ~3-5 seconds (includes vector search)

#### Pass 3: Deep Reasoning
- **Input**: Context-enriched understanding
- **Process**:
  - Multi-step inference chains
  - "If X then Y" reasoning
  - Check for contradictions
  - Explore alternative interpretations
  - Consider implications
- **Output**: Deep understanding (~85-92% confidence)
- **Time**: ~2-4 seconds

#### Pass 4: Validation & Consensus
- **Input**: Deep understanding
- **Process**:
  - Query second AI provider (Phase 2.5)
  - Compare analyses
  - Identify discrepancies
  - Resolve through weighted consensus
  - Generate unified understanding
- **Output**: Validated understanding (~90-96% confidence)
- **Time**: ~3-5 seconds (second AI call)

#### Pass 5: User Clarification
- **Input**: Validated but still uncertain understanding
- **Process**:
  - Identify specific uncertainties
  - Generate targeted clarifying question
  - Present to user (via Review Queue)
  - Wait for user answer
  - Incorporate answer into analysis
- **Output**: User-validated understanding (~95-99% confidence)
- **Time**: User-dependent (async)

**Total Time**: 10-20 seconds (excluding user wait in Pass 5)

---

### 4. Passepartout - Long-Term Memory

**Valet**: Passepartout (from Verne's *Around the World in 80 Days*) - The resourceful valet who can find his way anywhere
**Module**: `src/passepartout/`
**Purpose**: Bidirectional knowledge base (Read + Write).

**Interface**:
```python
class PassepartoutMemory:
    """Long-term knowledge storage"""

    # READ operations
    def semantic_search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Note]:
        """
        Semantic search using embeddings.

        Uses sentence-transformers + FAISS/ChromaDB.
        """
        pass

    def get_entity(self, entity_id: str) -> Entity:
        """Get entity by ID (person, project, topic)"""
        pass

    def get_relationships(
        self,
        entity_id: str
    ) -> List[Relationship]:
        """Get all relationships for entity"""
        pass

    def get_history(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[Event]:
        """Get event history related to entity"""
        pass

    # WRITE operations
    def create_note(self, note: Note) -> str:
        """Create new note, return note_id"""
        pass

    def update_note(self, note_id: str, updates: Dict) -> None:
        """Update existing note"""
        pass

    def add_entity(self, entity: Entity) -> str:
        """Add new entity, return entity_id"""
        pass

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str
    ) -> None:
        """Create relationship between entities"""
        pass

    def commit(self, message: str) -> None:
        """Git commit changes to knowledge base"""
        pass
```

**Storage Technology**:
- **Notes**: Markdown files with YAML frontmatter
- **Version Control**: Git (automatic commits)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2 or similar)
- **Vector Store**: FAISS (local) or ChromaDB (scalable)
- **Graph**: NetworkX (for relationships)

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
**Phase 2.5** (Multi-Provider AI) → Used in Sancho's Pass 4 (Validation & Consensus)
**Phase 3** (Knowledge System) → Implemented by Passepartout
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
**Version**: 2.1.0
**Release**: [v1.0.0-rc.1](https://github.com/johanlb/scapin/releases/tag/v1.0.0-rc.1)
**Last Updated**: 2026-01-11

🎭 *"The valet who can do anything is worth more than the master who can do nothing."* - Molière
