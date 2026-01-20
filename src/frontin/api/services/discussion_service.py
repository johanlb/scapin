"""
Discussion Service

Async service for managing conversation threads with Scapin.
Integrates storage, AI responses, and contextual suggestions.
"""

from dataclasses import dataclass
from typing import Any, Optional

from src.core.config_manager import ScapinConfig
from src.frontin.api.models.discussions import (
    DiscussionCreateRequest,
    DiscussionDetailResponse,
    DiscussionListResponse,
    DiscussionResponse,
    DiscussionType,
    MessageCreateRequest,
    MessageResponse,
    MessageRole,
    QuickChatRequest,
    QuickChatResponse,
    SuggestionResponse,
    SuggestionType,
)
from src.integrations.storage.discussion_storage import (
    DiscussionStorage,
    StoredDiscussion,
    StoredMessage,
    get_discussion_storage,
)
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.services.discussion")


def _stored_message_to_response(msg: StoredMessage) -> MessageResponse:
    """Convert StoredMessage to API response model"""
    return MessageResponse(
        id=msg.id,
        discussion_id=msg.discussion_id,
        role=MessageRole(msg.role),
        content=msg.content,
        created_at=msg.created_at,
        metadata=msg.metadata,
    )


def _stored_discussion_to_response(discussion: StoredDiscussion) -> DiscussionResponse:
    """Convert StoredDiscussion to API response model"""
    return DiscussionResponse(
        id=discussion.id,
        title=discussion.title,
        discussion_type=DiscussionType(discussion.discussion_type),
        attached_to_id=discussion.attached_to_id,
        attached_to_type=discussion.attached_to_type,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
        message_count=discussion.message_count,
        last_message_preview=discussion.last_message_preview,
        metadata=discussion.metadata,
    )


def _stored_discussion_to_detail_response(
    discussion: StoredDiscussion,
    suggestions: Optional[list[SuggestionResponse]] = None,
) -> DiscussionDetailResponse:
    """Convert StoredDiscussion to detailed API response model"""
    return DiscussionDetailResponse(
        id=discussion.id,
        title=discussion.title,
        discussion_type=DiscussionType(discussion.discussion_type),
        attached_to_id=discussion.attached_to_id,
        attached_to_type=discussion.attached_to_type,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
        message_count=discussion.message_count,
        last_message_preview=discussion.last_message_preview,
        metadata=discussion.metadata,
        messages=[_stored_message_to_response(m) for m in discussion.messages],
        suggestions=suggestions or [],
    )


