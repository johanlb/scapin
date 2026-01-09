# Migration Guide: PKM System → Scapin

**Date**: 2026-01-02
**From**: pkm-system v3.1.0
**To**: scapin v1.0.0-alpha.3

---

## 🎭 Why the Rename?

The project has evolved far beyond a "Personal Knowledge Management email processor":

**Before (PKM)**:
- Email processing tool
- Focused on inbox management
- Generic name

**After (Scapin)**:
- Intelligent personal assistant
- Cognitive architecture with reasoning
- Multi-input support (emails, files, questions, calendar)
- Named after Molière's clever valet - resourceful problem solver

---

## 🔄 Repository Migration

### Old Repository
- **URL**: https://github.com/johanlb/pkm-system
- **Status**: Archived (read-only)
- **Last Version**: v3.1.0

### New Repository
- **URL**: https://github.com/johanlb/scapin
- **Status**: Active development
- **Version**: v1.0.0-alpha (continuing from 3.1.0)

---

## 📦 Code Migration

### What Changed

#### 1. Module Names (Theme: Famous Valets)

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `src/ai/` | `src/sancho/` | Wisdom & Reasoning (Sancho Panza) |
| `src/core/email_processor` | `src/trivelin/` | Triage & Classification (Trivelin) |
| `src/core/multi_account_processor` | `src/figaro/` | Orchestration (Figaro) |
| `src/cli/` | `src/jeeves/` | Service & API Layer (Jeeves) |
| New | `src/planchet/` | Planning & Scheduling (Planchet) |
| New | `src/sganarelle/` | Learning & Adaptation (Sganarelle) |
| New | `src/passepartout/` | Navigation & Search (Passepartout) |

**Note**: Some modules remain in `src/core/` as they are shared infrastructure.

#### 2. Entry Point

```bash
# Old
python3 pkm.py

# New
python3 scapin.py
```

#### 3. Package Names (Phase 0.6 Complete ✅)

```python
# Old imports (DEPRECATED)
from src.ai.router import AIRouter
from src.core.email_processor import EmailProcessor

# New imports (Active as of 2026-01-02)
from src.sancho.router import AIRouter
from src.trivelin.processor import EmailProcessor

# Package-level exports
from src.sancho import AIRouter, get_ai_router, ModelSelector
from src.jeeves import run, InteractiveMenu, DisplayManager
from src.trivelin import EmailProcessor
```

**Current State**: ✅ Full refactor complete (Phase 0.6). All imports use new valet paths.

---

## 🛠️ Migration Steps

### For Users

If you were using PKM System:

1. **Clone new repository**:
   ```bash
   git clone https://github.com/johanlb/scapin.git
   cd scapin
   ```

2. **Copy your configuration**:
   ```bash
   # Copy .env file
   cp ../pkm-system/.env .

   # Copy data directory (optional)
   cp -r ../pkm-system/data .
   ```

3. **Install dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run**:
   ```bash
   python3 scapin.py
   ```

**Everything else works the same!** Your data, configuration, and workflows are compatible.

### For Developers

If you were developing on PKM System:

1. **Update git remote**:
   ```bash
   cd pkm-system
   git remote set-url origin https://github.com/johanlb/scapin.git
   git pull
   ```

2. **Or clone fresh**:
   ```bash
   git clone https://github.com/johanlb/scapin.git
   ```

3. **Module refactoring in progress**:
   - Current code uses old structure
   - New valet-themed modules being created
   - Gradual migration over Phase 0.6

---

## 📋 Breaking Changes

### None (Yet)

The initial migration is **fully backward compatible**:
- Same code, same structure
- Only branding and repository changed
- All imports still work

### Future Breaking Changes (Phase 0.6)

When module refactoring completes:
```python
# Will need to update imports
from src.sancho.router import AIRouter  # New
from src.trivelin.processor import EmailProcessor  # New
```

We'll provide automated migration tools when this happens.

---

## 🎯 What Stays the Same

- ✅ Configuration format (.env)
- ✅ Data storage (SQLite, Markdown, Git)
- ✅ CLI commands
- ✅ API (when implemented)
- ✅ Tests (all 525 tests still pass)
- ✅ Cognitive architecture
- ✅ Email processing logic
- ✅ Multi-account support

---

## 🚀 What's New in Scapin

1. **New Identity**:
   - Professional branding
   - Clear mission: personal assistant
   - Valet theme for modules

2. **Enhanced Documentation**:
   - README focused on assistant capabilities
   - Clearer architecture docs
   - Better onboarding

3. **Future Features** (Roadmap):
   - Web UI (Phase 0.8)
   - Mobile PWA (Phase 0.9)
   - Chat interface
   - Voice interaction

---

## ❓ FAQ

**Q: Will my PKM data work with Scapin?**
A: Yes! 100% compatible. Just copy your `data/` directory.

**Q: Do I need to change my .env configuration?**
A: No, same format.

**Q: Will PKM System still be maintained?**
A: No, it's archived. All development moves to Scapin.

**Q: Can I still use the old pkm.py script?**
A: Scapin includes a `pkm.py` → `scapin.py` symlink for compatibility (optional).

**Q: When will module names change in code?**
A: Phase 0.6 (Q1 2026). We'll announce with migration guide.

**Q: Is the cognitive architecture the same?**
A: Yes, identical. Scapin continues from PKM v3.1.0.

---

## 📞 Need Help?

- **Issues**: https://github.com/johanlb/scapin/issues
- **Discussions**: https://github.com/johanlb/scapin/discussions
- **Email**: johan.lebail@example.com

---

## 🎭 Welcome to Scapin!

The same intelligent assistant, now with a proper identity and ambitious roadmap.

**Next**: [README.md](README.md) - Learn about Scapin's capabilities
