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

### Current Capabilities

- ✅ **Intelligent Email Processing** - AI-powered classification with multi-provider consensus
- ✅ **Multi-Account Support** - Handle multiple email accounts seamlessly
- ✅ **Interactive Review** - Validate AI decisions with elegant UI
- ✅ **Task Creation** - Auto-create OmniFocus tasks from emails
- ✅ **Knowledge Base** - Build and query your personal knowledge graph
- ✅ **Decision Learning** - Improves from corrections and feedback
- ✅ **Health Monitoring** - System-wide health checks and error recovery

### Cognitive Architecture (Phase 0.5 - In Progress)

Scapin uses a sophisticated cognitive loop:

```
Event → Perception → Reasoning (iterative) → Planning → Action → Learning
         ↑                                                        ↓
         └────────────────── Feedback Loop ──────────────────────┘
```

**Multi-Pass Reasoning**:
1. **Initial Analysis** (~70% confidence) - Quick understanding
2. **Context Enrichment** (~80% confidence) - Retrieve relevant knowledge
3. **Deep Reasoning** (~90% confidence) - Multi-step inference
4. **Validation** (~95% confidence) - Multi-provider consensus
5. **User Clarification** (~99% confidence) - Ask when uncertain

---

## 🎪 Architecture - The Valet Team

Scapin delegates to specialized "valets", each expert in their domain:

```
scapin/
├── trivelin/        # 🔍 Triage & Classification
│   └── Sorts and categorizes incoming information
│
├── planchet/        # 📅 Planning & Scheduling
│   └── Creates action plans and manages timing
│
├── sancho/          # 🧠 Wisdom & Reasoning
│   └── Deep thinking, multi-step inference, consensus
│
├── sganarelle/      # 📚 Learning & Adaptation
│   └── Learns from mistakes, improves over time
│
├── figaro/          # 🎼 Orchestration
│   └── Coordinates workflows and action execution
│
├── jeeves/          # 🎩 Service & API Layer
│   └── RESTful API, WebSockets, authentication
│
└── passepartout/    # 🧭 Navigation & Search
    └── Semantic search across knowledge base
```

Named after famous valets:
- **Scapin** - Molière's resourceful valet
- **Trivelin** - Marivaux's clever servant
- **Planchet** - D'Artagnan's faithful companion
- **Sancho Panza** - Don Quixote's wise advisor
- **Sganarelle** - Molière's learning servant
- **Figaro** - The barber who orchestrates everything
- **Jeeves** - P.G. Wodehouse's perfect butler
- **Passepartout** - Phileas Fogg's resourceful valet

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

- **[Architecture](ARCHITECTURE.md)** - Cognitive system design
- **[Breaking Changes](BREAKING_CHANGES.md)** - Migration guides
- **[API Reference](docs/api/README.md)** - Complete API documentation
- **[Roadmap](ROADMAP.md)** - Development plans

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

### 🏗️ Phase 0.5: Cognitive Architecture (In Progress - 20% Week 1)
- [x] Universal event model (immutable)
- [x] Working memory
- [x] Continuity detection
- [ ] Reasoning engine (multi-pass)
- [ ] Context engine (semantic search)
- [ ] Planning engine
- [ ] Learning engine

### 📅 Phase 0.7: Jeeves - API Layer (Q1 2026)
- [ ] FastAPI backend
- [ ] REST endpoints
- [ ] WebSockets real-time
- [ ] Authentication (JWT)
- [ ] OpenAPI documentation

### 📅 Phase 0.8: Web Interface (Q1 2026)
- [ ] Modern web UI (Svelte/SvelteKit)
- [ ] Dashboard
- [ ] Chat interface
- [ ] Review queue UI
- [ ] Settings management

### 📅 Phase 0.9: Mobile PWA (Q1 2026)
- [ ] Progressive Web App
- [ ] Responsive mobile design
- [ ] Offline support
- [ ] Push notifications
- [ ] Install as native app

### 📅 Phase 1.0: Scapin v1.0 (Q2 2026) 🎭
- [ ] Production-ready web + mobile
- [ ] Complete documentation
- [ ] Onboarding flow
- [ ] Public release

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

**Core**:
- Python 3.9+
- Pydantic (data validation)
- Typer + Rich (CLI)

**AI**:
- Claude (Anthropic) - Primary reasoning
- GPT-4o (OpenAI) - Consensus validation
- Sentence Transformers - Embeddings

**Storage**:
- Markdown + Git (knowledge base)
- FAISS/ChromaDB (vector search)
- SQLite (decision tracking)

**Integrations**:
- IMAP (email)
- OmniFocus (tasks via MCP)
- macOS Keychain (credentials)

**Future (Web UI)**:
- FastAPI (backend API)
- Svelte/SvelteKit (frontend)
- WebSockets (real-time)
- PWA (mobile)

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

Inspired by:
- **Molière** - For Scapin and the valet tradition
- **Cognitive Architectures** - ACT-R, SOAR, CLARION
- **AI Reasoning** - ReAct, Chain-of-Thought, Tree of Thoughts
- **PKM Community** - Building a Second Brain, Zettelkasten

Technology:
- **Anthropic** - Claude AI
- **OpenAI** - GPT models
- **FSRS** - Spaced repetition algorithm

---

## 📞 Contact

**Johan Le Bail**
GitHub: [@johanlb](https://github.com/johanlb)

---

**🎭 Built with intelligence and elegance - Your personal Scapin awaits.**

---

## 🔄 Migration from PKM System

If you're coming from the previous `pkm-system` repository:

1. The cognitive architecture is the same
2. Module names have changed (see Architecture section)
3. See [MIGRATION.md](MIGRATION.md) for detailed guide

The `pkm-system` repository is now archived. All future development happens here in `scapin`.
