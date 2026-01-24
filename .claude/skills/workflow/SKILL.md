---
name: workflow
description: Méthodologie Scapin-Clean - Standards de qualité, checklist de fin de tâche, conventions de commit. Utiliser avant de committer ou pour vérifier la conformité du code.
allowed-tools: Bash, Read, Grep
---

# Méthodologie Scapin-Clean

Standards de qualité et workflow pour le développement Scapin.

## Checklist Avant Commit

**→ La checklist BLOQUANTE de référence est dans `CLAUDE.md` section "Discipline de Livraison".**

Résumé rapide :
- Documentation mise à jour (technique + user guide si besoin)
- Tests E2E pour UI, unitaires pour backend
- Test manuel effectué et décrit
- Ruff 0 warning, TypeScript check passe
- Pas de TODO, code commenté, console.log

## Conventions de Commit

Format : `type(scope): description`

**Types :**
| Type | Usage |
|------|-------|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `refactor` | Refactoring sans changement fonctionnel |
| `docs` | Documentation uniquement |
| `test` | Ajout/modification de tests |
| `chore` | Maintenance, dépendances |

**Exemples :**
```
feat(sancho): add multi-pass convergence logic
fix(api): handle null multi_pass in queue response
refactor(valets): rename Jeeves to Frontin
docs: update session notes
test(e2e): fix flaky selectors
```

## Commandes

```bash
# Développement
./scripts/dev.sh                      # Backend + Frontend

# Tests
.venv/bin/pytest tests/ -v            # Backend unitaires
cd web && npx playwright test         # E2E complets
cd web && npx playwright test --ui    # E2E avec UI debug

# Qualité
.venv/bin/ruff check src/ --fix       # Lint Python + autofix
cd web && npm run check               # Types TypeScript

# CLI Scapin
python scapin.py --help
```

## Structure du Projet

```
scapin/
├── src/
│   ├── trivelin/       # Perception & triage
│   ├── sancho/         # Raisonnement IA
│   ├── passepartout/   # Base de connaissances
│   ├── planchet/       # Planification
│   ├── figaro/         # Orchestration
│   ├── sganarelle/     # Apprentissage
│   ├── frontin/        # API & CLI
│   └── core/           # Infrastructure partagée
├── web/                # Frontend SvelteKit
├── tests/              # Tests backend
└── docs/               # Documentation
    └── user-guide/     # Guide utilisateur (specs)
```

## Fichiers Critiques

**Ne pas modifier sans review (demander à Johan) :**

| Fichier | Rôle |
|---------|------|
| `src/trivelin/v2_processor.py` | Pipeline Multi-Pass v2.2 |
| `src/sancho/multi_pass_analyzer.py` | Convergence IA |
| `src/passepartout/note_manager.py` | Gestion notes |
| `src/core/config_manager.py` | Configuration globale |

## Qualité du Code

### Python (Ruff)
- 0 warning toléré
- Type hints obligatoires
- Docstrings pour fonctions publiques

### TypeScript/Svelte
- `npm run check` doit passer
- Types explicites, pas de `any`
- Svelte 5 runes : `$state`, `$derived`, `$effect`

### Tests
- Couverture backend : 95%+
- Tests E2E : 100% pass rate
- **Tester les cas d'erreur**, pas seulement le happy path

---

## Patterns de Code

### 1. Nouvel Endpoint API

```python
from fastapi import APIRouter, Depends, Query, HTTPException
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.mymodule")
router = APIRouter()

@router.get("/items", response_model=APIResponse[ItemsResponse])
async def get_items(
    limit: int = Query(10, ge=1, le=100),
    service: MyService = Depends(get_my_service),
) -> APIResponse[ItemsResponse]:
    """Get items with pagination."""
    try:
        items = await service.get_items(limit=limit)
        return APIResponse(success=True, data=items, timestamp=datetime.now(timezone.utc))
    except ScapinError as e:
        logger.error(f"Failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=e.message) from e
```

### 2. Logger avec Extra Fields

```python
from src.monitoring.logger import get_logger

logger = get_logger("module.name")  # Au top du fichier

# Simple
logger.info("Processing started")

# Avec contexte (JSON structuré)
logger.info("Email processed", extra={"email_id": "abc", "action": "archive", "confidence": 95})

# Avec exception
logger.error("Failed to process", extra={"email_id": "def"}, exc_info=True)
```

### 3. Gestion des Erreurs

```python
from src.core.exceptions import ScapinError, ValidationError

# Lever une erreur
if size > limit:
    raise ValidationError(f"Size {size} exceeds {limit}", details={"size": size, "limit": limit})

# Attraper les erreurs Scapin
try:
    result = process()
except ScapinError as e:
    logger.error(f"Error: {e}", exc_info=True)
    # e.message, e.details disponibles
```

### 4. Test Unitaire pytest

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

@pytest.fixture
def sample_data() -> MyModel:
    return MyModel(id="test-123", name="Test")

@pytest.fixture
def mock_service(sample_data) -> MagicMock:
    service = MagicMock()
    service.get_items = AsyncMock(return_value=[sample_data])
    return service

@pytest.fixture
def client(mock_service) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_my_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()

class TestGetItems:
    def test_returns_success(self, client: TestClient) -> None:
        response = client.get("/api/items")
        assert response.status_code == 200
        assert response.json()["success"] is True
```

### 5. Composant Svelte 5

```svelte
<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        title: string;
        variant?: 'primary' | 'secondary';
        loading?: boolean;
        onclick?: () => void;
        children?: Snippet;
    }

    let { title, variant = 'primary', loading = false, onclick, children }: Props = $props();

    // État réactif
    let count = $state(0);

    // Computed
    const doubled = $derived(count * 2);
</script>

<button class="btn-{variant}" disabled={loading} {onclick}>
    {#if loading}
        <span class="spinner" />
    {/if}
    {title}
    {#if children}{@render children()}{/if}
</button>
```

### 6. EventBus (Événements)

```python
from src.core.processing_events import EventBus, ProcessingEvent, ProcessingEventType

bus = EventBus()

# S'abonner
def my_handler(event: ProcessingEvent):
    logger.info(f"Event: {event.event_type}", extra={"email_id": event.email_id})

bus.subscribe(ProcessingEventType.EMAIL_COMPLETED, my_handler)

# Émettre
bus.emit(ProcessingEvent(
    event_type=ProcessingEventType.EMAIL_COMPLETED,
    email_id=123,
    subject="Test"
))
```

---

## Résumé des Conventions

| Domaine | Convention |
|---------|-----------|
| **Logger** | `get_logger("module.name")` au top, `extra={}` pour contexte |
| **Erreurs** | Hériter `ScapinError`, inclure `details` dict |
| **API** | `APIResponse[T]`, `Depends()` pour injection |
| **Tests** | `@pytest.fixture` + `AsyncMock` + `TestClient` |
| **Svelte** | `interface Props` + `$props()` + `$state` + `$derived` |
