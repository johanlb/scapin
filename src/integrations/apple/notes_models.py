"""
Apple Notes Data Models

Models for representing Apple Notes data in Scapin.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SyncDirection(str, Enum):
    """Direction of sync operation"""

    APPLE_TO_SCAPIN = "apple_to_scapin"
    SCAPIN_TO_APPLE = "scapin_to_apple"
    BIDIRECTIONAL = "bidirectional"


class SyncAction(str, Enum):
    """Type of sync action to perform"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SKIP = "skip"
    CONFLICT = "conflict"


class ConflictResolution(str, Enum):
    """How to resolve sync conflicts"""

    APPLE_WINS = "apple_wins"
    SCAPIN_WINS = "scapin_wins"
    NEWER_WINS = "newer_wins"
    MANUAL = "manual"


@dataclass
class AppleNote:
    """Represents a note from Apple Notes"""

    id: str  # x-coredata://... ID
    name: str
    body_html: str
    folder: str
    created_at: datetime
    modified_at: datetime
    # Computed fields
    body_text: str = ""
    body_markdown: str = ""

    def __post_init__(self) -> None:
        """Convert HTML to text and markdown after init"""
        if self.body_html and not self.body_text:
            self.body_text = self._html_to_text(self.body_html)
        if self.body_html and not self.body_markdown:
            self.body_markdown = self._html_to_markdown(self.body_html)

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert HTML to plain text"""
        import re

        # Remove HTML tags
        text = re.sub(r"<br\s*/?>", "\n", html)
        text = re.sub(r"</div>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        """Convert Apple Notes HTML to Markdown"""
        import re

        md = html

        # Headings
        md = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n", md, flags=re.DOTALL)
        md = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n", md, flags=re.DOTALL)
        md = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n", md, flags=re.DOTALL)

        # Bold and italic
        md = re.sub(r"<b>(.*?)</b>", r"**\1**", md, flags=re.DOTALL)
        md = re.sub(r"<strong>(.*?)</strong>", r"**\1**", md, flags=re.DOTALL)
        md = re.sub(r"<i>(.*?)</i>", r"*\1*", md, flags=re.DOTALL)
        md = re.sub(r"<em>(.*?)</em>", r"*\1*", md, flags=re.DOTALL)

        # Links
        md = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", md)

        # Lists
        md = re.sub(r"<li>(.*?)</li>", r"- \1\n", md, flags=re.DOTALL)
        md = re.sub(r"<[ou]l[^>]*>", "", md)
        md = re.sub(r"</[ou]l>", "", md)

        # Line breaks and divs
        md = re.sub(r"<br\s*/?>", "\n", md)
        md = re.sub(r"</div>", "\n", md)
        md = re.sub(r"<div[^>]*>", "", md)

        # Remove remaining tags
        md = re.sub(r"<[^>]+>", "", md)

        # Decode HTML entities
        md = md.replace("&nbsp;", " ")
        md = md.replace("&amp;", "&")
        md = md.replace("&lt;", "<")
        md = md.replace("&gt;", ">")
        md = md.replace("&quot;", '"')

        # Clean up whitespace
        md = re.sub(r"\n{3,}", "\n\n", md)
        md = re.sub(r"[ \t]+\n", "\n", md)

        return md.strip()


@dataclass
class AppleFolder:
    """Represents a folder from Apple Notes"""

    name: str
    note_count: int = 0


@dataclass
class SyncConflict:
    """Represents a sync conflict that needs resolution"""

    note_id: str
    apple_note: AppleNote | None
    scapin_note_path: str | None
    apple_modified: datetime | None
    scapin_modified: datetime | None
    reason: str
    suggested_resolution: ConflictResolution = ConflictResolution.NEWER_WINS


@dataclass
class SyncResult:
    """Result of a sync operation"""

    success: bool
    direction: SyncDirection
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    conflicts: list[SyncConflict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @property
    def total_synced(self) -> int:
        """Total number of notes synced"""
        return len(self.created) + len(self.updated)

    @property
    def duration_seconds(self) -> float | None:
        """Duration of sync in seconds"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class SyncMapping:
    """Mapping between Apple Notes ID and Scapin note path"""

    apple_id: str
    scapin_path: str
    apple_modified: datetime
    scapin_modified: datetime
    last_synced: datetime
