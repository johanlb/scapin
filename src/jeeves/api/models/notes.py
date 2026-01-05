"""
Notes API Models

Pydantic models for notes/carnets API.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EntityResponse(BaseModel):
    """Entity mentioned in a note"""

    type: str = Field(..., description="Entity type (person, project, date, etc.)")
    value: str = Field(..., description="Entity value")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Detection confidence")


class NoteResponse(BaseModel):
    """Note in API response"""

    id: str = Field(..., alias="note_id", description="Note identifier")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note content (Markdown)")
    excerpt: str = Field(..., description="Short excerpt for preview")
    path: str = Field(..., description="Folder path (e.g., 'Clients/ABC')")
    tags: list[str] = Field(default_factory=list, description="Tags")
    entities: list[EntityResponse] = Field(
        default_factory=list, description="Extracted entities"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    pinned: bool = Field(False, description="Whether note is pinned")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    class Config:
        populate_by_name = True


class NoteCreateRequest(BaseModel):
    """Request to create a new note"""

    title: str = Field(..., min_length=1, max_length=500, description="Note title")
    content: str = Field(..., min_length=1, description="Note content (Markdown)")
    path: str = Field("", description="Folder path (e.g., 'Clients/ABC')")
    tags: list[str] = Field(default_factory=list, description="Tags")
    pinned: bool = Field(False, description="Whether to pin the note")


class NoteUpdateRequest(BaseModel):
    """Request to update an existing note"""

    title: str | None = Field(None, min_length=1, max_length=500, description="New title")
    content: str | None = Field(None, min_length=1, description="New content")
    path: str | None = Field(None, description="New folder path")
    tags: list[str] | None = Field(None, description="New tags")
    pinned: bool | None = Field(None, description="Pin/unpin note")


class FolderNode(BaseModel):
    """Folder in the notes tree"""

    name: str = Field(..., description="Folder name")
    path: str = Field(..., description="Full path")
    note_count: int = Field(0, description="Number of notes in this folder")
    children: list["FolderNode"] = Field(
        default_factory=list, description="Child folders"
    )


class NotesTreeResponse(BaseModel):
    """Notes organized in folder tree"""

    folders: list[FolderNode] = Field(default_factory=list, description="Root folders")
    pinned: list[NoteResponse] = Field(
        default_factory=list, description="Pinned notes"
    )
    recent: list[NoteResponse] = Field(
        default_factory=list, description="Recently modified notes"
    )
    total_notes: int = Field(0, description="Total number of notes")


class NoteSearchResult(BaseModel):
    """Search result with relevance score"""

    note: NoteResponse = Field(..., description="Matching note")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    highlights: list[str] = Field(
        default_factory=list, description="Highlighted matching excerpts"
    )


class NoteSearchResponse(BaseModel):
    """Search results"""

    query: str = Field(..., description="Search query")
    results: list[NoteSearchResult] = Field(
        default_factory=list, description="Matching notes"
    )
    total: int = Field(0, description="Total matching notes")


class WikilinkResponse(BaseModel):
    """Wikilink information"""

    text: str = Field(..., description="Link text [[text]]")
    target_id: str | None = Field(None, description="Target note ID if exists")
    target_title: str | None = Field(None, description="Target note title if exists")
    exists: bool = Field(False, description="Whether target note exists")


class NoteLinksResponse(BaseModel):
    """Note's bidirectional links"""

    note_id: str = Field(..., description="Note ID")
    outgoing: list[WikilinkResponse] = Field(
        default_factory=list, description="Links from this note"
    )
    incoming: list[WikilinkResponse] = Field(
        default_factory=list, description="Links to this note"
    )


class NoteSyncStatus(BaseModel):
    """Apple Notes sync status"""

    last_sync: datetime | None = Field(None, description="Last sync timestamp")
    syncing: bool = Field(False, description="Currently syncing")
    notes_synced: int = Field(0, description="Number of notes synced")
    errors: list[str] = Field(default_factory=list, description="Sync errors")
