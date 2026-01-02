# Breaking Changes - Scapin

**Last Updated**: 2026-01-02

This document tracks all breaking changes introduced in Scapin (formerly PKM System), including migration guides.

---

## Version 1.0.0-alpha.3 (2026-01-02) - Phase 0.6 Valet Architecture Migration

### 🔴 CRITICAL: Module Path Changes

**Breaking Change**: Major module reorganization following valet architecture.

#### AI Module Migration

```python
# ❌ Old imports (BROKEN)
from src.ai.router import AIRouter, get_ai_router
from src.ai.model_selector import ModelSelector
from src.ai.templates import TemplateManager, get_template_manager

# ✅ New imports (CORRECT)
from src.sancho.router import AIRouter, get_ai_router
from src.sancho.model_selector import ModelSelector
from src.sancho.templates import TemplateManager, get_template_manager

# Or use the package exports:
from src.sancho import AIRouter, get_ai_router, ModelSelector, TemplateManager
```

#### CLI Module Migration

```python
# ❌ Old imports (BROKEN)
from src.cli.app import run
from src.cli.display_manager import DisplayManager
from src.cli.menu import InteractiveMenu

# ✅ New imports (CORRECT)
from src.jeeves.cli import run
from src.jeeves.display_manager import DisplayManager
from src.jeeves.menu import InteractiveMenu

# Or use the package exports:
from src.jeeves import run, DisplayManager, InteractiveMenu
```

#### Email Processor Migration

```python
# ❌ Old import (BROKEN)
from src.core.email_processor import EmailProcessor

# ✅ New import (CORRECT)
from src.trivelin.processor import EmailProcessor

# Or use the package export:
from src.trivelin import EmailProcessor
```

**Why**: Aligning code structure with the valet architecture (Sancho = AI/Reasoning, Jeeves = Interface, Trivelin = Perception).

---

## Version 3.1.0 (2025-12-31) - Phase 0.5 Week 1 Fixes

### 🔴 CRITICAL: PerceivedEvent is Now Immutable

**Breaking Change**: `PerceivedEvent` dataclass is now frozen (immutable).

```python
@dataclass(frozen=True)  # ← New: frozen=True
class PerceivedEvent:
    """Universal event representation (Immutable)"""
    # ... fields
```

**Why**: Data integrity and thread safety. Immutable events prevent accidental modification during processing.

**Migration Guide**:

❌ **Old Code (BROKEN)**:
```python
event = PerceivedEvent(...)

# This will raise FrozenInstanceError
event.perception_confidence = 0.95  # ❌ Error!
event.entities.append(new_entity)    # ❌ Error!
```

✅ **New Code (CORRECT)**:
```python
from dataclasses import replace

event = PerceivedEvent(...)

# Create a new event with modified field
modified_event = replace(event, perception_confidence=0.95)

# For complex modifications, unpack existing values
modified_event = replace(
    event,
    entities=event.entities + [new_entity],  # Create new list
    topics=event.topics + ["new topic"]
)
```

**Impact**:
- All code that modifies `PerceivedEvent` after creation
- Tests that relied on mutation
- Processors that incrementally built events

**Files Affected**:
- `src/core/events/universal_event.py` - Event definition
- `tests/unit/test_working_memory.py` - Fixed in commit ac5f01f