@dataclass
class DiscussionService:
    """
    Discussion service for API endpoints

    Manages conversation threads with storage, AI responses,
    and contextual suggestions.
    """

    config: ScapinConfig
    storage: Optional[DiscussionStorage] = None

    def __post_init__(self) -> None:
        """Initialize storage if not provided"""
        if self.storage is None:
            self.storage = get_discussion_storage()

    async def create_discussion(
        self,
        request: DiscussionCreateRequest,
    ) -> DiscussionDetailResponse:
        """
        Create a new discussion

        Args:
            request: Discussion creation request

        Returns:
            Created discussion with optional initial AI response
        """
        logger.info(
            "Creating discussion",
            extra={
                "title": request.title,
                "type": request.discussion_type.value,
                "attached_to": request.attached_to_id,
            },
        )

        # Create the discussion
        discussion = self.storage.create_discussion(
            title=request.title,
            discussion_type=request.discussion_type.value,
            attached_to_id=request.attached_to_id,
            attached_to_type=request.attached_to_type,
            metadata=request.context or {},
        )

        suggestions: list[SuggestionResponse] = []

        # Add initial user message if provided
        if request.initial_message:
            self.storage.add_message(
                discussion_id=discussion.id,
                role=MessageRole.USER.value,
                content=request.initial_message,
            )

            # Generate AI response
            ai_response = await self._generate_ai_response(
                discussion_id=discussion.id,
                user_message=request.initial_message,
                context=request.context,
            )

            if ai_response:
                self.storage.add_message(
                    discussion_id=discussion.id,
                    role=MessageRole.ASSISTANT.value,
                    content=ai_response,
                )

            # Generate suggestions
            suggestions = await self._generate_suggestions(
                discussion_id=discussion.id,
                context=request.context,
            )

            # Reload discussion with messages
            discussion = self.storage.get_discussion(discussion.id)

        return _stored_discussion_to_detail_response(discussion, suggestions)

    async def get_discussion(
        self,
        discussion_id: str,
    ) -> Optional[DiscussionDetailResponse]:
        """
        Get a discussion by ID with all messages

        Args:
            discussion_id: Discussion ID

        Returns:
            Discussion with messages or None if not found
        """
        discussion = self.storage.get_discussion(discussion_id)
        if not discussion:
            return None

        # Generate contextual suggestions based on current state
        suggestions = await self._generate_suggestions(
            discussion_id=discussion_id,
            context=discussion.metadata,
        )

        return _stored_discussion_to_detail_response(discussion, suggestions)

    async def list_discussions(
        self,
        discussion_type: Optional[DiscussionType] = None,
        attached_to_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DiscussionListResponse:
        """
        List discussions with optional filtering

        Args:
            discussion_type: Filter by type
            attached_to_id: Filter by attached object
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Paginated list of discussions
        """
        offset = (page - 1) * page_size

        discussions, total = self.storage.list_discussions(
            discussion_type=discussion_type.value if discussion_type else None,
            attached_to_id=attached_to_id,
            limit=page_size,
            offset=offset,
        )

        return DiscussionListResponse(
            discussions=[_stored_discussion_to_response(d) for d in discussions],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def add_message(
        self,
        discussion_id: str,
        request: MessageCreateRequest,
    ) -> Optional[DiscussionDetailResponse]:
        """
        Add a message to a discussion and get AI response

        Args:
            discussion_id: Discussion ID
            request: Message to add

        Returns:
            Updated discussion or None if not found
        """
        discussion = self.storage.get_discussion(discussion_id)
        if not discussion:
            return None

        logger.info(
            "Adding message to discussion",
            extra={
                "discussion_id": discussion_id,
                "role": request.role.value,
            },
        )

        # Add user message
        self.storage.add_message(
            discussion_id=discussion_id,
            role=request.role.value,
            content=request.content,
        )

        suggestions: list[SuggestionResponse] = []

        # If user message, generate AI response
        if request.role == MessageRole.USER:
            ai_response = await self._generate_ai_response(
                discussion_id=discussion_id,
                user_message=request.content,
                context=discussion.metadata,
            )

            if ai_response:
                self.storage.add_message(
                    discussion_id=discussion_id,
                    role=MessageRole.ASSISTANT.value,
                    content=ai_response,
                )

            # Generate suggestions
            suggestions = await self._generate_suggestions(
                discussion_id=discussion_id,
                context=discussion.metadata,
            )

        # Reload discussion
        discussion = self.storage.get_discussion(discussion_id)
        return _stored_discussion_to_detail_response(discussion, suggestions)

    async def update_discussion(
        self,
        discussion_id: str,
        title: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[DiscussionResponse]:
        """
        Update discussion metadata

        Args:
            discussion_id: Discussion ID
            title: New title
            metadata: Metadata to merge

        Returns:
            Updated discussion or None if not found
        """
        discussion = self.storage.update_discussion(
            discussion_id=discussion_id,
            title=title,
            metadata=metadata,
        )

        if not discussion:
            return None

        return _stored_discussion_to_response(discussion)

    async def delete_discussion(
        self,
        discussion_id: str,
    ) -> bool:
        """
        Delete a discussion

        Args:
            discussion_id: Discussion ID

        Returns:
            True if deleted, False if not found
        """
        return self.storage.delete_discussion(discussion_id)

    async def quick_chat(
        self,
        request: QuickChatRequest,
    ) -> QuickChatResponse:
        """
        Handle a quick one-off chat (no persistent discussion)

        Args:
            request: Quick chat request

        Returns:
            AI response with suggestions
        """
        logger.info(
            "Processing quick chat",
            extra={
                "context_type": request.context_type,
                "context_id": request.context_id,
            },
        )

        # Build context
        context: dict[str, Any] = {}
        context_used: list[str] = []

        if request.context_type and request.context_id:
            context["type"] = request.context_type
            context["id"] = request.context_id
            context_used.append(request.context_id)

            # Load context based on type
            context_data = await self._load_context(
                context_type=request.context_type,
                context_id=request.context_id,
            )
            if context_data:
                context.update(context_data)

        # Generate response
        response = await self._generate_ai_response(
            discussion_id=None,
            user_message=request.message,
            context=context,
        )

        # Generate suggestions if requested
        suggestions: list[SuggestionResponse] = []
        if request.include_suggestions:
            suggestions = await self._generate_suggestions(
                discussion_id=None,
                context=context,
            )

        return QuickChatResponse(
            response=response or "Je n'ai pas pu traiter votre demande.",
            suggestions=suggestions,
            context_used=context_used,
        )

    async def _generate_ai_response(
        self,
        discussion_id: Optional[str],
        user_message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Generate AI response for a user message

        Args:
            discussion_id: Discussion ID (if in a discussion)
            user_message: User's message
            context: Additional context

        Returns:
            AI response text or None if generation failed
        """
        try:
            # Build conversation history
            history: list[dict[str, str]] = []
            if discussion_id:
                discussion = self.storage.get_discussion(discussion_id)
                if discussion:
                    for msg in discussion.messages[-10:]:  # Last 10 messages for context
                        history.append({"role": msg.role, "content": msg.content})

            # Try to use Sancho for AI generation
            try:
                from src.sancho.router import AIModel, AIRouter

                ai_config = self.config.ai
                router = AIRouter(ai_config)

                # Build prompt with context and history
                system_prompt = self._build_system_prompt(context)

                # Format conversation history into prompt
                history_text = ""
                for msg in history:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    history_text += f"{role}: {msg['content']}\n"

                if history_text:
                    prompt = f"{history_text}User: {user_message}"
                else:
                    prompt = f"User: {user_message}"

                # Use analyze_with_prompt for chat generation
                response, _usage = router.analyze_with_prompt(
                    prompt=prompt,
                    model=AIModel.CLAUDE_HAIKU,  # Use fast model for chat
                    system_prompt=system_prompt,
                    max_tokens=1024,
                )
                return response

            except ImportError:
                logger.warning("AIRouter not available, using fallback response")
                return self._generate_fallback_response(user_message, context)

        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}", exc_info=True)
            return None

    def _build_system_prompt(self, context: Optional[dict[str, Any]] = None) -> str:
        """Build system prompt based on context"""
        base_prompt = (
            "Tu es Scapin, un assistant personnel intelligent et bienveillant. "
            "Tu aides Johan à gérer ses tâches, emails, notes et projets. "
            "Réponds de manière concise, utile et en français."
        )

        if not context:
            return base_prompt

        context_info = []
        if context.get("type") == "note":
            context_info.append("L'utilisateur discute d'une note de sa base de connaissances.")
        elif context.get("type") == "email":
            context_info.append("L'utilisateur discute d'un email.")
        elif context.get("type") == "task":
            context_info.append("L'utilisateur discute d'une tâche OmniFocus.")

        if context_info:
            return f"{base_prompt}\n\nContexte: {' '.join(context_info)}"

        return base_prompt

    def _generate_fallback_response(
        self,
        _user_message: str,
        _context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Generate a fallback response when AI is not available"""
        return (
            "Je suis désolé, je ne peux pas traiter votre demande pour le moment. "
            "Le service d'intelligence artificielle n'est pas disponible. "
            "Veuillez réessayer plus tard."
        )

    async def _generate_suggestions(
        self,
        discussion_id: Optional[str],  # noqa: ARG002
        context: Optional[dict[str, Any]] = None,
    ) -> list[SuggestionResponse]:
        """
        Generate contextual suggestions

        Args:
            discussion_id: Discussion ID (if in a discussion)
            context: Additional context

        Returns:
            List of suggestions
        """
        suggestions: list[SuggestionResponse] = []

        # Add default suggestions based on context type
        context_type = context.get("type") if context else None

        if context_type == "email":
            suggestions.extend([
                SuggestionResponse(
                    type=SuggestionType.ACTION,
                    content="Créer une tâche pour cet email",
                    action_id="create_task",
                    confidence=0.8,
                ),
                SuggestionResponse(
                    type=SuggestionType.ACTION,
                    content="Archiver cet email",
                    action_id="archive_email",
                    confidence=0.7,
                ),
            ])
        elif context_type == "note":
            suggestions.extend([
                SuggestionResponse(
                    type=SuggestionType.QUESTION,
                    content="Quelles sont les prochaines actions pour cette note ?",
                    confidence=0.75,
                ),
                SuggestionResponse(
                    type=SuggestionType.ACTION,
                    content="Lier cette note à un projet",
                    action_id="link_to_project",
                    confidence=0.7,
                ),
            ])
        elif context_type == "task":
            suggestions.extend([
                SuggestionResponse(
                    type=SuggestionType.QUESTION,
                    content="Quel est le statut de cette tâche ?",
                    confidence=0.8,
                ),
                SuggestionResponse(
                    type=SuggestionType.ACTION,
                    content="Reporter cette tâche",
                    action_id="defer_task",
                    confidence=0.6,
                ),
            ])
        else:
            # Generic suggestions
            suggestions.extend([
                SuggestionResponse(
                    type=SuggestionType.QUESTION,
                    content="Qu'est-ce qui est le plus urgent aujourd'hui ?",
                    confidence=0.7,
                ),
                SuggestionResponse(
                    type=SuggestionType.INSIGHT,
                    content="Consulter le briefing du matin",
                    action_id="view_briefing",
                    confidence=0.65,
                ),
            ])

        return suggestions

    async def _load_context(
        self,
        context_type: str,
        context_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Load context data for an object

        Args:
            context_type: Type of object (note, email, task, event)
            context_id: Object ID

        Returns:
            Context data or None
        """
        try:
            if context_type == "note":
                from src.passepartout.note_manager import get_note_manager

                manager = get_note_manager()
                note = manager.get_note(context_id)
                if note:
                    return {
                        "note_title": note.get("title", ""),
                        "note_content": note.get("content", "")[:500],
                        "note_tags": note.get("tags", []),
                    }
            # Add other context types as needed
            return None

        except Exception as e:
            logger.warning(f"Failed to load context {context_type}/{context_id}: {e}")
            return None
