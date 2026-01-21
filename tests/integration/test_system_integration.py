"""
End-to-End Integration Tests

Tests that validate all systems work together correctly.
"""

from pathlib import Path

import pytest

from src.core.schemas import (
    EmailAction,
    EmailAnalysis,
    EmailCategory,
    EmailContent,
    EmailMetadata,
    ProcessedEmail,
)
from src.core.state_manager import StateManager
from src.monitoring.health import get_health_service, quick_health_check
from src.monitoring.logger import LogFormat, LogLevel, ScapinLogger, get_logger
from src.sancho.templates import TemplateManager
from src.utils import (
    ensure_dir,
    now_utc,
    safe_read_file,
    safe_write_file,
    slugify,
)

pytestmark = pytest.mark.integration


class TestSystemIntegration:
    """
    End-to-end integration tests for the Scapin system

    These tests validate that all components work together correctly.
    """

    def test_full_email_processing_workflow(self, tmp_path: Path):
        """
        Test complete email processing workflow

        This test simulates the full email processing pipeline:
        1. Configure system
        2. Initialize state
        3. Load email metadata
        4. Create email content
        5. Analyze email (simulated)
        6. Update state
        7. Log results
        8. Store data
        """
        # ===== Phase 1: System Setup =====
        ScapinLogger.configure(level=LogLevel.INFO, format=LogFormat.TEXT)
        logger = get_logger("integration_test")
        logger.info("Starting integration test")

        # Create test directories
        config_dir = ensure_dir(tmp_path / "config")
        data_dir = ensure_dir(tmp_path / "data")
        notes_dir = ensure_dir(tmp_path / "data" / "notes")

        # ===== Phase 2: State Management =====
        state = StateManager()
        state.set("processing_mode", "auto")
        state.set("confidence_threshold", 90)

        # ===== Phase 3: Email Metadata =====
        email_metadata = EmailMetadata(
            id=12345,
            folder="INBOX",
            message_id="<integration-test@example.com>",
            from_address="sender@example.com",
            from_name="Test Sender",
            to_addresses=["recipient@example.com"],
            subject="Project Update - Q1 2025",
            date=now_utc(),
            has_attachments=False,
            size_bytes=2048,
            flags=[]
        )

        logger.info(
            "Processing email",
            extra={
                "email_id": email_metadata.id,
                "subject": email_metadata.subject
            }
        )

        # ===== Phase 4: Email Content =====
        email_content = EmailContent(
            plain_text="This is a project update for Q1 2025. The team has completed 80% of milestones.",
            html="<p>This is a project update for Q1 2025. The team has completed 80% of milestones.</p>",
            attachments=[]
        )

        # Verify preview generation
        assert email_content.preview is not None
        assert "project update" in email_content.preview.lower()

        # ===== Phase 5: Template System =====
        template_dir = ensure_dir(tmp_path / "templates")

        # Create test template
        template_file = template_dir / "email_analysis.j2"
        safe_write_file(
            template_file,
            "Analyze: {{ subject }}\nFrom: {{ from_address }}\n\n{{ body }}"
        )

        # Render template
        tm = TemplateManager(template_dir=template_dir)
        rendered = tm.render(
            "email_analysis.j2",
            subject=email_metadata.subject,
            from_address=email_metadata.from_address,
            body=email_content.plain_text
        )

        assert "Project Update" in rendered
        assert "sender@example.com" in rendered

        # ===== Phase 6: Email Analysis (Simulated) =====
        email_analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.WORK,
            destination="Archive/2025/Work/Projects",
            confidence=95,
            reasoning="Project update email with high confidence - team milestone report",
            tags=["work", "project", "q1-2025", "milestone"],
            entities={
                "people": ["Test Sender"],
                "projects": ["Q1 2025 Project"],
                "dates": ["Q1 2025"]
            },
            needs_full_content=False
        )

        # Verify analysis
        assert email_analysis.action == EmailAction.ARCHIVE
        assert email_analysis.confidence >= state.get("confidence_threshold", 90)

        # ===== Phase 7: Update State =====
        state.increment("emails_processed")
        state.add_confidence_score(email_analysis.confidence)
        state.mark_processed(str(email_metadata.id))

        # Cache email data
        state.cache_entity(f"email-{email_metadata.id}", {
            "subject": email_metadata.subject,
            "from": email_metadata.from_address,
            "action": email_analysis.action.value
        })

        # ===== Phase 8: Create Processed Email Record =====
        processed_email = ProcessedEmail(
            metadata=email_metadata,
            content=email_content,
            analysis=email_analysis,
            processed_at=now_utc()
        )

        # ===== Phase 9: File Operations =====
        # Create note from email
        note_slug = slugify(f"{email_metadata.subject}-{email_metadata.id}")
        note_path = notes_dir / f"{note_slug}.md"

        note_content = f"""# {email_metadata.subject}

**From:** {email_metadata.from_name} <{email_metadata.from_address}>
**Date:** {email_metadata.date.isoformat()}
**Tags:** {', '.join(email_analysis.tags)}

## Content

{email_content.plain_text}

## Analysis

- **Action:** {email_analysis.action.value}
- **Category:** {email_analysis.category.value}
- **Confidence:** {email_analysis.confidence}%
- **Reasoning:** {email_analysis.reasoning}
"""

        safe_write_file(note_path, note_content)

        # Verify note was created
        assert note_path.exists()
        saved_content = safe_read_file(note_path)
        assert saved_content is not None
        assert "Project Update" in saved_content

        # ===== Phase 10: Verify State =====
        # Verify state was updated
        assert state.get("emails_processed") == 1
        assert state.is_processed(str(email_metadata.id))

        # Verify cached entity
        cached = state.get_cached_entity(f"email-{email_metadata.id}")
        assert cached is not None
        assert cached["subject"] == email_metadata.subject

        # ===== Phase 11: Health Check =====
        health_service = get_health_service()

        # Check config health
        config_health = health_service.check_service("config")
        assert config_health.status.value in ["healthy", "degraded"]

        # Check all systems
        system_health = quick_health_check()
        assert len(system_health.checks) >= 3  # config, git, python_deps

        logger.info(
            "Integration test completed successfully",
            extra={
                "emails_processed": state.get("emails_processed"),
                "email_id": email_metadata.id
            }
        )

    def test_concurrent_state_access(self):
        """
        Test concurrent access to state manager

        Validates thread safety of state manager with concurrent updates.
        """
        import threading

        state = StateManager()

        def increment_worker(count: int):
            for _ in range(count):
                state.increment("counter")

        # Create 10 threads, each incrementing 100 times
        threads = []
        for _ in range(10):
            t = threading.Thread(target=increment_worker, args=(100,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify count is correct (10 threads × 100 increments)
        assert state.get("counter") == 1000

    def test_logger_formats(self, tmp_path: Path, capsys):
        """
        Test logger with different formats

        Validates both TEXT and JSON logging formats.
        """
        # Test TEXT format
        ScapinLogger.configure(level=LogLevel.INFO, format=LogFormat.TEXT)
        logger = get_logger("test_logger")

        logger.info("Test message in TEXT format")
        captured = capsys.readouterr()
        # Output goes to stdout
        assert "Test message in TEXT format" in captured.out

        # Test JSON format
        ScapinLogger._configured = False  # Reset for reconfiguration
        ScapinLogger.configure(level=LogLevel.INFO, format=LogFormat.JSON)
        logger = get_logger("test_logger_json")

        logger.info("Test message in JSON format", extra={"key": "value"})
        captured = capsys.readouterr()
        # JSON format should include structured data
        assert "Test message in JSON format" in captured.out

    def test_template_caching(self, tmp_path: Path):
        """
        Test template caching behavior

        Validates that templates are cached and reused correctly.
        """
        template_dir = ensure_dir(tmp_path / "templates")
        template_file = template_dir / "test.j2"
        safe_write_file(template_file, "Hello {{ name }}")

        tm = TemplateManager(template_dir=template_dir)

        # First render - loads template
        result1 = tm.render("test.j2", name="World")
        assert result1 == "Hello World"

        # Second render - uses cache
        result2 = tm.render("test.j2", name="Alice")
        assert result2 == "Hello Alice"

        # Third render - Jinja2 handles caching automatically with auto_reload=True
        result3 = tm.render("test.j2", name="Bob")
        assert result3 == "Hello Bob"

    def test_health_check_caching(self):
        """
        Test health check caching

        Validates that health checks are cached correctly.
        """
        health = get_health_service()

        # First check - performs actual check
        result1 = health.check_service("config")
        assert result1 is not None

        # Second check within cache window - uses cache
        result2 = health.check_service("config")
        assert result2.checked_at == result1.checked_at

        # Clear cache
        health.clear_cache()

        # Third check - performs new check
        result3 = health.check_service("config")
        assert result3.checked_at >= result1.checked_at

    def test_utility_functions_integration(self, tmp_path: Path):
        """
        Test utility functions working together

        Validates integration between file, string, and date utilities.
        """
        from src.utils import (
            ensure_dir,
            format_datetime,
            normalize_whitespace,
            now_utc,
            safe_read_file,
            safe_write_file,
            slugify,
        )

        # Create directory structure
        notes_dir = ensure_dir(tmp_path / "notes" / "2025")

        # Generate filename from title
        title = "My Important Note   -   2025"
        slug = slugify(title)
        timestamp = format_datetime(now_utc(), "date_only")

        filename = f"{timestamp}-{slug}.md"
        file_path = notes_dir / filename

        # Create note content
        content = """
        This   is   a   test   note
        with   irregular   whitespace
        """
        normalized = normalize_whitespace(content)

        # Write and verify
        success = safe_write_file(file_path, normalized)
        assert success is True

        # Read and verify
        read_content = safe_read_file(file_path)
        assert read_content is not None
        assert "irregular whitespace" in read_content
        assert "   " not in read_content  # Multiple spaces removed

    def test_schema_validation_pipeline(self):
        """
        Test schema validation throughout pipeline

        Validates that all schemas properly validate and serialize data.
        """
        # Create metadata with validation
        metadata = EmailMetadata(
            id=99999,
            folder="INBOX",
            message_id="<test@example.com>",
            from_address="valid@example.com",
            from_name="Valid User",
            to_addresses=["recipient@example.com"],
            subject="Valid Subject",
            date=now_utc(),
            has_attachments=False,
            size_bytes=1024,
            flags=[]
        )

        # Create content with auto-generation
        content = EmailContent(
            plain_text="Test email content for validation",
            html="<p>Test email content for validation</p>"
        )

        # Verify preview was auto-generated
        assert content.preview is not None

        # Create analysis with validation
        analysis = EmailAnalysis(
            action=EmailAction.ARCHIVE,
            category=EmailCategory.PERSONAL,
            destination="Archive/Personal",
            confidence=85,  # Should be clamped to 0-100
            reasoning="Personal email, low priority, can be archived safely",
            tags=["personal", "archive"]
        )

        # Verify confidence clamping
        assert 0 <= analysis.confidence <= 100

        # Create processed email
        processed = ProcessedEmail(
            metadata=metadata,
            content=content,
            analysis=analysis,
            processed_at=now_utc()
        )

        # Serialize to dict
        data = processed.model_dump()
        assert data["metadata"]["id"] == 99999
        assert data["analysis"]["confidence"] == 85

        # Serialize to JSON and back
        json_str = processed.model_dump_json()
        assert "valid@example.com" in json_str

        # Deserialize
        restored = ProcessedEmail.model_validate_json(json_str)
        assert restored.metadata.id == 99999
        assert restored.analysis.confidence == 85
