"""
Drafts API Models

Pydantic models for draft email reply API requests and responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DraftResponse(BaseModel):
    """Draft reply response"""

    draft_id: str = Field(..., description="Unique draft ID")
    email_id: int = Field(..., description="Original email ID")
    account_email: str = Field(..., description="Account email address")
    message_id: str | None = Field(None, description="Original message ID")
    subject: str = Field(..., description="Reply subject")
    to_addresses: list[str] = Field(default_factory=list, description="To recipients")
    cc_addresses: list[str] = Field(default_factory=list, description="CC recipients")
    bcc_addresses: list[str] = Field(default_factory=list, description="BCC recipients")
    body: str = Field(..., description="Draft body content")
    body_format: str = Field("plain_text", description="Body format (plain_text, html, markdown)")
    ai_generated: bool = Field(True, description="Whether AI-generated")
    ai_confidence: float = Field(0.0, description="AI confidence score 0-1")
    ai_reasoning: str | None = Field(None, description="AI reasoning for the draft")
    status: str = Field("draft", description="Status (draft, sent, discarded, failed)")
    original_subject: str | None = Field(None, description="Original email subject")
    original_from: str | None = Field(None, description="Original email sender")
    original_date: datetime | None = Field(None, description="Original email date")
    user_edited: bool = Field(False, description="Whether user has edited")
    edit_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Edit history"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    sent_at: datetime | None = Field(None, description="When sent (if sent)")
    discarded_at: datetime | None = Field(None, description="When discarded (if discarded)")


class DraftCreateRequest(BaseModel):
    """Request to create a draft manually"""

    email_id: int = Field(..., description="Original email ID")
    account_email: str = Field(..., description="Account email address")
    subject: str = Field(..., description="Reply subject")
    body: str = Field("", description="Draft body content")
    to_addresses: list[str] = Field(default_factory=list, description="To recipients")
    cc_addresses: list[str] = Field(default_factory=list, description="CC recipients")
    body_format: str = Field("plain_text", description="Body format")
    original_subject: str | None = Field(None, description="Original email subject")
    original_from: str | None = Field(None, description="Original email sender")


class DraftUpdateRequest(BaseModel):
    """Request to update a draft"""

    subject: str | None = Field(None, description="New subject")
    body: str | None = Field(None, description="New body content")
    to_addresses: list[str] | None = Field(None, description="New to recipients")
    cc_addresses: list[str] | None = Field(None, description="New CC recipients")
    bcc_addresses: list[str] | None = Field(None, description="New BCC recipients")


class DraftDiscardRequest(BaseModel):
    """Request to discard a draft"""

    reason: str | None = Field(None, description="Reason for discarding")


class DraftStatsResponse(BaseModel):
    """Draft statistics response"""

    total: int = Field(..., description="Total drafts")
    by_status: dict[str, int] = Field(
        default_factory=dict, description="Count by status"
    )
    by_account: dict[str, int] = Field(
        default_factory=dict, description="Count by account"
    )


class GenerateDraftRequest(BaseModel):
    """Request to generate a draft from an email"""

    email_id: int = Field(..., description="Original email ID")
    account_email: str = Field(..., description="Account email address")
    original_subject: str = Field(..., description="Original email subject")
    original_from: str = Field(..., description="Original email sender")
    original_content: str = Field(..., description="Original email content")
    reply_intent: str = Field("", description="Intended reply content")
    tone: str = Field("professional", description="Tone (professional, casual, formal, friendly)")
    language: str = Field("fr", description="Language (fr, en)")
    include_original: bool = Field(True, description="Include quoted original")
    original_date: datetime | None = Field(None, description="Original email date")
    original_message_id: str | None = Field(None, description="Original message ID")
