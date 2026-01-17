# Scapin - API Documentation

Complete API documentation for the Scapin system.

> ⚠️ **v3.1.0 Breaking Changes**: `PerceivedEvent` is now immutable. Use `dataclasses.replace()` for modifications. See [Migration Guide](#perceivedevent-immutability-v310).

## Table of Contents

1. [Core Systems](#core-systems)
   - [Configuration Manager](#configuration-manager)
   - [State Manager](#state-manager)
   - [Logger](#logger)
2. [Data Schemas](#data-schemas)
   - [PerceivedEvent Immutability (v3.1.0)](#perceivedevent-immutability-v310)
3. [Template System](#template-system)
4. [Utility Functions](#utility-functions)
5. [Health Monitoring](#health-monitoring)
6. [CLI Interface](#cli-interface)

---

## Core Systems

### Configuration Manager

Thread-safe configuration management using Pydantic Settings.

**Usage:**

```python
from src.core.config_manager import get_config

# Get configuration (singleton)
config = get_config()

# Access email settings
print(config.email.imap_host)
print(config.email.imap_port)

# Access AI settings
print(config.ai.confidence_threshold)
print(config.ai.rate_limit_per_minute)

# Access storage settings
print(config.storage.database_path)
print(config.storage.notes_path)
```

**Configuration File Example (`config/defaults.yaml`):**

```yaml
email:
  imap_host: imap.mail.me.com
  imap_port: 993
  imap_username: your@email.com
  imap_password: ${IMAP_PASSWORD}  # From environment
  inbox_folder: INBOX
  archive_folder: Archive
  max_workers: 10

ai:
  anthropic_api_key: ${ANTHROPIC_API_KEY}  # From environment
  confidence_threshold: 90
  rate_limit_per_minute: 40

storage:
  database_path: data/scapin.db
  notes_path: data/notes
  backup_enabled: true
```

---

### State Manager

Thread-safe in-memory state management for the current session.

**Usage:**

```python
from src.core.state_manager import get_state_manager

# Get state manager (singleton)
state = get_state_manager()

# Set values
state.set("current_email_id", 12345)
state.set("processing_mode", "auto")

# Get values
email_id = state.get("current_email_id")
mode = state.get("processing_mode", default="learning")

# Increment counters
state.increment("emails_processed")
state.increment("archived", amount=5)

# Track processed items
state.mark_processed("email", 12345)
if state.is_processed("email", 12345):
    print("Already processed")

# Cache entities
state.cache_entity("email", 12345, {"subject": "Test", "from": "sender@example.com"})
cached = state.get_cached_entity("email", 12345)

# Session management
state.reset_session()  # Start new session
state.end_session()    # End current session

# Get statistics
stats = state.to_dict()
print(f"Processed: {stats['stats']['emails_processed']}")
print(f"Duration: {stats['stats']['duration_minutes']} minutes")
```

---

### Logger

Structured logging system with JSON and text formats.

**Usage:**

```python
from src.monitoring.logger import ScapinLogger, LogLevel, LogFormat, get_logger

# Configure logging (do once at startup)
ScapinLogger.configure(level=LogLevel.INFO, format=LogFormat.JSON)

# Get logger for your module
logger = get_logger("my_module")

# Log messages
logger.info("Processing started")
logger.debug("Debug information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)

# Log with extra fields (JSON format)
logger.info(
    "Email processed",
    extra={
        "email_id": 12345,
        "action": "archive",
        "confidence": 95
    }
)

# Temporary log level
from src.monitoring.logger import temporary_log_level

with temporary_log_level(LogLevel.DEBUG):
    logger.debug("This will be logged even if global level is INFO")
```

---

## Data Schemas

All data models use Pydantic for validation and serialization.

### Email Metadata

```python
from src.core.schemas import EmailMetadata
from datetime import datetime, timezone

metadata = EmailMetadata(
    id=12345,
    folder="INBOX",
    message_id="<abc123@example.com>",
    from_address="sender@example.com",
    from_name="John Doe",
    to_addresses=["recipient@example.com"],
    subject="Meeting Tomorrow",
    date=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    has_attachments=False,
    size_bytes=1024,
    flags=["\\Seen"]
)

# Access fields
print(metadata.subject)
print(metadata.from_address)

# Serialize to dict
data = metadata.model_dump()

# Serialize to JSON
json_str = metadata.model_dump_json()
```

### Email Analysis

```python
from src.core.schemas import EmailAnalysis, EmailAction, EmailCategory

analysis = EmailAnalysis(
    action=EmailAction.ARCHIVE,
    category=EmailCategory.WORK,
    destination="Archive/2025/Work",
    confidence=95,
    reasoning="Work-related project update email, can be archived",
    tags=["work", "project", "update"],
    needs_full_content=False
)

# Access fields
print(analysis.action)  # EmailAction.ARCHIVE
print(analysis.confidence)  # 95

# Check if needs action
if analysis.action == EmailAction.TASK:
    print(f"Create task: {analysis.omnifocus_task}")
```

---

### PerceivedEvent Immutability (v3.1.0)

**Breaking Change**: As of v3.1.0, `PerceivedEvent` is immutable (`@dataclass(frozen=True)`).

**Why Immutable?**
- Prevents accidental modification during multi-pass reasoning
- Thread-safe by design
- Ensures data integrity across the processing pipeline
- Makes debugging easier (events can't change unexpectedly)

**Usage:**

```python
from src.core.events import PerceivedEvent, EventSource, EventType, UrgencyLevel
from dataclasses import replace
from datetime import datetime
from src.utils import now_utc

# Create event (normal)
event = PerceivedEvent(
    event_id="evt_12345",
    source=EventSource.EMAIL,
    source_id="12345",
    occurred_at=now_utc(),
    received_at=now_utc(),
    title="Meeting Tomorrow",
    content="Let's meet at 2pm",
    event_type=EventType.INVITATION,
    urgency=UrgencyLevel.MEDIUM,
    entities=[],
    topics=["meeting"],
    keywords=[],
    from_person="john@example.com",
    to_people=["me@example.com"],
    cc_people=[],
    thread_id=None,
    references=[],
    in_reply_to=None,
    has_attachments=False,
    attachment_count=0,
    attachment_types=[],
    urls=[],
    metadata={},
    perception_confidence=0.85,
    needs_clarification=False,
    clarification_questions=[]
)

# ❌ WRONG: Direct modification (raises FrozenInstanceError)
event.perception_confidence = 0.95  # ❌ Error!
event.entities.append(new_entity)    # ❌ Error!

# ✅ CORRECT: Use dataclasses.replace() to create modified copy
updated_event = replace(event, perception_confidence=0.95)

# ✅ CORRECT: Modify complex fields (lists, dicts)
from src.core.events import Entity

new_entity = Entity(type="person", value="jane@example.com", confidence=0.90)

updated_event = replace(
    event,
    entities=event.entities + [new_entity],  # Create new list
    topics=event.topics + ["collaboration"],
    metadata={**event.metadata, "processed": True}  # Create new dict
)

# ✅ CORRECT: Chain multiple modifications
final_event = replace(
    replace(event, perception_confidence=0.95),
    urgency=UrgencyLevel.HIGH
)

# ✅ CORRECT: Conditional modification
if event.perception_confidence < 0.90:
    event = replace(event, needs_clarification=True)
```

**Common Patterns:**

```python
# Pattern 1: Add to list
event = replace(event, topics=event.topics + ["new_topic"])

# Pattern 2: Update dict
event = replace(event, metadata={**event.metadata, "key": "value"})

# Pattern 3: Multiple field updates
event = replace(
    event,
    perception_confidence=0.95,
    needs_clarification=False,
    clarification_questions=[]
)

# Pattern 4: Conditional update
def increase_confidence(event: PerceivedEvent, amount: float) -> PerceivedEvent:
    """Returns new event with increased confidence"""
    new_confidence = min(event.perception_confidence + amount, 1.0)
    return replace(event, perception_confidence=new_confidence)

# Pattern 5: Builder pattern for complex updates
class EventBuilder:
    """Helper for building modified events"""

    def __init__(self, event: PerceivedEvent):
        self._event = event

    def with_confidence(self, confidence: float) -> 'EventBuilder':
        self._event = replace(self._event, perception_confidence=confidence)
        return self

    def add_entity(self, entity: Entity) -> 'EventBuilder':
        self._event = replace(
            self._event,
            entities=self._event.entities + [entity]
        )
        return self

    def build(self) -> PerceivedEvent:
        return self._event

# Usage
updated = (EventBuilder(event)
    .with_confidence(0.95)
    .add_entity(new_entity)
    .build())
```

**Testing with Immutable Events:**

```python
import pytest
from dataclasses import replace

def test_event_modification():
    """Test modifying immutable event"""
    event = create_sample_event()

    # Modify event
    modified = replace(event, perception_confidence=0.95)

    # Original unchanged
    assert event.perception_confidence == 0.70
    assert modified.perception_confidence == 0.95

    # All other fields copied
    assert modified.event_id == event.event_id
    assert modified.title == event.title

def test_frozen_enforcement():
    """Test that direct modification raises error"""
    event = create_sample_event()

    with pytest.raises(FrozenInstanceError):
        event.perception_confidence = 0.95
```

**Migration from v2.x to v3.1.0:**

See [BREAKING_CHANGES.md](../../archive/historical/BREAKING_CHANGES.md#-critical-perceivedevent-is-now-immutable) for complete migration guide.

---

## Template System

Jinja2-based template system for AI prompts and emails.

**Usage:**

```python
from src.ai.templates import TemplateManager

# Create template manager
tm = TemplateManager()

# Render template
prompt = tm.render(
    "email_analysis.j2",
    subject="Meeting Tomorrow",
    from_address="boss@company.com",
    body="Let's meet tomorrow at 2pm",
    has_attachments=False
)

# Custom template from string
custom_template = "Hello {{ name }}, your score is {{ score }}"
result = tm.render_string(
    custom_template,
    {"name": "John", "score": 95}
)

# List available templates
templates = tm.list_templates()

# Clear cache
tm.clear_cache()
```

**Template Example (`templates/ai/email_analysis.j2`):**

```jinja2
Analyze this email and determine the appropriate action.

Subject: {{ subject }}
From: {{ from_address }}
{% if has_attachments %}
Has Attachments: Yes
{% endif %}

Content:
{{ body | truncate_smart(500) }}

Provide analysis as JSON with action, category, destination, and confidence.
```

---

## Utility Functions

### File Utilities

```python
from src.utils import (
    ensure_dir,
    safe_read_file,
    safe_write_file,
    atomic_write,
    list_files,
    get_file_hash
)
from pathlib import Path

# Ensure directory exists
data_dir = ensure_dir(Path("data/notes"))

# Safe file operations
content = safe_read_file(Path("data/notes/example.md"))
safe_write_file(Path("data/notes/new.md"), "# New Note\n\nContent here")

# Atomic write (safe for concurrent access)
atomic_write(Path("data/state.json"), '{"key": "value"}')

# List files
txt_files = list_files(Path("data"), "*.txt", recursive=True)

# Get file hash
hash_value = get_file_hash(Path("data/file.txt"), algorithm="sha256")
```

### String Utilities

```python
from src.utils import (
    truncate,
    sanitize_filename,
    extract_email,
    extract_urls,
    slugify,
    normalize_whitespace
)

# Truncate text
short = truncate("Long text here...", length=20)

# Sanitize filename
safe_name = sanitize_filename("My<File>Name?.txt")  # "My_File_Name_.txt"

# Extract email
email = extract_email("Contact me at john@example.com")  # "john@example.com"

# Extract URLs
urls = extract_urls("Visit https://example.com and http://test.org")

# Create URL slug
slug = slugify("Hello World 2025!")  # "hello-world-2025"

# Normalize whitespace
clean = normalize_whitespace("Hello    World  \n\t  Test")  # "Hello World Test"
```

### Date Utilities

```python
from src.utils import (
    now_utc,
    parse_date,
    format_datetime,
    time_ago,
    is_business_hours,
    next_business_day
)

# Get current UTC time
now = now_utc()

# Parse date string
dt = parse_date("2025-01-15T10:30:00Z")
dt = parse_date("2025-01-15")
dt = parse_date("15 Jan 2025")

# Format datetime
iso_string = format_datetime(dt, "iso")
friendly = format_datetime(dt, "friendly")  # "January 15, 2025 at 10:30 AM"

# Time ago
ago = time_ago(dt)  # "5 minutes ago", "2 hours ago", etc.

# Business hours check
if is_business_hours():
    print("It's business hours!")

# Next business day
next_day = next_business_day()  # Skips weekends
```

---

## Health Monitoring

System health checks for all components.

**Usage:**

```python
from src.monitoring.health import get_health_service, quick_health_check

# Get health service
health = get_health_service()

# Check individual service
config_health = health.check("config")
print(f"Config: {config_health.status}")

# Check all services
all_health = health.check_all()
for check in all_health.checks:
    print(f"{check.service}: {check.status} - {check.message}")

# Quick health check (convenience function)
system_health = quick_health_check()
if system_health.is_healthy:
    print("All systems healthy")
else:
    print(f"Unhealthy services: {system_health.unhealthy_services}")

# Register custom health checker
def check_custom_service() -> bool:
    # Your check logic here
    return True

health.register("my_service", check_custom_service)

# Clear cache (force recheck)
health.clear_cache()
```

---

## CLI Interface

Command-line interface using Typer and Rich.

**Usage:**

```bash
# Check system health
python3 scapin.py health

# View configuration
python3 scapin.py config
python3 scapin.py config --validate

# Show session statistics
python3 scapin.py stats

# Process emails (coming in Phase 1)
python3 scapin.py process --limit 50 --auto --confidence 90

# Review decisions (coming in Phase 2.5)
python3 scapin.py review --limit 20

# Manage queue (coming in Phase 1)
python3 scapin.py queue --process

# Verbose logging
python3 scapin.py --verbose --log-format json stats

# Show version
python3 scapin.py --version
```

**Programmatic Usage:**

```python
from src.cli.app import app
from typer.testing import CliRunner

runner = CliRunner()

# Run health check
result = runner.invoke(app, ["health"])
print(result.stdout)

# Run with options
result = runner.invoke(app, ["--verbose", "stats"])
```

---

## Error Handling

All functions use consistent error handling patterns:

```python
# Functions return None or False on error
content = safe_read_file(Path("nonexistent.txt"))
if content is None:
    print("File not found or unreadable")

# Functions log errors using the logger
from src.monitoring.logger import get_logger
logger = get_logger("my_module")

try:
    # Your code here
    pass
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```

---

## Type Hints

All functions include comprehensive type hints:

```python
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

def process_email(
    email_id: int,
    metadata: EmailMetadata,
    config: Optional[ScapinConfig] = None
) -> Optional[EmailAnalysis]:
    """
    Process email and return analysis

    Args:
        email_id: Email ID
        metadata: Email metadata
        config: Optional configuration

    Returns:
        Email analysis or None if processing fails
    """
    pass
```

---

## Testing

All components have comprehensive test coverage:

```bash
# Run all tests
pytest tests/unit/ -v

# Run specific module tests
pytest tests/unit/test_utils.py -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

For more examples, see the `tests/unit/` directory which contains extensive usage examples for all components.
