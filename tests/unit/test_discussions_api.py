"""
Tests for Discussions API

Tests for storage, service, and router layers of the Discussions API.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.integrations.storage.discussion_storage import DiscussionStorage
from src.jeeves.api.app import create_app
from src.jeeves.api.deps import get_cached_config, get_discussion_service
from src.jeeves.api.models.discussions import (
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
from src.jeeves.api.services.discussion_service import DiscussionService


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for test storage"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock configuration"""
    config = MagicMock()

    # Auth config
    config.auth.enabled = False
    config.auth.jwt_secret_key = "test-secret-key-minimum-32-characters"
    config.auth.jwt_algorithm = "HS256"
    config.auth.jwt_expire_minutes = 60

    # AI config
    config.ai.model = "claude-3-5-haiku-20241022"
    config.ai.anthropic_api_key = "test-key"

    return config


@pytest.fixture
def client(mock_config: MagicMock) -> TestClient:
    """Create test client with mocked config"""
    app = create_app()
    app.dependency_overrides[get_cached_config] = lambda: mock_config
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestDiscussionStorage:
    """Tests for DiscussionStorage"""

    def test_create_discussion(self, temp_storage_dir: Path) -> None:
        """Test creating a new discussion"""
        storage = DiscussionStorage(temp_storage_dir)

        discussion = storage.create_discussion(
            title="Test Discussion",
            discussion_type="free",
        )

        assert discussion.id is not None
        assert discussion.title == "Test Discussion"
        assert discussion.discussion_type == "free"
        assert discussion.message_count == 0

    def test_create_discussion_attached_to_object(self, temp_storage_dir: Path) -> None:
        """Test creating discussion attached to an object"""
        storage = DiscussionStorage(temp_storage_dir)

        discussion = storage.create_discussion(
            title="Email Discussion",
            discussion_type="email",
            attached_to_id="email-123",
            attached_to_type="email",
        )

        assert discussion.attached_to_id == "email-123"
        assert discussion.attached_to_type == "email"
        assert discussion.discussion_type == "email"

    def test_get_discussion(self, temp_storage_dir: Path) -> None:
        """Test getting a discussion by ID"""
        storage = DiscussionStorage(temp_storage_dir)

        created = storage.create_discussion(title="Test")
        retrieved = storage.get_discussion(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test"

    def test_get_discussion_not_found(self, temp_storage_dir: Path) -> None:
        """Test getting a non-existent discussion"""
        storage = DiscussionStorage(temp_storage_dir)

        result = storage.get_discussion("non-existent-id")

        assert result is None

    def test_list_discussions(self, temp_storage_dir: Path) -> None:
        """Test listing discussions"""
        storage = DiscussionStorage(temp_storage_dir)

        storage.create_discussion(title="Discussion 1")
        storage.create_discussion(title="Discussion 2")
        storage.create_discussion(title="Discussion 3")

        discussions, total = storage.list_discussions()

        assert total == 3
        assert len(discussions) == 3

    def test_list_discussions_with_filter(self, temp_storage_dir: Path) -> None:
        """Test listing discussions with type filter"""
        storage = DiscussionStorage(temp_storage_dir)

        storage.create_discussion(title="Free 1", discussion_type="free")
        storage.create_discussion(title="Email 1", discussion_type="email")
        storage.create_discussion(title="Free 2", discussion_type="free")

        discussions, total = storage.list_discussions(discussion_type="email")

        assert total == 1
        assert discussions[0].title == "Email 1"

    def test_list_discussions_with_pagination(self, temp_storage_dir: Path) -> None:
        """Test listing discussions with pagination"""
        storage = DiscussionStorage(temp_storage_dir)

        for i in range(5):
            storage.create_discussion(title=f"Discussion {i}")

        discussions, total = storage.list_discussions(limit=2, offset=2)

        assert total == 5
        assert len(discussions) == 2

    def test_add_message(self, temp_storage_dir: Path) -> None:
        """Test adding a message to a discussion"""
        storage = DiscussionStorage(temp_storage_dir)

        discussion = storage.create_discussion(title="Test")
        message = storage.add_message(
            discussion_id=discussion.id,
            role="user",
            content="Hello!",
        )

        assert message is not None
        assert message.content == "Hello!"
        assert message.role == "user"
        assert message.discussion_id == discussion.id

        # Reload and check
        updated = storage.get_discussion(discussion.id)
        assert updated.message_count == 1

    def test_add_message_to_nonexistent_discussion(
        self, temp_storage_dir: Path
    ) -> None:
        """Test adding a message to non-existent discussion"""
        storage = DiscussionStorage(temp_storage_dir)

        result = storage.add_message(
            discussion_id="non-existent",
            role="user",
            content="Hello!",
        )

        assert result is None

    def test_update_discussion(self, temp_storage_dir: Path) -> None:
        """Test updating discussion metadata"""
        storage = DiscussionStorage(temp_storage_dir)

        discussion = storage.create_discussion(title="Original")
        updated = storage.update_discussion(discussion.id, title="Updated")

        assert updated is not None
        assert updated.title == "Updated"

    def test_delete_discussion(self, temp_storage_dir: Path) -> None:
        """Test deleting a discussion"""
        storage = DiscussionStorage(temp_storage_dir)

        discussion = storage.create_discussion(title="To Delete")
        result = storage.delete_discussion(discussion.id)

        assert result is True
        assert storage.get_discussion(discussion.id) is None

    def test_delete_nonexistent_discussion(self, temp_storage_dir: Path) -> None:
        """Test deleting non-existent discussion"""
        storage = DiscussionStorage(temp_storage_dir)

        result = storage.delete_discussion("non-existent")

        assert result is False


class TestDiscussionModels:
    """Tests for Discussion Pydantic models"""

    def test_discussion_response_model(self) -> None:
        """Test DiscussionResponse model"""
        now = datetime.now(timezone.utc)
        response = DiscussionResponse(
            id="test-123",
            title="Test Discussion",
            discussion_type=DiscussionType.FREE,
            created_at=now,
            updated_at=now,
            message_count=5,
        )

        assert response.id == "test-123"
        assert response.title == "Test Discussion"
        assert response.discussion_type == DiscussionType.FREE
        assert response.message_count == 5

    def test_message_response_model(self) -> None:
        """Test MessageResponse model"""
        now = datetime.now(timezone.utc)
        response = MessageResponse(
            id="msg-123",
            discussion_id="disc-456",
            role=MessageRole.USER,
            content="Hello there!",
            created_at=now,
        )

        assert response.id == "msg-123"
        assert response.role == MessageRole.USER
        assert response.content == "Hello there!"

    def test_suggestion_response_model(self) -> None:
        """Test SuggestionResponse model"""
        response = SuggestionResponse(
            type=SuggestionType.ACTION,
            content="Create a task",
            action_id="create_task",
            confidence=0.85,
        )

        assert response.type == SuggestionType.ACTION
        assert response.confidence == 0.85

    def test_discussion_create_request(self) -> None:
        """Test DiscussionCreateRequest model"""
        request = DiscussionCreateRequest(
            title="New Discussion",
            discussion_type=DiscussionType.NOTE,
            attached_to_id="note-123",
            initial_message="Let's talk about this note",
        )

        assert request.title == "New Discussion"
        assert request.discussion_type == DiscussionType.NOTE
        assert request.initial_message is not None

    def test_quick_chat_request(self) -> None:
        """Test QuickChatRequest model"""
        request = QuickChatRequest(
            message="What's urgent today?",
            include_suggestions=True,
        )

        assert request.message == "What's urgent today?"
        assert request.include_suggestions is True


class TestDiscussionService:
    """Tests for DiscussionService"""

    @pytest.fixture
    def service(self, temp_storage_dir: Path, mock_config: MagicMock) -> DiscussionService:
        """Create service with temp storage"""
        storage = DiscussionStorage(temp_storage_dir)
        return DiscussionService(config=mock_config, storage=storage)

    @pytest.mark.asyncio
    async def test_create_discussion(self, service: DiscussionService) -> None:
        """Test creating a discussion through service"""
        request = DiscussionCreateRequest(title="Test Discussion")

        result = await service.create_discussion(request)

        assert result is not None
        assert result.title == "Test Discussion"
        assert result.discussion_type == DiscussionType.FREE

    @pytest.mark.asyncio
    async def test_create_discussion_with_initial_message(
        self, service: DiscussionService
    ) -> None:
        """Test creating discussion with initial message"""
        request = DiscussionCreateRequest(
            title="Test",
            initial_message="Hello Scapin!",
        )

        # Mock AI response
        with patch.object(
            service, "_generate_ai_response", new=AsyncMock(return_value="Hi there!")
        ):
            result = await service.create_discussion(request)

        # Should have 2 messages: user + assistant
        assert result.message_count >= 1

    @pytest.mark.asyncio
    async def test_get_discussion(self, service: DiscussionService) -> None:
        """Test getting a discussion"""
        request = DiscussionCreateRequest(title="Test")
        created = await service.create_discussion(request)

        result = await service.get_discussion(created.id)

        assert result is not None
        assert result.id == created.id

    @pytest.mark.asyncio
    async def test_get_discussion_not_found(self, service: DiscussionService) -> None:
        """Test getting non-existent discussion"""
        result = await service.get_discussion("non-existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_discussions(self, service: DiscussionService) -> None:
        """Test listing discussions"""
        await service.create_discussion(DiscussionCreateRequest(title="D1"))
        await service.create_discussion(DiscussionCreateRequest(title="D2"))

        result = await service.list_discussions()

        assert result.total == 2
        assert len(result.discussions) == 2

    @pytest.mark.asyncio
    async def test_add_message(self, service: DiscussionService) -> None:
        """Test adding a message to a discussion"""
        created = await service.create_discussion(
            DiscussionCreateRequest(title="Test")
        )

        request = MessageCreateRequest(content="New message")

        with patch.object(
            service, "_generate_ai_response", new=AsyncMock(return_value="Response")
        ):
            result = await service.add_message(created.id, request)

        assert result is not None
        assert result.message_count >= 1

    @pytest.mark.asyncio
    async def test_delete_discussion(self, service: DiscussionService) -> None:
        """Test deleting a discussion"""
        created = await service.create_discussion(
            DiscussionCreateRequest(title="To Delete")
        )

        result = await service.delete_discussion(created.id)

        assert result is True

        # Verify it's gone
        retrieved = await service.get_discussion(created.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_quick_chat(self, service: DiscussionService) -> None:
        """Test quick chat without persistent discussion"""
        request = QuickChatRequest(message="What's the weather?")

        with patch.object(
            service, "_generate_ai_response", new=AsyncMock(return_value="I don't know")
        ):
            result = await service.quick_chat(request)

        assert result is not None
        assert result.response is not None


class TestDiscussionEndpoints:
    """Tests for /api/discussions endpoints"""

    @pytest.fixture
    def client_with_auth(self) -> TestClient:
        """Create test client with auth disabled"""
        mock_config = MagicMock()
        mock_config.auth.enabled = False
        mock_config.auth.jwt_secret_key = "test-secret-key-minimum-32-characters"
        mock_config.auth.jwt_algorithm = "HS256"
        mock_config.auth.jwt_expire_minutes = 60
        mock_config.auth.pin_hash = ""
        mock_config.api.cors_origins = ["*"]
        mock_config.api.cors_methods = ["*"]
        mock_config.api.cors_headers = ["*"]
        mock_config.environment = "test"
        mock_config.ai.model = "claude-3-5-haiku-20241022"

        with (
            patch("src.jeeves.api.deps.get_cached_config", return_value=mock_config),
            patch("src.core.config_manager.get_config", return_value=mock_config),
            patch("src.jeeves.api.auth.jwt_handler.get_config", return_value=mock_config),
        ):
            app = create_app()
            yield TestClient(app)

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        """Create mock service"""
        service = MagicMock(spec=DiscussionService)

        now = datetime.now(timezone.utc)
        mock_discussion = DiscussionDetailResponse(
            id="disc-123",
            title="Test Discussion",
            discussion_type=DiscussionType.FREE,
            created_at=now,
            updated_at=now,
            message_count=0,
            messages=[],
            suggestions=[],
        )
        service.create_discussion = AsyncMock(return_value=mock_discussion)
        service.get_discussion = AsyncMock(return_value=mock_discussion)
        service.list_discussions = AsyncMock(
            return_value=DiscussionListResponse(
                discussions=[
                    DiscussionResponse(
                        id="disc-123",
                        title="Test",
                        discussion_type=DiscussionType.FREE,
                        created_at=now,
                        updated_at=now,
                        message_count=0,
                    )
                ],
                total=1,
                page=1,
                page_size=20,
            )
        )
        service.add_message = AsyncMock(return_value=mock_discussion)
        service.update_discussion = AsyncMock(
            return_value=DiscussionResponse(
                id="disc-123",
                title="Updated",
                discussion_type=DiscussionType.FREE,
                created_at=now,
                updated_at=now,
                message_count=0,
            )
        )
        service.delete_discussion = AsyncMock(return_value=True)
        service.quick_chat = AsyncMock(
            return_value=QuickChatResponse(
                response="Hello!",
                suggestions=[],
                context_used=[],
            )
        )

        return service

    def test_create_discussion(
        self, client_with_auth: TestClient, mock_service: MagicMock
    ) -> None:
        """Test POST /api/discussions"""
        app = client_with_auth.app
        app.dependency_overrides[get_discussion_service] = lambda: mock_service

        response = client_with_auth.post(
            "/api/discussions",
            json={"title": "New Discussion"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "disc-123"

    def test_list_discussions(
        self, client_with_auth: TestClient, mock_service: MagicMock
    ) -> None:
        """Test GET /api/discussions"""
        app = client_with_auth.app
        app.dependency_overrides[get_discussion_service] = lambda: mock_service

        response = client_with_auth.get("/api/discussions")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 1
        assert len(data["data"]["discussions"]) == 1

    def test_get_discussion(
        self, client_with_auth: TestClient, mock_service: MagicMock
    ) -> None:
        """Test GET /api/discussions/{id}"""
        app = client_with_auth.app
        app.dependency_overrides[get_discussion_service] = lambda: mock_service

        response = client_with_auth.get("/api/discussions/disc-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "disc-123"

    def test_get_discussion_not_found(
        self, client_with_auth: TestClient, mock_service: MagicMock
    ) -> None:
        """Test GET /api/discussions/{id} with non-existent ID"""
        app = client_with_auth.app
        mock_service.get_discussion = AsyncMock(return_value=None)
        app.dependency_overrides[get_discussion_service] = lambda: mock_service

        response = client_with_auth.get("/api/discussions/non-existent")

        assert response.status_code == 404

    def test_add_message(
        self, client_with_auth: TestClient, mock_service: MagicMock
    ) -> None:
        """Test POST /api/discussions/{id}/messages"""
        app = client_with_auth.app
        app.dependency_overrides[get_discussion_service] = lambda: mock_service

        response = client_with_auth.post(
            "/api/discussions/disc-123/messages",
            json={"content": "Hello!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_discussion(
        self, client_with_auth: TestClient, mock_service: MagicMock
    ) -> None:
        """Test DELETE /api/discussions/{id}"""
        app = client_with_auth.app
        app.dependency_overrides[get_discussion_service] = lambda: mock_service

        response = client_with_auth.delete("/api/discussions/disc-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] is True

    def test_quick_chat(
        self, client_with_auth: TestClient, mock_service: MagicMock
    ) -> None:
        """Test POST /api/discussions/quick"""
        app = client_with_auth.app
        app.dependency_overrides[get_discussion_service] = lambda: mock_service

        response = client_with_auth.post(
            "/api/discussions/quick",
            json={"message": "What's urgent?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["response"] == "Hello!"
