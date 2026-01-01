# 🎭 Scapin - Your Intelligent Personal Assistant

**Version:** 1.0.0-alpha
**Status:** 🏗️ Active Development - Cognitive Architecture Foundation
**Python:** 3.9+

> Named after Scapin, Molière's cunning and resourceful valet who always finds a solution.

---

## 🎯 Vision

Scapin is not just an email processor or a task manager. It's a **cognitive personal assistant** that:

- **Perceives** diverse inputs (emails, files, questions, calendar events)
- **Reasons** about them with full context awareness and multi-step thinking
- **Decides** intelligently through iterative cognitive passes
- **Learns** continuously from outcomes and your feedback
- **Acts** as your trusted digital valet

### Core Philosophy

**Quality over speed** - Scapin takes 10-20 seconds to reason deeply, ensuring the RIGHT decision rather than a fast but wrong one.

**Context is king** - Every decision leverages your personal knowledge base, past decisions, and learned preferences.

**Transparent intelligence** - You can see Scapin's reasoning process, confidence scores, and why it made each decision.

---

## ✨ What Scapin Does

### Current Capabilities (v1.0.0-alpha)

| Feature | Status | Description |
|---------|--------|-------------|
| **Intelligent Email Processing** | ✅ Production | AI-powered classification, multi-account support, batch processing |
| **Interactive Menu System** | ✅ Production | Arrow-key navigation, account selection, review queue management |
| **Multi-Account Email** | ✅ Production | Handle unlimited email accounts with per-account configs |
| **Review Queue** | ✅ Production | Approve/modify/reject AI decisions with rich UI |
| **Task Integration** | ✅ Production | Auto-create OmniFocus tasks via MCP |
| **Event System** | ✅ Production | Thread-safe pub/sub with 17 event types |
| **Health Monitoring** | ✅ Production | IMAP, AI API, disk, queue health checks |
| **Error Recovery** | ✅ Production | Exponential backoff, timeout protection, LRU cache |
| **Decision Tracking** | ✅ Production | SQLite-based error store with context |
| **Cognitive Architecture** | 🏗️ 25% Complete | Universal events, working memory (Week 1 ✅), Week 2 starting |

**Test Coverage**: 867 tests, 95% coverage, 100% pass rate ⬆️
**Code Quality**: 10/10 (50 non-critical style warnings, down from 610)

### Cognitive Architecture (Phase 0.5 - In Progress)

Scapin uses a sophisticated **iterative cognitive loop** - not one-shot AI, but true multi-step reasoning:

```
Event → Trivelin → Sancho ↔ Passepartout → Planchet → Figaro → Sganarelle
                     ↑                                             ↓
                     └─────────── Learning Feedback ──────────────┘
```

**Sancho's Multi-Pass Reasoning** (up to 5 iterations):

| Pass | Process | Confidence Target | Time |
|------|---------|------------------|------|
| **1. Initial Analysis** | Understand the event | ~60-70% | 2-3s |
| **2. Context Enrichment** | Query Passepartout for relevant knowledge | ~75-85% | 3-5s |
| **3. Deep Reasoning** | Multi-step inference, "if X then Y" chains | ~85-92% | 2-4s |
| **4. Validation** | Multi-provider consensus (Claude + GPT-4o) | ~90-96% | 3-5s |
| **5. User Clarification** | Ask user when still uncertain | ~95-99% | async |

**Stops when**: Confidence ≥ 95% OR max iterations reached

**Total time**: 10-20 seconds for high-quality, context-aware decisions

**Example**: Email from accountant with spreadsheet
- Pass 1: "Email from Marie with attachment" (65%)
- Pass 2: Passepartout finds "Marie = Accountant, Q2 Budget project" (82%)
- Pass 3: Infers deadline from notes, plans actions (89%)
- Pass 4: GPT-4o validates, suggests folder location (94.5%)
- Pass 5: Asks user "Flag as priority?" → User: "No" (97%)
- Result: 5 actions executed perfectly (save file, create task, update note, draft reply, archive)

---

## 🎪 Architecture - The Valet Team

