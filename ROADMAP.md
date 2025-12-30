# Scapin - Product Roadmap

**Last Updated**: 2025-12-31
**Version**: 1.0.0-alpha (continuing from PKM v3.1.0)
**Current Phase**: Phase 0.6 (Valet Module Refactoring)

---

## 📊 Executive Summary

**Status**: ✅ **Production Ready Core** - Transitioning to Intelligent Assistant

- **Test Coverage**: 525 tests, 92% coverage, 100% pass rate
- **Code Quality**: 10/10
- **Repository**: https://github.com/johanlb/scapin
- **Previous Identity**: PKM System (archived at https://github.com/johanlb/pkm-system)

**Vision**: Transform from email processor into a complete **intelligent personal assistant** with:
- 🎭 **Valet-themed architecture** - Inspired by Molière's resourceful valet
- 🧠 **Cognitive reasoning** - Multi-pass iterative reasoning (not one-shot AI)
- 🌐 **Modern interfaces** - Web app + Mobile PWA (in addition to CLI)
- 📚 **Knowledge management** - Your personal knowledge base with semantic search
- 🔄 **Multi-modal inputs** - Emails, files, questions, calendar, documents

---

## ✅ Completed Phases (Inherited from PKM)

### Phase 0: Foundations (100% Complete) ✅

**Duration**: Weeks 1-2
**Status**: ✅ Production Ready
**Tests**: 115 tests, 95%+ coverage

#### Deliverables
- [x] Project structure and organization
- [x] Configuration management (Pydantic Settings)
- [x] Structured logging system (JSON/Text formats)
- [x] Thread-safe state management (singleton pattern)
- [x] Pydantic schemas for all data types
- [x] ABC interfaces for clean architecture
- [x] Health check system foundation
- [x] Template manager (Jinja2)
- [x] CLI framework (Typer + Rich)
- [x] Complete test suite with fixtures
- [x] CI/CD pipeline (GitHub Actions)
- [x] Pre-commit hooks (black, ruff, mypy)
- [x] Development tooling (Makefile)

---

### Phase 1: Email Processing (100% Complete) ✅

**Duration**: Weeks 3-4
**Status**: ✅ Production Ready
**Tests**: 62 tests (50 unit + 11 integration + 1 workflow), 90%+ coverage

#### Deliverables
- [x] EmailProcessor with multi-account support
- [x] AIRouter with Claude Haiku/Sonnet/Opus integration
- [x] IMAP client wrapper with UTF-8 encoding support
- [x] Batch processing with parallelization
- [x] Rate limiting and retry logic
- [x] Comprehensive error management system:
  - ErrorManager (thread-safe singleton with LRU cache)
  - ErrorStore (SQLite persistence with context managers)
  - RecoveryEngine (exponential backoff, timeout protection)
- [x] Thread-safe operations with double-check locking
- [x] Context sanitization for JSON serializability
- [x] Timeout protection (no infinite hangs)
- [x] LRU cache for memory optimization
- [x] Comprehensive test suite

---

### Phase 1.5: Event System & Display Manager (100% Complete) ✅

**Duration**: Week 5
**Status**: ✅ Production Ready
**Tests**: 44 tests (19 events + 18 display + 7 integration), 100% pass rate

#### Deliverables
- [x] Event-driven architecture (EventBus with pub/sub)
- [x] Thread-safe event system with double-check locking
- [x] ProcessingEvent with 17 event types
- [x] DisplayManager with Rich rendering:
  - Action icons: 📦 Archive, 🗑️ Delete, ✅ Task, 📚 Reference, ↩️ Reply
  - Category icons: 💼 Work, 👤 Personal, 💰 Finance, 🎨 Art, 📰 Newsletter
  - Confidence bars: ████ 95% (green) to ██░░ 55% (orange)
  - Content previews (80 chars max)
  - Progress tracking (Email 1/10, 2/10...)
- [x] Sequential display of parallel processing
- [x] Logger display mode (hide console logs during processing)

---

### Phase 1.6: Health Monitoring System (100% Complete) ✅

**Duration**: Week 5
**Status**: ✅ Production Ready
**Tests**: 31 tests, 100% pass rate, 100% coverage

#### Deliverables
- [x] Health check system with 4 services:
  - IMAP health check (connectivity, authentication)
  - AI API health check (Anthropic API, with ModelSelector)
  - Disk space health check (data directory monitoring)
  - Queue health check (review queue size tracking)
- [x] ServiceStatus enum (healthy, degraded, unhealthy, unknown)
- [x] HealthCheckService singleton with caching (60s TTL)
- [x] CLI commands (health, stats, config, settings)

---

### Phase 1.7: AI Model Selector (100% Complete) ✅

**Duration**: Week 5
**Status**: ✅ Production Ready
**Tests**: 25 tests, 100% pass rate

#### Deliverables
- [x] ModelSelector class with intelligent tier-based selection
- [x] ModelTier enum (HAIKU, SONNET, OPUS)
- [x] Dynamic model discovery via Anthropic API
- [x] Automatic selection of latest model per tier
- [x] Multi-level fallback strategy
- [x] Static fallback models ordered newest to oldest
- [x] Integration with health checks

---

### Phase 2: Interactive Menu System (80% Complete) ✅

**Status**: 🚧 Near Complete
**Tests**: 108 tests (menu, review, queue storage)

#### Completed ✅
- [x] **Interactive Menu** (questionary navigation)
  - Main menu with 6 options
  - Arrow-key navigation
  - Graceful Ctrl+C handling
  - Custom styling
- [x] **Multi-Account Support**
  - EmailAccountConfig (Pydantic model)
  - Multi-account configuration (.env format)
  - MultiAccountProcessor for sequential processing
  - Account selection UI (checkbox for batch)
  - Per-account statistics
- [x] **Review Queue System**
  - QueueStorage (JSON-based, thread-safe singleton)
  - InteractiveReviewMode with Rich UI
  - Actions: Approve/Modify/Reject/Skip
  - Queue management CLI (list, stats, clear)
  - Tracking of AI corrections for learning
- [x] **CLI Integration**
  - `python scapin.py menu` command
  - `python scapin.py` launches menu by default
  - Full backward compatibility

#### Remaining Tasks
- [ ] **Config Migration Script** (90% complete)
- [ ] **Integration Tests** (20% complete)
- [ ] **User Documentation** (30% complete)

---

## 🚧 Current Phase

### Phase 0.6: Valet Module Refactoring (0% - Q1 2026)

**Status**: 📋 Planned
**Duration**: 2-3 weeks
**Priority**: 🟡 MEDIUM
**Complexity**: 🟡 MEDIUM

#### Objectives
Refactor module structure to reflect Scapin's valet-themed architecture.

#### Module Mapping

| Current Path | New Path | Valet Name | Purpose |
|-------------|----------|------------|---------|
| `src/ai/` | `src/sancho/` | Sancho Panza | Wisdom & Reasoning (Don Quixote's wise squire) |
| `src/core/email_processor.py` | `src/trivelin/processor.py` | Trivelin | Triage & Classification (Marivaux's clever valet) |
| `src/core/multi_account_processor.py` | `src/figaro/orchestrator.py` | Figaro | Orchestration (The Barber of Seville) |
| `src/cli/` | `src/jeeves/` | Jeeves | Service & API Layer (Wodehouse's perfect butler) |
| New | `src/planchet/` | Planchet | Planning & Scheduling (D'Artagnan's resourceful servant) |
| New | `src/sganarelle/` | Sganarelle | Learning & Adaptation (Molière's recurring character) |
| New | `src/passepartout/` | Passepartout | Navigation & Search (Around the World in 80 Days) |

**Note**: `src/core/` remains for shared infrastructure (events, config, state, etc.)

#### Deliverables
- [ ] Create new valet-themed module directories
- [ ] Move and refactor existing code to new structure
- [ ] Update all import paths throughout codebase
- [ ] Automated migration script for users
- [ ] Update documentation with new architecture
- [ ] Verify all 525 tests still pass
- [ ] Create architecture diagram with valet names

#### Success Criteria
- ✅ All modules follow valet theme
- ✅ Clear separation of concerns
- ✅ Zero breaking changes for users
- ✅ All tests pass
- ✅ Documentation updated

---

## 📅 Future Phases

### Phase 0.5: Cognitive Architecture Foundation (CRITICAL - Q1 2026)

**Status**: 🏗️ Design Complete - Ready for Implementation
**Duration**: 4-5 weeks
**Priority**: 🔴 CRITICAL (Foundation for ALL future development)
**Complexity**: 🔴 VERY HIGH

#### Vision

Transform Scapin from email processor into **true cognitive assistant** with genuine reasoning capabilities.

**Core Model**: `Event → Perception → Reasoning (iterative) → Planning → Action → Learning`

#### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Max Iterations** | 5 passes (10-20s) | Balance depth vs time |
| **Confidence Threshold** | 95% | Quality over speed |
| **Context Retrieval** | Embeddings + semantic search | Best accuracy |
| **Memory Persistence** | Hybrid auto-detect continuity | Adaptive |
| **Reasoning Approach** | Iterative multi-pass | Real intelligence isn't one-shot |

#### Architecture Components

1. **Perception Layer** (→ `src/trivelin/perception.py`)
   - Universal event normalization
   - Entity extraction
   - Multi-source support (email, files, questions, documents)

2. **Working Memory** (→ `src/core/memory/working_memory.py`)
   - Short-term understanding accumulator
   - Reasoning trace across passes
   - Confidence tracking
   - Continuity detection

3. **Reasoning Engine** (→ `src/sancho/reasoning_engine.py`)
   - **Pass 1**: Initial Analysis (~60-70% confidence)
   - **Pass 2**: Context Enrichment from PKM (~75-85% confidence)
   - **Pass 3**: Deep Multi-Step Reasoning (~85-92% confidence)
   - **Pass 4**: Validation & Multi-Provider Consensus (~90-96% confidence)
   - **Pass 5**: User Clarification if needed (~95-99% confidence)
   - Stops when confidence >= 95% OR max iterations

4. **Long-Term Memory (PKM)** (→ `src/passepartout/pkm_manager.py`)
   - **READ**: Semantic search (embeddings), entity/relationship queries
   - **WRITE**: Note creation/update, entity management, Git commits
   - Technology: Markdown + YAML + sentence-transformers + FAISS + Git

5. **Planning & Decision Engine** (→ `src/planchet/planning_engine.py`)
   - Action candidate generation
   - Outcome simulation
   - Risk assessment
   - Dependency resolution (DAG)
   - Approval strategy (auto/review/manual)

6. **Action Execution Layer** (→ `src/core/actions/`)
   - Transaction-based execution
   - Parallel execution where possible
   - Rollback on failure
   - Error handling

7. **Learning & Memory Update** (→ `src/sganarelle/learning_engine.py`)
   - PKM enrichment (new notes, entities, relationships)
   - Provider accuracy tracking
   - Confidence calibration
   - Pattern learning
   - User preference models

#### Example: Complex Email Processing

```
Event: Email from accountant with budget spreadsheet

Pass 1 (3s): "Email from Marie with attachment"
  → Confidence: 65% (Who is Marie? What project?)

Pass 2 (4s): Query PKM → Marie = Accountant, Project = Q2 Budget
  → Confidence: 82% (Should I create task? Deadline?)

Pass 3 (3s): Infer deadline from previous notes (Jan 15)
  → Confidence: 89% (What folder for attachment?)

Pass 4 (4s): Consult GPT-4o → Suggests Finance/Q2 folder
  → Confidence: 94.5% (Should task be flagged?)

Pass 5 (user): Ask user about flagging → "No, normal priority"
  → Confidence: 97%

Planning: 5 ordered actions (save file, create task, update note, draft reply, archive)

Execution: All actions succeed (1.9s)

Learning: PKM updated, patterns learned, providers scored

Total: ~18s for high-quality, context-aware decision
```

#### Implementation Roadmap (5 Weeks)

**Week 1**: Core Infrastructure
- Universal Event Model
- Working Memory
- Continuity detection
- Tests

**Week 2**: Reasoning Engine
- Iterative loop (5 passes)
- Confidence tracking
- Convergence detection
- Tests

**Week 3**: Context & Memory
- PKM semantic search (embeddings)
- Entity/relationship queries
- PKM write operations
- Git integration
- Vector store (FAISS)
- Tests

**Week 4**: Planning & Execution
- Planning engine
- Action framework (base class + implementations)
- DAG-based execution
- Transaction support
- Rollback mechanism
- Tests

**Week 5**: Learning & Integration
- Learning engine
- Feedback processing
- End-to-end integration
- POC validation
- Documentation

#### Deliverables

**Code**:
- `src/core/events/` - Universal events & normalizers
- `src/core/memory/` - Working memory + continuity
- `src/sancho/reasoning_engine.py` - 5-pass reasoning
- `src/passepartout/context_queries.py` - PKM context retrieval
- `src/planchet/planning_engine.py` - Planning & risk assessment
- `src/core/actions/` - Action framework
- `src/sganarelle/learning_engine.py` - Learning engine
- `src/passepartout/pkm_manager.py` - PKM with embeddings

**Documentation**:
- ✅ `ARCHITECTURE.md` - Complete specification (inherited from PKM)
- API documentation
- Usage examples
- Reasoning flow diagrams

**Tests**:
- 100+ unit tests
- 20+ integration tests
- End-to-end POC validation
- Performance benchmarks

#### Success Criteria

- ✅ All tests pass (>90% coverage)
- ✅ POC processes 10 diverse events successfully
- ✅ Average reasoning time: 10-20s
- ✅ Confidence convergence: >90% of cases
- ✅ No infinite loops or hangs
- ✅ Performance targets met
- ✅ Documentation complete

#### Dependencies

- **Depends on**: Phase 2 completion (for review queue integration)
- **Enables**: ALL future phases (foundation for everything)
- **Integrates with**: Phase 2.5 (multi-provider used in Pass 4)

**This is the foundation that makes Scapin a true cognitive assistant.**

---

### Phase 0.7: Jeeves API Layer (NEW - Q1 2026)

**Status**: 📋 Planned
**Duration**: 3-4 weeks
**Priority**: 🟡 MEDIUM
**Complexity**: 🟡 MEDIUM

#### Objectives
Build FastAPI-based REST API to enable web and mobile interfaces.

#### Deliverables
- [ ] **FastAPI Application** (`src/jeeves/api/`)
  - RESTful API design
  - OpenAPI/Swagger documentation
  - JWT authentication
  - CORS support for web clients

- [ ] **Core Endpoints**
  - `POST /api/process/email` - Process emails
  - `GET /api/queue` - Get review queue
  - `POST /api/queue/{id}/approve` - Approve queued item
  - `POST /api/queue/{id}/modify` - Modify and execute
  - `GET /api/health` - System health
  - `GET /api/stats` - Processing statistics
  - `POST /api/reasoning/query` - Ask questions
  - `GET /api/notes` - List PKM notes
  - `GET /api/notes/{id}` - Get specific note

- [ ] **WebSocket Support**
  - Real-time processing events
  - Live updates during email processing
  - Notification system

- [ ] **Security**
  - API key authentication
  - Rate limiting
  - Input validation
  - HTTPS only (production)

#### Technology Stack
- FastAPI (Python async web framework)
- Pydantic (request/response validation)
- uvicorn (ASGI server)
- WebSockets (real-time updates)

#### Success Criteria
- ✅ All CRUD operations available via API
- ✅ Real-time updates via WebSocket
- ✅ < 100ms API response time (non-processing endpoints)
- ✅ Comprehensive API documentation
- ✅ 90%+ test coverage

#### Dependencies
- Phase 0.5 complete (cognitive architecture)
- Phase 2 complete (review queue)

---

### Phase 0.8: Web UI (NEW - Q1-Q2 2026)

**Status**: 📋 Planned
**Duration**: 6-8 weeks
**Priority**: 🔴 HIGH
**Complexity**: 🔴 HIGH

#### Objectives
Build modern web application for daily Scapin usage.

#### Deliverables
- [ ] **Frontend Application** (SvelteKit)
  - Modern, responsive UI
  - Real-time updates
  - Email processing interface
  - Review queue management
  - PKM note browser
  - Statistics dashboard
  - Settings management

- [ ] **Core Views**
  - `/dashboard` - Overview with stats
  - `/process` - Email processing interface
  - `/queue` - Review queue with approve/modify/reject
  - `/notes` - PKM knowledge base browser
  - `/search` - Semantic search interface
  - `/settings` - Account and AI configuration
  - `/health` - System health monitoring

- [ ] **Real-Time Features**
  - Live processing status
  - WebSocket-based updates
  - Progress bars and notifications
  - Confidence visualizations

- [ ] **Interactive Reasoning**
  - View reasoning trace (all 5 passes)
  - Understand AI decisions
  - Provide feedback
  - Modify and re-run

#### Technology Stack
- **Frontend**: SvelteKit (modern, fast, simple)
- **Styling**: TailwindCSS (utility-first CSS)
- **Charts**: Chart.js or D3.js
- **Icons**: Lucide or Heroicons
- **State**: Svelte stores + API client
- **Build**: Vite (fast dev server)

#### Design Principles
- **Clean & Minimal**: Focus on content, not chrome
- **Fast**: < 2s page load, instant interactions
- **Accessible**: WCAG 2.1 AA compliant
- **Responsive**: Mobile-first design

#### Success Criteria
- ✅ All CLI features available in web UI
- ✅ < 2s initial page load
- ✅ Real-time updates work smoothly
- ✅ Works on desktop, tablet, mobile
- ✅ User satisfaction: "better than CLI"

#### Dependencies
- Phase 0.7 complete (Jeeves API)
- Phase 0.5 complete (cognitive architecture)

---

### Phase 0.9: Mobile PWA (NEW - Q2 2026)

**Status**: 📋 Planned
**Duration**: 3-4 weeks
**Priority**: 🟡 MEDIUM
**Complexity**: 🟢 LOW

#### Objectives
Convert web UI into Progressive Web App for mobile use.

#### Deliverables
- [ ] **PWA Infrastructure**
  - Service Worker for offline support
  - App manifest (icons, colors, name)
  - Install prompts
  - Push notifications
  - Background sync

- [ ] **Mobile Optimizations**
  - Touch-friendly UI
  - Mobile navigation patterns
  - Offline queue management
  - Quick actions (process, review)
  - Native share integration

- [ ] **Notifications**
  - New emails ready for review
  - Processing complete
  - Review queue items
  - System alerts

#### Technology Stack
- Workbox (service worker toolkit)
- Web Push API
- Background Sync API
- Storage API (offline data)

#### Success Criteria
- ✅ Works offline (read-only)
- ✅ Install as app on iOS/Android
- ✅ Push notifications functional
- ✅ < 3s load on 3G
- ✅ Lighthouse PWA score > 90

#### Dependencies
- Phase 0.8 complete (Web UI)

---

### Phase 2.5: Multi-Provider AI System (Q2 2026)

**Status**: 📋 Planned
**Duration**: 4-5 weeks
**Priority**: 🔴 HIGH
**Complexity**: 🔴 HIGH

#### Objectives
Support multiple AI providers with intelligent consensus mechanism.

#### Deliverables
- [ ] **Provider Abstraction Layer**
  - `ClaudeProvider` (existing) ✅
  - `OpenAIProvider` (GPT-4o, GPT-4-turbo)
  - `MistralProvider` (Mistral Large/Medium/Small)
  - `GeminiProvider` (Gemini 2.0 Flash, Gemini 1.5 Pro)

- [ ] **Consensus Engine**
  - Trigger when confidence < 75%
  - Query 2-3 providers
  - Aggregate responses
  - Weighted consensus based on provider accuracy

- [ ] **Intelligent Routing**
  - Use cheapest provider for simple tasks
  - Consensus for uncertain decisions
  - Automatic failover
  - Cost tracking and optimization

- [ ] **Configuration**
  ```bash
  AI__PROVIDER_PRIORITY=anthropic,openai,mistral,google
  AI__CONSENSUS__ENABLED=true
  AI__CONSENSUS__THRESHOLD=75
  AI__MONTHLY_BUDGET_USD=100
  ```

#### Benefits
- **Resilience**: No single point of failure
- **Accuracy**: Consensus reduces errors by 10%+
- **Cost Optimization**: Choose cheapest for task
- **Future-Proof**: Easy to add new providers

#### Success Metrics
- Support for 4 AI providers ✓
- Consensus improves accuracy by 10%+ ✓
- Automatic failover < 5s latency ✓
- Cost tracking accurate within 5% ✓
- 90%+ test coverage ✓

#### Dependencies
- Phase 0.5 complete (integrates into Pass 4 of reasoning)

---

### Phase 3: Knowledge System (Q2 2026)

**Status**: 📋 Planned
**Duration**: 4-6 weeks
**Priority**: 🟡 MEDIUM
**Complexity**: 🔴 HIGH

#### Objectives
Build knowledge management system with Markdown notes, Git version control, and entity extraction.

#### Deliverables
- [ ] **NoteManager** (`src/passepartout/note_manager.py`)
  - Create, read, update, delete notes
  - YAML frontmatter support
  - Auto-linking between notes
  - Tag management
  - Search functionality

- [ ] **Git Integration**
  - Auto-commit on note changes
  - Version history tracking
  - Conflict resolution
  - Branch management

- [ ] **Context Engine** (`src/passepartout/context_engine.py`)
  - Recent notes retrieval for AI context
  - Relevant context suggestions
  - Smart search with embeddings (FAISS)
  - Context window management

- [ ] **Entity Extraction**
  - Named entity recognition (people, organizations, projects)
  - Automatic tagging
  - Entity linking to notes
  - Relationship tracking

#### Technology Stack
- Markdown files with YAML frontmatter
- Git for version control
- sentence-transformers for embeddings
- FAISS for vector search
- NetworkX for relationship graph (Phase 5)

#### Success Criteria
- 100+ notes managed
- Sub-second search
- Zero data loss
- Git history preserved
- Semantic search accuracy > 85%

#### Dependencies
- Phase 0.5 complete (cognitive architecture uses PKM)
- Phase 2 complete

---

### Phase 4: Review System with FSRS (Q2-Q3 2026)

**Status**: 📋 Planned
**Duration**: 3-4 weeks
**Priority**: 🟢 LOW
**Complexity**: 🔴 HIGH

#### Objectives
Implement spaced repetition system for knowledge review using FSRS algorithm.

#### Deliverables
- [ ] **Adaptive Review Scheduler** (FSRS algorithm)
  - Calculate optimal review intervals
  - Track memory strength per note
  - Optimize for 90%+ retention
  - Adaptive difficulty adjustment

- [ ] **Auto-Grading System**
  - Automatic assessment of recall quality
  - Difficulty adjustment based on performance
  - Performance tracking over time
  - Analytics dashboard

- [ ] **Review Agent**
  - Daily review prompts
  - Interactive review UI (web + CLI)
  - Progress visualization
  - Streak tracking

#### Success Criteria
- 90%+ retention rate
- Daily review < 10 minutes
- Adaptive scheduling works
- User engagement: daily usage

#### Dependencies
- Phase 3 complete (NoteManager)
- Phase 0.8 complete (Web UI for review interface)

---

### Phase 5: Property Graph (Q3 2026)

**Status**: 📋 Planned
**Duration**: 3-4 weeks
**Priority**: 🟢 LOW
**Complexity**: 🟡 MEDIUM

#### Objectives
Build property graph for knowledge relationships using NetworkX.

#### Deliverables
- [ ] **Graph Implementation** (NetworkX)
  - Nodes: notes, entities, emails, tasks
  - Edges: relationships, references, links
  - Graph algorithms (centrality, clustering, path finding)
  - Visualization export

- [ ] **Relation Ontology**
  - Define relationship types (mentions, references, relates_to, etc.)
  - Semantic meaning for each type
  - Bidirectional links
  - Relationship strength scoring

- [ ] **AI Link Suggestions**
  - Automatic relationship detection
  - Smart recommendations
  - Link validation
  - Graph visualization (D3.js for web UI)

#### Success Criteria
- 1000+ nodes and edges
- Sub-second graph queries
- Useful link suggestions
- Beautiful graph visualization

#### Dependencies
- Phase 3 complete (NoteManager, entities)
- Phase 0.8 complete (Web UI for visualization)

---

### Phase 6: Integrations (Q3 2026)

**Status**: 🔶 Partial (30% - OmniFocus only)
**Duration**: 4-5 weeks remaining
**Priority**: 🟢 LOW
**Complexity**: 🟡 MEDIUM

#### Completed ✅
- [x] **OmniFocus MCP Integration** (30%)
  - MCP tools available
  - Task creation from emails
  - Basic project organization

#### Remaining
- [ ] **OmniFocus - Complete** (70%)
  - Task status sync
  - Due date management
  - Project hierarchy
  - Tags and contexts

- [ ] **Apple Contacts Sync**
  - Contact enrichment from emails
  - Automatic updates
  - Bidirectional sync
  - Contact deduplication

- [ ] **Apple Calendar Integration**
  - Event extraction from emails
  - Calendar sync
  - Meeting scheduling
  - Availability checking

#### Dependencies
- Phase 2 complete
- Phase 0.5 complete (cognitive architecture for smart extraction)

---

### Phase 7: Bidirectional Sync (Q3-Q4 2026)

**Status**: 📋 Planned
**Duration**: 5-6 weeks
**Priority**: 🟢 LOW
**Complexity**: 🔴 VERY HIGH

#### Objectives
Enable bidirectional sync between Markdown notes and Apple Notes.

#### Deliverables
- [ ] **Markdown ↔ Apple Notes Sync**
  - Two-way sync
  - Format conversion (Markdown ↔ Rich Text)
  - Media handling (images, attachments)
  - Note metadata preservation

- [ ] **Conflict Resolution**
  - Timestamp-based merging
  - User conflict resolution UI
  - Version history preservation
  - Merge strategies

- [ ] **File Watcher Daemon**
  - Real-time sync on file changes
  - Efficient change detection
  - Background process management
  - Error recovery

#### Success Criteria
- Zero data loss
- < 5s sync latency
- Conflict resolution works
- Background daemon stable

#### Dependencies
- Phase 3 complete (NoteManager, Git)

---

## 📈 Overall Progress

### Phased Roadmap Overview

```
Phase 0:   ████████████████████ 100% ✅ Foundations
Phase 1:   ████████████████████ 100% ✅ Email Processing
Phase 1.5: ████████████████████ 100% ✅ Event & Display
Phase 1.6: ████████████████████ 100% ✅ Health Monitoring
Phase 1.7: ████████████████████ 100% ✅ AI Model Selector
Phase 2:   ████████████████░░░░  80% 🚧 Interactive Menu
Phase 0.6: ░░░░░░░░░░░░░░░░░░░░   0% 📋 Valet Refactor (NEW)
Phase 0.5: ░░░░░░░░░░░░░░░░░░░░   0% 🏗️ Cognitive Arch (CRITICAL)
Phase 0.7: ░░░░░░░░░░░░░░░░░░░░   0% 📋 Jeeves API (NEW)
Phase 0.8: ░░░░░░░░░░░░░░░░░░░░   0% 📋 Web UI (NEW)
Phase 0.9: ░░░░░░░░░░░░░░░░░░░░   0% 📋 Mobile PWA (NEW)
Phase 2.5: ░░░░░░░░░░░░░░░░░░░░   0% 📋 Multi-Provider AI
Phase 3:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Knowledge System
Phase 4:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 FSRS Review
Phase 5:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Property Graph
Phase 6:   ██████░░░░░░░░░░░░░░  30% 📋 Integrations
Phase 7:   ░░░░░░░░░░░░░░░░░░░░   0% 📋 Bidirectional Sync

Overall:   ██████████████░░░░░░  70% 🚀
```

### Test Coverage Evolution

| Phase | Tests | Coverage | Pass Rate | Status |
|-------|-------|----------|-----------|--------|
| Phase 0 | 115 | 95%+ | 100% | ✅ |
| Phase 1 | 62 | 90%+ | 100% | ✅ |
| Phase 1.5 | 44 | 100% | 100% | ✅ |
| Phase 1.6 | 31 | 100% | 100% | ✅ |
| Phase 1.7 | 25 | 100% | 100% | ✅ |
| Phase 2 | 108 | 85%+ | 100% | 🚧 |
| Phase 0.5 | TBD (100+) | 90%+ | - | 📋 |
| Phase 0.7-0.9 | TBD (150+) | 90%+ | - | 📋 |
| **Total** | **525** | **92%** | **100%** | **✅** |

---

## 🎯 Success Metrics

### Completed (Phase 0-2) ✅
- ✅ 10/10 code quality
- ✅ 525 tests, 92% coverage, 100% pass rate
- ✅ Zero critical bugs
- ✅ Production-ready email processing
- ✅ Beautiful event-driven UX
- ✅ Interactive menu functional
- ✅ Multi-account support operational
- ✅ Review queue system working
- ✅ Health monitoring complete
- ✅ AI model selection intelligent

### Phase 0.5 Targets (Cognitive Architecture)
- Reasoning time: 10-20s average
- Confidence convergence: >90% of cases
- Accuracy improvement: +15% vs current
- Zero infinite loops
- 100+ unit tests, 90%+ coverage

### Phase 0.7-0.9 Targets (UI Layers)
- API response time: < 100ms
- Web UI page load: < 2s
- PWA Lighthouse score: > 90
- Mobile install rate: > 50% of web users
- User satisfaction: "better than CLI"

### Long-Term (All Phases)
- Knowledge graph: 1000+ notes
- Spaced repetition retention: 90%+
- Zero data loss
- Sub-second search performance

---

## 🚀 Development Priorities

### Q1 2026 (Next 3 Months)
1. **Complete Phase 2** (Interactive Menu) - 2-3 weeks
2. **Phase 0.6** (Valet Refactoring) - 2-3 weeks
3. **Phase 0.5** (Cognitive Architecture) - 4-5 weeks ⭐ CRITICAL
4. **Begin Phase 0.7** (Jeeves API) - Start if time permits

### Q2 2026
1. **Complete Phase 0.7** (Jeeves API)
2. **Phase 0.8** (Web UI) - 6-8 weeks
3. **Phase 0.9** (Mobile PWA) - 3-4 weeks
4. **Phase 2.5** (Multi-Provider AI)
5. **Begin Phase 3** (Knowledge System)

### Q3 2026
1. **Complete Phase 3** (Knowledge System)
2. **Phase 4** (FSRS Review)
3. **Phase 5** (Property Graph)
4. **Phase 6** (Complete Integrations)

### Q4 2026
1. **Phase 7** (Bidirectional Sync)
2. **Polish & Performance Optimization**
3. **Public Beta Release**

---

## 📝 Development Principles

### Code Quality
1. **User First**: Beautiful UX is non-negotiable
2. **Quality Over Speed**: 10/10 code quality maintained
3. **Test Everything**: 90%+ coverage target
4. **Event-Driven**: Decouple backend from frontend
5. **Progressive Enhancement**: Each phase builds on previous

### Architectural Principles
1. **Valet Theme**: All modules follow the resourceful assistant metaphor
2. **Separation of Concerns**: Clear module boundaries
3. **API-First**: Jeeves API enables all interfaces
4. **Cognitive Core**: Phase 0.5 is the intelligence foundation
5. **Multi-Interface**: CLI + Web + Mobile (not CLI-only)

### Technical Stack
- **Backend**: Python 3.11+, FastAPI, Pydantic
- **Frontend**: SvelteKit, TailwindCSS, TypeScript
- **AI**: Claude (Anthropic), GPT-4o (OpenAI), Mistral, Gemini
- **Storage**: SQLite, Markdown+Git, FAISS
- **Testing**: pytest, 90%+ coverage
- **Deployment**: Docker, cloud-ready

---

## 🔗 Resources

- **GitHub Repository**: https://github.com/johanlb/scapin
- **Previous Repository**: https://github.com/johanlb/pkm-system (archived)
- **Documentation**: `README.md`, `ARCHITECTURE.md`, `MIGRATION.md`
- **Interactive Menu Plan**: `.claude/plans/abstract-puzzling-axolotl.md`

---

## 📊 Version History

- **v1.0.0-alpha** (2025-12-31): Repository migration from PKM to Scapin
  - Renamed from "PKM System" to "Scapin"
  - Established valet-themed architecture vision
  - Planned UI phases (Web + PWA)
  - Migrated 88 files and 6 open issues

- **v3.1.0** (2025-12-30): Final PKM version
  - Completed cognitive architecture design
  - 525 tests, 92% coverage
  - Production-ready email processing
  - Interactive menu system (80% complete)

---

**Status**: Phase 2 near complete → Phase 0.6 (Valet Refactor) → Phase 0.5 (Cognitive Architecture) ⭐
**Quality**: 10/10 Production Ready Core 🚀
**Tests**: 525 tests, 92% coverage, 100% pass ✅
**Next Milestone**: Complete Phase 2, refactor to valet structure, implement cognitive architecture