**Related Issues**: [#8](https://github.com/johanlb/pkm-system/issues/8) (Fixed)

---

### 🟡 MEDIUM: EmailAnalysis Confidence Validation

**Breaking Change**: `EmailAnalysis.confidence` now raises `ValueError` instead of silently clamping invalid values.

**Before** (Phase 1):
```python
# Silently clamped to 0-100 range
analysis = EmailAnalysis(
    action=EmailAction.ARCHIVE,
    category=EmailCategory.WORK,
    confidence=150,  # Would be clamped to 100
    reasoning="..."
)
# No error, confidence=100
```

**After** (Phase 0.5):
```python
# Raises ValueError with diagnostic message
analysis = EmailAnalysis(
    action=EmailAction.ARCHIVE,
    category=EmailCategory.WORK,
    confidence=150,  # ❌ ValueError!
    reasoning="..."
)
# ValueError: Confidence must be 0-100, got 150. This indicates a bug in confidence calculation.
```

**Why**: Silent failures hide bugs. Explicit errors catch confidence calculation bugs during development.

**Migration Guide**:
1. Fix confidence calculation logic to ensure 0-100 range
2. Add validation BEFORE creating EmailAnalysis:

```python
def calculate_confidence(factors: dict) -> int:
    raw_confidence = sum(factors.values())

    # Add validation
    if not (0 <= raw_confidence <= 100):
        logger.error(f"Invalid confidence calculation: {raw_confidence}, factors={factors}")
        raise ValueError(f"Confidence calculation produced invalid value: {raw_confidence}")

    return raw_confidence
```

**Impact**: Code with buggy confidence calculations will fail fast instead of silently producing wrong values.

**Files Affected**:
- `src/core/schemas.py:172-186` - Validation added

**Related Issues**: [#48](https://github.com/johanlb/pkm-system/issues/48) (Fixed)

---

### 🟡 MEDIUM: DecisionRecord Correction Consistency Validation

**Breaking Change**: `DecisionRecord` now validates consistency between `is_correction` and `correct_action`.

**Before**:
```python
# These inconsistent states were allowed
record = DecisionRecord(
    is_correction=True,
    correct_action=None,  # ❌ Inconsistent but allowed
    # ...
)

record2 = DecisionRecord(
    is_correction=False,
    correct_action=EmailAction.ARCHIVE,  # ❌ Inconsistent but allowed
    # ...
)
```

**After**:
```python
# Now raises ValueError on inconsistency
record = DecisionRecord(
    is_correction=True,
    correct_action=None,  # ❌ ValueError!
    # ...
)
# ValueError: correct_action is required when is_correction=True

record2 = DecisionRecord(
    is_correction=False,
    correct_action=EmailAction.ARCHIVE,  # ❌ ValueError!
    # ...
)
# ValueError: correct_action should be None when is_correction=False
```

**Why**: Prevents invalid states that lead to learning data corruption.

**Migration Guide**:

✅ **Correct Usage**:
```python
# User corrected AI decision
record = DecisionRecord(
    is_correction=True,
    correct_action=EmailAction.TASK,  # ✅ Required
    # ...
)

# AI was right, no correction
record = DecisionRecord(
    is_correction=False,
    correct_action=None,  # ✅ Must be None
    # ...
)
```

**Impact**: Code creating `DecisionRecord` with inconsistent correction states.

**Files Affected**:
- `src/core/schemas.py:242-259` - Validation added

**Related Issues**: [#49](https://github.com/johanlb/pkm-system/issues/49) (Fixed)

---

## Behavioral Changes (Non-Breaking)

These changes modify behavior but are backward compatible:

### Thread ID Extraction - Malformed Headers Handling

**Change**: Thread ID extraction now validates and falls back on malformed headers.

**Before**:
```python
# Always used references[0] even if malformed
thread_id = metadata.references[0]  # Could be wrong
```

**After**:
```python
# Validates consistency with in_reply_to
if metadata.in_reply_to and metadata.in_reply_to not in metadata.references:
    # Malformed headers detected, use in_reply_to instead
    return metadata.in_reply_to
return metadata.references[0]
```

**Why**: Fixes known bug ([BUG_CONVERSATION_DETECTION.md](/archive/phase_reports/BUG_CONVERSATION_DETECTION.md)) that caused thread fragmentation.

**Impact**: Better conversation threading, fewer false negatives in continuity detection.

**Files Affected**:
- `src/core/events/normalizers/email_normalizer.py:353-393`

**Related Issues**: [#21](https://github.com/johanlb/pkm-system/issues/21) (Fixed - Reintroduced Bug)

---

### Timezone Normalization in Continuity Detection

**Change**: Time proximity calculation now normalizes to UTC before comparison.

**Before**:
```python
# Compared datetimes with different timezones directly
time_gap = current.occurred_at - previous.occurred_at
```

**After**:
```python
# Normalize to UTC first
current_utc = current.occurred_at.astimezone(timezone.utc)
previous_utc = previous.occurred_at.astimezone(timezone.utc)
time_gap = current_utc - previous_utc
```

**Why**: Prevents incorrect continuity scores across timezone boundaries.

**Impact**: More accurate continuity detection for events in different timezones.

**Files Affected**:
- `src/core/memory/continuity_detector.py` (lines TBD)

**Related Issues**: [#35](https://github.com/johanlb/pkm-system/issues/35) (Fixed)

---

### Entity Confidence Calibration

**Change**: Entity confidence changed from `1.0` to `0.95`.

**Before**:
```python
Entity(type="person", value="john@example.com", confidence=1.0)
```

**After**:
```python
Entity(type="person", value="john@example.com", confidence=0.95)
```

**Why**: No extraction is perfect. Email spoofing, parsing edge cases, etc. make 100% confidence unrealistic.

**Impact**: Slightly lower confidence scores, but more realistic.

**Files Affected**:
- `src/core/events/normalizers/email_normalizer.py:213-229`

**Related Issues**: [#17](https://github.com/johanlb/pkm-system/issues/17) (Fixed)

---

### Future Timestamp Tolerance

**Change**: Events with `occurred_at` up to 1 second in the future are now allowed.

**Before**:
```python
# Strict check
if self.occurred_at > now_utc():
    raise ValueError("occurred_at cannot be in the future")
```

**After**:
```python
# 1-second tolerance for clock skew
tolerance = timedelta(seconds=1)
if self.occurred_at > now_utc() + tolerance:
    raise ValueError(
        f"occurred_at cannot be in the future: {self.occurred_at} "
        f"(current time: {now_utc()}, tolerance: 1s)"
    )
```

**Why**: Prevents spurious failures due to minor clock differences between systems.

**Impact**: Fewer false validation errors for events created "right now".

**Files Affected**:
- `src/core/events/universal_event.py:243-252`

**Related Issues**: [#4](https://github.com/johanlb/pkm-system/issues/4) (Fixed)

---

### Attachment Count Exact Matching

**Change**: `attachment_count` must exactly match `len(attachment_types)`.

**Before**:
```python
# Allowed mismatches
PerceivedEvent(
    has_attachments=True,
    attachment_count=3,
    attachment_types=["pdf", "jpg"],  # Only 2 types, but count=3
    # ... accepted
)
```

**After**:
```python
# Exact match required
PerceivedEvent(
    has_attachments=True,
    attachment_count=3,
    attachment_types=["pdf", "jpg"],  # ❌ ValueError!
    # ...
)
# ValueError: attachment_count (3) must exactly match attachment_types length (2)
```

**Why**: Prevents data inconsistencies where count doesn't reflect actual attachments.

**Migration**:
```python
# Always derive count from types
attachment_types = ["pdf", "jpg", "docx"]
PerceivedEvent(
    has_attachments=True,
    attachment_count=len(attachment_types),  # ✅ Always consistent
    attachment_types=attachment_types,
    # ...
)
```

**Files Affected**:
- `src/core/events/universal_event.py:264-269`

**Related Issues**: [#5](https://github.com/johanlb/pkm-system/issues/5) (Fixed)

---

## Testing Changes

### Test Modifications Required

If you have tests that:
1. **Modify PerceivedEvent after creation** → Use `dataclasses.replace()`
2. **Create EmailAnalysis with invalid confidence** → Fix confidence values
3. **Create DecisionRecord with inconsistent correction state** → Fix consistency
4. **Test threading with malformed headers** → Update expectations
5. **Compare datetimes across timezones** → Normalize to UTC first

**Example Test Fix**:

❌ **Before**:
```python
def test_working_memory_confidence():
    event = create_sample_event()
    event.perception_confidence = 0.85  # ❌ Mutation
    wm = WorkingMemory(event)
    assert wm.overall_confidence == 0.85
```

✅ **After**:
```python
def test_working_memory_confidence():
    from dataclasses import replace

    event = create_sample_event()
    modified_event = replace(event, perception_confidence=0.85)  # ✅ Immutable
    wm = WorkingMemory(modified_event)
    assert wm.overall_confidence == 0.85
```

---

## Migration Checklist

Use this checklist when upgrading to Phase 0.5 Week 1:

- [ ] **Search codebase for `PerceivedEvent` mutation**
  ```bash
  grep -r "event\." src/ tests/ | grep -E "=((?!PerceivedEvent).)*$"
  ```

- [ ] **Replace mutations with `dataclasses.replace()`**
  ```python
  from dataclasses import replace
  new_event = replace(old_event, field=new_value)
  ```

- [ ] **Validate confidence calculations**
  ```bash
  grep -r "EmailAnalysis" src/ | grep "confidence"
  ```

- [ ] **Check DecisionRecord creation**
  ```bash
  grep -r "DecisionRecord" src/ | grep "is_correction"
  ```

- [ ] **Run full test suite**
  ```bash
  pytest tests/unit/ -v
  pytest tests/integration/ -v
  ```

- [ ] **Check for deprecation warnings in logs**
  ```bash
  pytest tests/ 2>&1 | grep -i "deprecat"
  ```

---

## Deprecations

No deprecations in this release. All changes are immediate breaking changes.

---

## Rollback Guide

If you need to rollback to Phase 1 (pre-cognitive architecture):

```bash
# Checkout previous stable version
git checkout 46f55e9  # Last commit before cognitive architecture

# Reinstall dependencies (if changed)
pip install -r requirements.txt

# Run tests to verify
pytest tests/unit/ -v
```

**Note**: Phase 0.5 introduces architectural changes that are not backward compatible. Rollback is only recommended for emergency situations.

---

## Future Breaking Changes (Planned)

### Phase 0.5 Week 2-5 (Expected)

- **Working Memory API changes** - Reasoning passes structure
- **Action interface** - New action execution model
- **PKM integration** - Long-term memory interface

These will be documented in future updates to this file.

---

## Questions?

For questions about breaking changes:
1. Check related GitHub issues (linked above)
2. Review commit messages for detailed context
3. See `archive/phase_reports/` for architectural decisions
4. Open new issue if migration is unclear

---

**Version History**:
- `3.1.0` (2025-12-31): Phase 0.5 Week 1 - Cognitive architecture foundation
- `2.1.0` (2025-12-28): Phase 2 - Interactive menu system
- `2.0.0` (2025-12-15): Phase 1 - Email processing with AI
- `1.0.0` (2025-12-01): Phase 0 - Foundation