Scapin is built around a **valet-themed architecture** where specialized modules work together like a well-trained household staff. Each "valet" excels at their specific duty:

### The Valet Roster

| Valet | Literary Origin | Module | Specialty |
|-------|----------------|--------|-----------|
| **Trivelin** | Marivaux's *L'Île des esclaves* | `src/trivelin/` | 🔍 **Triage & Classification** - Receives and sorts all incoming events |
| **Sancho** | Cervantes' *Don Quixote* | `src/sancho/` | 🧠 **Wisdom & Reasoning** - Multi-pass iterative thinking |
| **Passepartout** | Verne's *Around the World in 80 Days* | `src/passepartout/` | 🧭 **Navigation & Search** - Finds anything in your knowledge base |
| **Planchet** | Dumas' *The Three Musketeers* | `src/planchet/` | 📅 **Planning & Scheduling** - Devises action plans |
| **Figaro** | Beaumarchais' *The Barber of Seville* | `src/figaro/` | 🎼 **Orchestration** - Executes actions in perfect coordination |
| **Sganarelle** | Molière's plays | `src/sganarelle/` | 📚 **Learning & Adaptation** - Improves from experience |
| **Jeeves** | Wodehouse's stories | `src/jeeves/` | 🎩 **Service & API** - The perfect butler interface |

### How They Work Together

When an event arrives (email, file, question), here's the workflow:

```
1. TRIVELIN receives and triages the event
        ↓
2. SANCHO reasons about it (5 passes if needed)
        ↓ ← consults → PASSEPARTOUT (knowledge base)
        ↓
3. PLANCHET creates an action plan
        ↓
4. FIGARO orchestrates the execution
        ↓
5. SGANARELLE learns from the outcome → updates PASSEPARTOUT
        ↑
6. JEEVES provides the API for web/mobile clients
```

**Directory Structure**:
```
scapin/
├── src/
│   ├── trivelin/        # Perception & triage
│   ├── sancho/          # Reasoning engine (5-pass iterative)
│   ├── passepartout/    # Knowledge base (Markdown + Git + FAISS)
│   ├── planchet/        # Planning & decision engine
│   ├── figaro/          # Action orchestration (DAG execution)
│   ├── sganarelle/      # Learning & feedback processing
│   ├── jeeves/          # API layer (FastAPI + WebSockets)
│   └── core/            # Shared infrastructure (events, config, state)
├── tests/               # 525 tests, 92% coverage
└── docs/                # Architecture, API, guides
```

**The Scapin Philosophy**: Like a valet who knows your preferences, anticipates your needs, and learns from experience - except this one reasons with AI, manages your knowledge graph, and never sleeps.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Git
- Email account (iCloud, Gmail, etc.)
- Anthropic API key (Claude)

### Installation

```bash
# Clone repository
git clone https://github.com/johanlb/scapin.git
cd scapin

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials
```

### Basic Usage

