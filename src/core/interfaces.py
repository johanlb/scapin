"""
PKM Abstract Base Classes (Interfaces)

Defines contracts for all major system components:
- Email processing
- AI routing
- Storage
- Knowledge management
- Review/FSRS
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from src.core.schemas import (
    EmailMetadata,
    EmailContent,
    EmailAnalysis,
    ProcessedEmail,
    EmailAction,
    DecisionRecord,
    KnowledgeEntry,
    KnowledgeQuery,
    FSRSCard,
    FSRSReview,
    ReviewGrade,
    ConversationContext,
    HealthCheck,
)


# ============================================================================
# EMAIL CLIENT INTERFACE
# ============================================================================


class IEmailClient(ABC):
    """
    Interface for email client operations (IMAP)

    Implementations: IMAPClient (using imapclient library)
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Connect to email server

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from email server"""
        pass

    @abstractmethod
    def select_folder(self, folder: str) -> None:
        """
        Select IMAP folder

        Args:
            folder: Folder path (e.g., "INBOX", "Archive/2024")

        Raises:
            ValueError: If folder doesn't exist
        """
        pass

    @abstractmethod
    def list_folders(self) -> List[str]:
        """
        List all available folders

        Returns:
            List of folder paths
        """
        pass

    @abstractmethod
    def search(
        self, criteria: List[str], folder: Optional[str] = None
    ) -> List[int]:
        """
        Search for emails matching criteria

        Args:
            criteria: IMAP search criteria (e.g., ["UNFLAGGED", "SINCE", "01-Jan-2024"])
            folder: Optional folder to search in (defaults to current)

        Returns:
            List of message UIDs
        """
        pass

    @abstractmethod
    def fetch_metadata(
        self, message_ids: List[int], folder: Optional[str] = None
    ) -> List[EmailMetadata]:
        """
        Fetch email metadata (headers only)

        Args:
            message_ids: List of IMAP UIDs
            folder: Optional folder (defaults to current)

        Returns:
            List of EmailMetadata objects
        """
        pass

    @abstractmethod
    def fetch_content(
        self, message_id: int, folder: Optional[str] = None
    ) -> EmailContent:
        """
        Fetch email content (body + attachments)

        Args:
            message_id: IMAP UID
            folder: Optional folder (defaults to current)

        Returns:
            EmailContent object

        Raises:
            ValueError: If email not found
        """
        pass

    @abstractmethod
    def move_email(
        self, message_id: int, destination: str, source: Optional[str] = None
    ) -> int:
        """
        Move email to another folder

        Args:
            message_id: IMAP UID in source folder
            destination: Destination folder path
            source: Optional source folder (defaults to current)

        Returns:
            New message UID in destination folder

        Raises:
            ValueError: If email not found or destination invalid
        """
        pass

    @abstractmethod
    def delete_email(
        self, message_id: int, folder: Optional[str] = None
    ) -> None:
        """
        Delete email (mark as deleted + expunge)

        Args:
            message_id: IMAP UID
            folder: Optional folder (defaults to current)
        """
        pass

    @abstractmethod
    def add_flags(
        self, message_ids: List[int], flags: List[str], folder: Optional[str] = None
    ) -> None:
        """
        Add flags to emails

        Args:
            message_ids: List of IMAP UIDs
            flags: List of IMAP flags (e.g., ["\\Flagged", "$MailFlagBit2"])
            folder: Optional folder (defaults to current)
        """
        pass

    @abstractmethod
    def health_check(self) -> HealthCheck:
        """
        Check email server connection health

        Returns:
            HealthCheck result
        """
        pass


# ============================================================================
# AI ROUTER INTERFACE
# ============================================================================


class IAIRouter(ABC):
    """
    Interface for AI routing and email analysis

    Implementations: AnthropicRouter (using Claude via Anthropic API)
    """

    @abstractmethod
    def analyze_email(
        self,
        metadata: EmailMetadata,
        content: EmailContent,
        context: Optional[ConversationContext] = None,
        preview_mode: bool = False,
    ) -> EmailAnalysis:
        """
        Analyze email and recommend action

        Args:
            metadata: Email metadata
            content: Email content
            context: Optional conversation context for thread analysis
            preview_mode: Use preview (first 500 chars) to save tokens

        Returns:
            EmailAnalysis with recommended action

        Raises:
            APIError: If AI service fails
        """
        pass

    @abstractmethod
    def analyze_conversation(
        self, emails: List[ProcessedEmail]
    ) -> EmailAnalysis:
        """
        Analyze email thread/conversation

        Args:
            emails: List of emails in thread (chronological order)

        Returns:
            EmailAnalysis for entire conversation
        """
        pass

    @abstractmethod
    def extract_knowledge(
        self, email: ProcessedEmail
    ) -> Optional[KnowledgeEntry]:
        """
        Extract knowledge from reference email

        Args:
            email: Processed email

        Returns:
            KnowledgeEntry if knowledge found, None otherwise
        """
        pass

    @abstractmethod
    def generate_task_description(
        self, email: ProcessedEmail
    ) -> str:
        """
        Generate OmniFocus task description from email

        Args:
            email: Processed email

        Returns:
            Task description string
        """
        pass

    @abstractmethod
    def health_check(self) -> HealthCheck:
        """
        Check AI service connection health

        Returns:
            HealthCheck result
        """
        pass


# ============================================================================
# STORAGE INTERFACE
# ============================================================================


class IStorage(ABC):
    """
    Interface for persistent storage

    Implementations:
    - JSONStorage: JSON files in /tmp or config directory
    - GitStorage: Git-tracked files
    """

    @abstractmethod
    def save_decision(self, decision: DecisionRecord) -> None:
        """
        Save processing decision to history

        Args:
            decision: Decision record to save
        """
        pass

    @abstractmethod
    def load_decisions(
        self,
        limit: Optional[int] = None,
        reviewed_only: bool = False,
        unreviewed_only: bool = False,
    ) -> List[DecisionRecord]:
        """
        Load decision history

        Args:
            limit: Maximum number of decisions to load (most recent first)
            reviewed_only: Only load reviewed decisions
            unreviewed_only: Only load unreviewed decisions

        Returns:
            List of DecisionRecord objects
        """
        pass

    @abstractmethod
    def save_queue_item(
        self, email_metadata: EmailMetadata, analysis: EmailAnalysis
    ) -> None:
        """
        Save email to processing queue (low confidence items)

        Args:
            email_metadata: Email metadata
            analysis: AI analysis with confidence score
        """
        pass

    @abstractmethod
    def load_queue(self) -> List[Dict[str, Any]]:
        """
        Load processing queue

        Returns:
            List of queued items with metadata and analysis
        """
        pass

    @abstractmethod
    def clear_queue(self) -> None:
        """Clear processing queue"""
        pass

    @abstractmethod
    def save_session_stats(self, stats: Dict[str, Any]) -> None:
        """
        Save session statistics

        Args:
            stats: Session statistics dictionary
        """
        pass

    @abstractmethod
    def load_session_stats(self) -> Optional[Dict[str, Any]]:
        """
        Load last session statistics

        Returns:
            Session stats dict or None if not found
        """
        pass


# ============================================================================
# KNOWLEDGE INTERFACE
# ============================================================================


class IKnowledgeBase(ABC):
    """
    Interface for knowledge base management

    Implementations: GitKnowledgeBase (markdown files in Git)
    """

    @abstractmethod
    def save_entry(self, entry: KnowledgeEntry) -> Path:
        """
        Save knowledge entry

        Args:
            entry: Knowledge entry to save

        Returns:
            Path to saved file

        Raises:
            IOError: If save fails
        """
        pass

    @abstractmethod
    def load_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """
        Load knowledge entry by ID

        Args:
            entry_id: Entry identifier

        Returns:
            KnowledgeEntry or None if not found
        """
        pass

    @abstractmethod
    def search(self, query: KnowledgeQuery) -> List[KnowledgeEntry]:
        """
        Search knowledge base

        Args:
            query: Search query parameters

        Returns:
            List of matching KnowledgeEntry objects
        """
        pass

    @abstractmethod
    def delete_entry(self, entry_id: str) -> bool:
        """
        Delete knowledge entry

        Args:
            entry_id: Entry identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def commit_changes(self, message: str) -> None:
        """
        Commit knowledge base changes to Git

        Args:
            message: Commit message
        """
        pass

    @abstractmethod
    def sync_with_notes(self) -> Dict[str, Any]:
        """
        Sync knowledge base with Apple Notes

        Returns:
            Sync statistics (added, updated, deleted)
        """
        pass


