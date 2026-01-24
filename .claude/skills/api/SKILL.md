---
name: api
description: Architecture API Scapin - Endpoints, conventions FastAPI, client TypeScript, authentification. Utiliser pour créer ou modifier des endpoints API.
allowed-tools: Read, Grep, Glob, Bash
---

# Architecture API Scapin

Guide pour développer et maintenir l'API REST Scapin.

> **Fichiers clés** : `src/frontin/api/` (endpoints), `web/src/lib/api/` (client TS)

---

## Structure des Endpoints

```
src/frontin/api/
├── __init__.py         # Router principal
├── queue.py            # /api/queue/* - Péripéties
├── notes.py            # /api/notes/* - Notes PKM
├── briefing.py         # /api/briefing/* - Briefings
├── valets.py           # /api/valets/* - Monitoring valets
├── config.py           # /api/config/* - Configuration
├── health.py           # /api/health - Health check
└── models/             # Pydantic models
    ├── requests.py     # Input models
    └── responses.py    # Output models
```

---

## Conventions FastAPI

### Pattern Standard pour Endpoint

```python
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from src.frontin.api.models.responses import APIResponse
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.module")
router = APIRouter()

@router.get("/items", response_model=APIResponse[ItemsResponse])
async def get_items(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Max items"),
    offset: int = Query(0, ge=0, description="Offset"),
    service: MyService = Depends(get_service),
) -> APIResponse[ItemsResponse]:
    """
    Get items with pagination.

    Returns list of items sorted by date.
    """
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")

    try:
        items = await service.get_items(limit=limit, offset=offset)
        return APIResponse(
            success=True,
            data=ItemsResponse(items=items, total=len(items)),
            timestamp=datetime.now(timezone.utc)
        )
    except ScapinError as e:
        logger.error(
            f"Failed to get items: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise HTTPException(status_code=400, detail=e.message) from e
```

### Règles

| Règle | Description |
|-------|-------------|
| **Async everywhere** | `async def` pour toutes les fonctions, y compris dependencies |
| **Service Layer** | Logique métier dans services, pas dans endpoints |
| **Correlation ID** | Toujours logger avec correlation ID pour traçabilité |
| **Pydantic models** | Input/Output typés, jamais de `dict` brut |
| **Query validation** | Utiliser `Query()` avec `ge`, `le`, `description` |

---

## Response Models

### APIResponse Standard

```python
from pydantic import BaseModel
from typing import Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    success: bool
    data: T | None = None
    error: str | None = None
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### Pagination

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool
```

### Conventions de Nommage

| Type | Convention | Exemple |
|------|------------|---------|
| Request body | `{Action}Request` | `CreateNoteRequest` |
| Response data | `{Resource}Response` | `NoteResponse` |
| List response | `{Resource}ListResponse` | `NotesListResponse` |
| Detail response | `{Resource}DetailResponse` | `NoteDetailResponse` |

---

## Client TypeScript

### Structure

```
web/src/lib/api/
├── client.ts           # Fetch wrapper avec error handling
├── types/              # Types générés depuis Pydantic
│   ├── queue.ts
│   ├── notes.ts
│   └── common.ts
├── queue.ts            # API queue
├── notes.ts            # API notes
└── index.ts            # Exports
```

### Pattern Client

```typescript
// web/src/lib/api/notes.ts
import { apiClient, type APIResponse } from './client';
import type { Note, CreateNoteRequest } from './types/notes';

export async function getNotes(params?: { limit?: number }): Promise<Note[]> {
    const response = await apiClient.get<APIResponse<{ items: Note[] }>>(
        '/api/notes',
        { params }
    );
    return response.data?.items ?? [];
}

export async function createNote(data: CreateNoteRequest): Promise<Note> {
    const response = await apiClient.post<APIResponse<Note>>(
        '/api/notes',
        data
    );
    if (!response.success || !response.data) {
        throw new Error(response.error ?? 'Failed to create note');
    }
    return response.data;
}
```

### Error Handling

```typescript
// web/src/lib/api/client.ts
export class APIError extends Error {
    constructor(
        message: string,
        public status: number,
        public code?: string
    ) {
        super(message);
        this.name = 'APIError';
    }
}

export async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new APIError(
            error.detail ?? response.statusText,
            response.status,
            error.code
        );
    }
    return response.json();
}
```

---

## Endpoints Existants