```bash
# Launch interactive menu
python3 scapin.py

# Or use CLI commands
python3 scapin.py health      # System health check
python3 scapin.py process     # Process emails
python3 scapin.py chat        # Chat with Scapin (coming soon)
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Complete cognitive architecture - how the valet team works |
| **[ROADMAP.md](ROADMAP.md)** | Development phases, priorities, timelines (Q1-Q4 2026) |
| **[MIGRATION.md](MIGRATION.md)** | Migrating from PKM System to Scapin |
| **[BREAKING_CHANGES.md](BREAKING_CHANGES.md)** | API changes and migration guides |
| **[docs/api/](docs/api/)** | API reference documentation |

**Key Concepts**:
- **Valet Architecture**: How Trivelin, Sancho, Passepartout, etc. work together
- **Multi-Pass Reasoning**: Why Scapin takes 10-20s but makes better decisions
- **Cognitive Loop**: Event → Perception → Reasoning → Planning → Action → Learning
- **Knowledge Base**: Markdown + Git + FAISS for your personal knowledge graph

---

## 🛣️ Roadmap

### ✅ Phase 0: Foundations (Complete)
- [x] Project structure and configuration
- [x] Logging and monitoring
- [x] Health checks
- [x] CLI framework

### ✅ Phase 1: Email Intelligence (Complete)
- [x] Multi-account email processing
- [x] AI-powered classification
- [x] Error management and recovery
- [x] Decision tracking

### ✅ Phase 2: Interactive Experience (Complete)
- [x] Interactive menu system
- [x] Review queue
- [x] Multi-account UI
- [x] Configuration management

### 🏗️ Phase 0.5: Cognitive Architecture (In Progress - 20% Complete)
**Valet Modules**: Trivelin, Sancho, Passepartout, Planchet, Figaro, Sganarelle

- [x] **Week 1** (Complete): Universal events, working memory, continuity detection
- [ ] **Week 2**: Sancho reasoning engine (5-pass iterative loop)
- [ ] **Week 3**: Passepartout knowledge base (embeddings + FAISS)
- [ ] **Week 4**: Planchet planning + Figaro execution (DAG-based)
- [ ] **Week 5**: Sganarelle learning engine + end-to-end integration

**Goal**: Transform from email processor into true cognitive assistant

### 📅 Phase 0.6: Valet Module Refactoring (Q1 2026)
**Goal**: Refactor codebase to match valet architecture
- [ ] Move `src/ai/` → `src/sancho/`
- [ ] Move email processor → `src/trivelin/`
- [ ] Move multi-account → `src/figaro/`
- [ ] Update all imports and tests (zero breaking changes for users)

### 📅 Phase 0.7: Jeeves - API Layer (Q1 2026)
**Valet**: Jeeves (the perfect butler interface)
- [ ] FastAPI REST API (async)
- [ ] WebSocket support (real-time events)
- [ ] JWT authentication + rate limiting
- [ ] OpenAPI/Swagger documentation
- [ ] Endpoints: `/api/process`, `/api/queue`, `/api/notes`, `/api/health`

### 📅 Phase 0.8: Web Interface (Q1-Q2 2026)
**Frontend**: SvelteKit + TailwindCSS
- [ ] Modern responsive UI (< 2s page load)
- [ ] Dashboard with statistics
- [ ] Interactive review queue
- [ ] Reasoning trace viewer (see all 5 passes)
- [ ] Knowledge base browser
- [ ] Settings management

### 📅 Phase 0.9: Mobile PWA (Q2 2026)
**Platform**: Progressive Web App
- [ ] Install on iOS/Android
- [ ] Offline support (service workers)
- [ ] Push notifications
- [ ] Native share integration
- [ ] Lighthouse PWA score > 90

### 📅 Phase 2.5: Multi-Provider AI (Q2 2026)
- [ ] OpenAI (GPT-4o, GPT-4-turbo)
- [ ] Mistral (Large, Medium, Small)
- [ ] Google (Gemini 2.0 Flash, 1.5 Pro)
- [ ] Consensus engine for uncertain decisions
- [ ] Cost tracking and optimization

### 📅 Phase 3: Knowledge System (Q2 2026)
**Valet**: Passepartout (full implementation)
- [ ] Markdown notes with Git version control
- [ ] Semantic search (sentence-transformers + FAISS)
- [ ] Entity extraction and linking
- [ ] Relationship graph (NetworkX)
- [ ] Context engine for Sancho

### 📅 Phase 1.0: Scapin v1.0 (Q3 2026) 🎭
- [ ] Production-ready CLI + Web + Mobile
- [ ] Complete cognitive architecture
- [ ] Multi-provider AI consensus
- [ ] Knowledge graph with 1000+ notes
- [ ] Public beta release

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

**Current Coverage**: 92%+ (525 tests)

---

## 🎨 Technology Stack

### Backend (Python)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.11+ | Core runtime |
| **Validation** | Pydantic Settings | Type-safe configuration |
| **CLI** | Typer + Rich | Beautiful command-line interface |
| **Testing** | pytest | 525 tests, 92% coverage |
| **Events** | Custom EventBus | Thread-safe pub/sub (Phase 1.5) |

### AI & Intelligence
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Primary AI** | Claude (Anthropic) | Sonnet 4.5 for reasoning |
| **Consensus** | GPT-4o (OpenAI) | Validation in Pass 4 |
| **Future** | Mistral, Gemini | Multi-provider support |
| **Embeddings** | sentence-transformers | Semantic search (all-MiniLM-L6-v2) |
| **Vector DB** | FAISS → ChromaDB | Fast similarity search |

### Knowledge & Storage
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Notes** | Markdown + YAML | Human-readable knowledge base |
| **Versioning** | Git | Automatic commits, full history |
| **Decisions** | SQLite | Error tracking, state management |
| **Graph** | NetworkX | Relationship mapping (Phase 5) |

### Integrations
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Email** | IMAP | Multi-account email processing |
| **Tasks** | OmniFocus MCP | Task creation and management |
| **Credentials** | macOS Keychain | Secure credential storage |
| **Apple Contacts** | Planned | Contact enrichment |
| **Calendar** | Planned | Event extraction |

### Web & API (Planned)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Backend** | FastAPI | Async REST + WebSockets (Jeeves) |
| **Frontend** | SvelteKit | Modern web UI (Phase 0.8) |
| **Styling** | TailwindCSS | Utility-first CSS |
| **Mobile** | PWA | Progressive Web App (Phase 0.9) |
| **Auth** | JWT | Secure authentication |
| **Build** | Vite | Fast development server |

**Design Philosophy**: Fast, type-safe, tested, production-ready

---

## 🤝 Contributing

This is currently a personal project, but feedback and suggestions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes (maintain test coverage)
4. Run tests: `make test`
5. Submit a pull request

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

### Literary Inspiration
- **Molière** - Scapin, Sganarelle (*Les Fourberies de Scapin*, *Dom Juan*)
- **Marivaux** - Trivelin (*L'Île des esclaves*)
- **Cervantes** - Sancho Panza (*Don Quixote*)
- **Dumas** - Planchet (*The Three Musketeers*)
- **Beaumarchais** - Figaro (*The Barber of Seville*)
- **Wodehouse** - Jeeves (*My Man Jeeves*)
- **Verne** - Passepartout (*Around the World in 80 Days*)

### Technical Inspiration
- **Cognitive Architectures** - ACT-R, SOAR, CLARION
- **AI Reasoning** - ReAct (Yao et al.), Chain-of-Thought (Wei et al.), Tree of Thoughts
- **Decision Making** - OODA Loop (Boyd), Recognition-Primed Decision (Klein)
- **PKM Community** - Building a Second Brain (Forte), Zettelkasten Method

### Technology
- **Anthropic** - Claude AI (Sonnet 4.5, Opus 4.5)
- **OpenAI** - GPT-4o, GPT-4-turbo
- **sentence-transformers** - Semantic embeddings
- **FSRS** - Spaced repetition algorithm

---

## 📞 Contact

**Johan Le Bail**
GitHub: [@johanlb](https://github.com/johanlb)

---

---

## 🔄 Migration from PKM System

If you're coming from the previous **pkm-system** repository:

| Aspect | PKM System | Scapin |
|--------|-----------|--------|
| **Identity** | Email processor | Cognitive personal assistant |
| **Modules** | Generic (`src/ai/`, `src/core/`) | Valet-themed (`src/sancho/`, `src/trivelin/`) |
| **Version** | v3.1.0 (final) | v1.0.0-alpha (continuing) |
| **Repository** | [Archived](https://github.com/johanlb/pkm-system) | [Active](https://github.com/johanlb/scapin) |
| **Architecture** | ✅ Same cognitive design | ✅ Inherited + enhanced |
| **Data** | ✅ 100% compatible | ✅ Just copy `.env` and `data/` |
| **Tests** | 525 tests, 92% coverage | ✅ All passing |

**Migration Steps**:
1. Clone Scapin: `git clone https://github.com/johanlb/scapin.git`
2. Copy config: `cp ../pkm-system/.env .`
3. Copy data: `cp -r ../pkm-system/data .` (optional)
4. Run: `python3 scapin.py`

See **[MIGRATION.md](MIGRATION.md)** for complete details.

---

**🎭 Built with intelligence and elegance - Your personal Scapin awaits.**

*"The valet who can do anything is worth more than the master who can do nothing."* - Molière