# ============================================================================
# REVIEW INTERFACE
# ============================================================================


class IReviewSystem(ABC):
    """
    Interface for spaced repetition review system (FSRS)

    Implementations: FSRSReviewSystem
    """

    @abstractmethod
    def create_card(
        self, knowledge_entry: KnowledgeEntry, question: str, answer: str
    ) -> FSRSCard:
        """
        Create flashcard from knowledge entry

        Args:
            knowledge_entry: Source knowledge entry
            question: Review question
            answer: Expected answer

        Returns:
            Created FSRSCard
        """
        pass

    @abstractmethod
    def get_due_cards(self, limit: int = 20) -> List[FSRSCard]:
        """
        Get cards due for review

        Args:
            limit: Maximum number of cards to return

        Returns:
            List of due FSRSCard objects
        """
        pass

    @abstractmethod
    def review_card(self, card_id: str, grade: ReviewGrade) -> FSRSCard:
        """
        Review card and update scheduling

        Args:
            card_id: Card identifier
            grade: Review grade (again, hard, good, easy)

        Returns:
            Updated FSRSCard with new scheduling

        Raises:
            ValueError: If card not found
        """
        pass

    @abstractmethod
    def get_card_stats(self, card_id: str) -> Dict[str, Any]:
        """
        Get card statistics

        Args:
            card_id: Card identifier

        Returns:
            Statistics dictionary (retention, intervals, etc.)
        """
        pass

    @abstractmethod
    def get_review_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get review statistics for period

        Args:
            days: Number of days to analyze

        Returns:
            Statistics dictionary (reviews, retention, etc.)
        """
        pass


# ============================================================================
# EMAIL PROCESSOR INTERFACE
# ============================================================================


class IEmailProcessor(ABC):
    """
    Interface for email processing orchestration

    Implementations: EmailProcessor (coordinates all components)
    """

    @abstractmethod
    def process_inbox(
        self,
        limit: Optional[int] = None,
        auto_mode: bool = False,
        confidence_threshold: int = 90,
    ) -> Dict[str, Any]:
        """
        Process emails in inbox

        Args:
            limit: Maximum number of emails to process
            auto_mode: Auto-process high confidence emails
            confidence_threshold: Minimum confidence for auto-processing

        Returns:
            Processing statistics
        """
        pass

    @abstractmethod
    def process_email(
        self,
        email_id: int,
        folder: str = "INBOX",
        auto_mode: bool = False,
    ) -> ProcessedEmail:
        """
        Process single email

        Args:
            email_id: IMAP message UID
            folder: Source folder
            auto_mode: Auto-apply high confidence decisions

        Returns:
            ProcessedEmail with analysis and action

        Raises:
            ValueError: If email not found
        """
        pass

    @abstractmethod
    def apply_action(
        self,
        email_id: int,
        action: EmailAction,
        destination: Optional[str] = None,
        folder: str = "INBOX",
    ) -> None:
        """
        Apply action to email

        Args:
            email_id: IMAP message UID
            action: Action to apply
            destination: Destination folder (for archive/reference)
            folder: Source folder
        """
        pass

    @abstractmethod
    def review_decisions(self, limit: int = 20) -> None:
        """
        Review past decisions (interactive)

        Args:
            limit: Maximum number of decisions to review
        """
        pass

    @abstractmethod
    def process_queue(self) -> Dict[str, Any]:
        """
        Process low-confidence queue (interactive)

        Returns:
            Processing statistics
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, HealthCheck]:
        """
        Check health of all system components

        Returns:
            Dict of service name -> HealthCheck
        """
        pass