### Queue (Péripéties)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/queue` | GET | Liste des items en queue |
| `/api/queue/{id}` | GET | Détail d'un item |
| `/api/queue/{id}/decide` | POST | Appliquer une décision |
| `/api/queue/{id}/skip` | POST | Passer un item |
| `/api/queue/{id}/reanalyze` | POST | Relancer l'analyse |
| `/api/queue/stats` | GET | Statistiques de la queue |

### Notes

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/notes` | GET | Liste des notes (avec recherche) |
| `/api/notes/{id}` | GET | Détail d'une note |
| `/api/notes/{id}` | PATCH | Modifier une note |
| `/api/notes/tree` | GET | Arborescence des dossiers |
| `/api/notes/search` | POST | Recherche hybride |
| `/api/notes/reindex` | POST | Reconstruire l'index FAISS |

### Briefing

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/briefing/daily` | GET | Briefing du jour |
| `/api/briefing/meeting/{id}` | GET | Briefing pré-réunion |

### Health & Monitoring

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/health` | GET | Health check complet |
| `/api/stats` | GET | Statistiques globales |
| `/api/valets` | GET | État des valets |
| `/api/valets/{name}/metrics` | GET | Métriques d'un valet |

---

## Ajouter un Nouvel Endpoint

### Checklist

```
□ Créer le router dans src/frontin/api/{module}.py
□ Définir les Pydantic models (request/response)
□ Implémenter la logique dans un service (pas dans l'endpoint)
□ Ajouter le router dans src/frontin/api/__init__.py
□ Créer les types TypeScript correspondants
□ Créer les fonctions client dans web/src/lib/api/
□ Écrire les tests pytest
□ Documenter dans ARCHITECTURE.md si endpoint majeur
```

### Exemple Complet

**1. Backend - Models**
```python
# src/frontin/api/models/requests.py
class CreateWidgetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: WidgetType
    config: dict[str, Any] = Field(default_factory=dict)

# src/frontin/api/models/responses.py
class WidgetResponse(BaseModel):
    id: str
    name: str
    type: WidgetType
    created_at: datetime
```

**2. Backend - Service**
```python
# src/frontin/services/widget_service.py
class WidgetService:
    async def create(self, request: CreateWidgetRequest) -> Widget:
        # Logique métier ici
        ...
```

**3. Backend - Endpoint**
```python
# src/frontin/api/widgets.py
@router.post("/widgets", response_model=APIResponse[WidgetResponse])
async def create_widget(
    request: Request,
    data: CreateWidgetRequest,
    service: WidgetService = Depends(get_widget_service),
) -> APIResponse[WidgetResponse]:
    widget = await service.create(data)
    return APIResponse(success=True, data=widget)
```

**4. Frontend - Types**
```typescript
// web/src/lib/api/types/widgets.ts
export interface Widget {
    id: string;
    name: string;
    type: WidgetType;
    created_at: string;
}

export interface CreateWidgetRequest {
    name: string;
    type: WidgetType;
    config?: Record<string, unknown>;
}
```

**5. Frontend - Client**
```typescript
// web/src/lib/api/widgets.ts
export async function createWidget(data: CreateWidgetRequest): Promise<Widget> {
    const response = await apiClient.post<APIResponse<Widget>>('/api/widgets', data);
    if (!response.success) throw new APIError(response.error ?? 'Failed');
    return response.data!;
}
```

---

## Tests API

### pytest avec TestClient

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_service():
    service = MagicMock()
    service.get_items = AsyncMock(return_value=[])
    return service

@pytest.fixture
def client(mock_service):
    from src.frontin.api import create_app
    app = create_app()
    app.dependency_overrides[get_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()

class TestGetItems:
    def test_returns_empty_list(self, client):
        response = client.get("/api/items")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["items"] == []

    def test_validates_limit(self, client):
        response = client.get("/api/items?limit=999")
        assert response.status_code == 422  # Validation error
```

---

## Anti-patterns API

| ❌ Ne pas faire | ✅ Faire |
|-----------------|----------|
| Logique métier dans endpoint | Service layer séparé |
| `def` pour dependencies | `async def` toujours |
| Retourner `dict` | Pydantic model typé |
| Ignorer correlation ID | Logger avec correlation ID |
| `try/except: pass` | Propager ou logger l'erreur |
| Endpoint sans docstring | Docstring pour OpenAPI |

---

## Ressources

- **OpenAPI docs** : `http://localhost:8000/docs` (Swagger UI)
- **ReDoc** : `http://localhost:8000/redoc`
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
