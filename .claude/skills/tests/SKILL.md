---
name: tests
description: Patterns de tests Scapin - pytest fixtures, Playwright E2E, mocks, stratégies de test. Utiliser pour écrire ou débugger des tests.
allowed-tools: Bash, Read, Grep, Glob
---

# Patterns de Tests Scapin

Guide pour écrire des tests efficaces et maintenables.

> **Couverture cible** : Backend 95%+ | E2E 100% pass rate

---

## Structure des Tests

```
tests/                          # Tests backend pytest
├── unit/                       # Tests unitaires isolés
├── integration/                # Tests avec dépendances réelles
├── fixtures/                   # Fixtures partagées
└── conftest.py                 # Configuration pytest globale

web/e2e/                        # Tests E2E Playwright
├── pages/                      # Tests par page
├── fixtures/                   # Fixtures Playwright
└── playwright.config.ts        # Configuration
```

---

## pytest - Backend

### Fixture de Base

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

@pytest.fixture
def sample_email() -> dict:
    """Email de test standard."""
    return {
        "id": "test-123",
        "subject": "Test Subject",
        "from": "sender@example.com",
        "date": datetime.now(timezone.utc),
        "body": "Test body content"
    }

@pytest.fixture
def mock_ai_client() -> MagicMock:
    """Mock du client Anthropic."""
    client = MagicMock()
    client.analyze = AsyncMock(return_value={
        "confidence": 85,
        "action": "archive",
        "reasoning": "Test reasoning"
    })
    return client
```

### Fixture avec Cleanup

```python
@pytest.fixture
def temp_database(tmp_path):
    """Base de données temporaire avec cleanup automatique."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    db.initialize()
    yield db
    db.close()
    # tmp_path est nettoyé automatiquement par pytest
```

### Mock de Service avec Dependency Override

```python
from fastapi.testclient import TestClient

@pytest.fixture
def mock_queue_service() -> MagicMock:
    service = MagicMock()
    service.get_items = AsyncMock(return_value=[])
    service.process_item = AsyncMock(return_value=True)
    return service

@pytest.fixture
def client(mock_queue_service) -> TestClient:
    from src.frontin.api.app import create_app
    from src.frontin.api.deps import get_queue_service

    app = create_app()
    app.dependency_overrides[get_queue_service] = lambda: mock_queue_service

    yield TestClient(app)

    app.dependency_overrides.clear()
```

### Test de Cas d'Erreur

```python
class TestQueueProcessor:
    def test_handles_empty_queue(self, processor):
        """Test avec queue vide."""
        result = processor.process_next()
        assert result is None

    def test_raises_on_invalid_input(self, processor):
        """Test qu'une erreur est levée pour input invalide."""
        with pytest.raises(ValidationError) as exc_info:
            processor.process({"invalid": "data"})

        assert "required field" in str(exc_info.value)
        assert exc_info.value.details["field"] == "subject"

    def test_retries_on_transient_error(self, processor, mock_ai_client):
        """Test de retry sur erreur transitoire."""
        mock_ai_client.analyze.side_effect = [
            NetworkError("timeout"),
            {"confidence": 90, "action": "archive"}
        ]

        result = processor.process(sample_email)

        assert result.success is True
        assert mock_ai_client.analyze.call_count == 2
```

### Test Async

```python
import pytest

@pytest.mark.asyncio
async def test_async_processing(processor, sample_email):
    """Test d'une fonction async."""
    result = await processor.process_async(sample_email)

    assert result.status == "completed"
    assert result.confidence >= 80

@pytest.mark.asyncio
async def test_concurrent_processing(processor):
    """Test de traitement concurrent."""
    emails = [{"id": f"email-{i}"} for i in range(5)]

    results = await processor.process_batch(emails)

    assert len(results) == 5
    assert all(r.success for r in results)
```

### Parametrize pour Cas Multiples

```python
@pytest.mark.parametrize("input_confidence,expected_action", [
    (95, "auto_archive"),
    (80, "suggest_archive"),
    (60, "manual_review"),
    (30, "skip"),
])
def test_action_selection(processor, input_confidence, expected_action):
    """Test de sélection d'action selon la confiance."""
    result = processor.select_action(confidence=input_confidence)
    assert result == expected_action
```

### Mock de Fichier/IO

```python
from unittest.mock import mock_open, patch

def test_reads_config_file(config_manager):
    """Test de lecture de fichier config."""
    mock_content = '{"key": "value"}'

    with patch("builtins.open", mock_open(read_data=mock_content)):
        config = config_manager.load("config.json")

    assert config["key"] == "value"
```

---

## Playwright - E2E

### Structure d'un Test E2E

```typescript
// web/e2e/pages/queue.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Queue Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/flux');
        // Attendre que la page soit chargée
        await page.waitForSelector('[data-testid="queue-list"]');
    });

    test('displays queue items', async ({ page }) => {
        const items = page.locator('[data-testid="queue-item"]');
        await expect(items).toHaveCount.greaterThan(0);
    });

    test('can open item details', async ({ page }) => {
        await page.click('[data-testid="queue-item"]:first-child');
        await expect(page.locator('[data-testid="item-details"]')).toBeVisible();
    });
});
```

### Sélecteurs Recommandés

```typescript
// ✅ Bon - data-testid explicite
await page.click('[data-testid="submit-button"]');

// ✅ Bon - rôle ARIA
await page.click('button[role="submit"]');
await page.getByRole('button', { name: 'Envoyer' });

// ⚠️ Acceptable - texte visible (fragile si traduction)
await page.click('text=Envoyer');

// ❌ Éviter - sélecteur CSS fragile
await page.click('.btn-primary.submit-form');
await page.click('div > div > button');
```

### Attentes Explicites (éviter flakiness)

```typescript
// ❌ Flaky - networkidle peut timeout
await page.goto('/flux', { waitUntil: 'networkidle' });

// ✅ Mieux - attendre un élément spécifique
await page.goto('/flux');
await page.waitForSelector('[data-testid="queue-loaded"]');

// ✅ Attendre une condition
await expect(page.locator('[data-testid="count"]')).toHaveText(/\d+ items/);

// ✅ Attendre la disparition d'un loader
await page.waitForSelector('[data-testid="spinner"]', { state: 'hidden' });
```

### Test avec État Initial

```typescript
test.describe('Empty Queue', () => {
    test.beforeEach(async ({ page }) => {
        // Intercepter l'API pour simuler queue vide
        await page.route('**/api/queue', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ success: true, data: { items: [] } })
            });
        });
        await page.goto('/flux');
    });

    test('shows empty state message', async ({ page }) => {
        await expect(page.locator('[data-testid="empty-state"]')).toBeVisible();
        await expect(page.locator('[data-testid="empty-state"]')).toContainText('Aucun élément');
    });
});
```

### Test de Formulaire

```typescript
test('can submit form', async ({ page }) => {
    // Remplir le formulaire
    await page.fill('[data-testid="input-title"]', 'Mon titre');
    await page.selectOption('[data-testid="select-type"]', 'projet');
    await page.check('[data-testid="checkbox-urgent"]');

    // Soumettre
    await page.click('[data-testid="submit-button"]');

    // Vérifier le résultat
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
});
```

### Test Keyboard Navigation

```typescript
test('supports keyboard navigation', async ({ page }) => {
    await page.goto('/flux');

    // Tab vers le premier item
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Enter pour ouvrir
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-testid="item-details"]')).toBeVisible();

    // Escape pour fermer
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-testid="item-details"]')).not.toBeVisible();
});
```

### Debug de Tests Flaky

```typescript
// Ajouter des logs pour debug
test('flaky test debug', async ({ page }) => {
    await page.goto('/flux');

    // Screenshot avant action
    await page.screenshot({ path: 'debug-before.png' });

    // Log du HTML actuel
    console.log(await page.content());

    // Pause pour inspection manuelle
    // await page.pause();

    await page.click('[data-testid="button"]');
});
```

---

## Commandes

```bash
# Backend - tous les tests
.venv/bin/pytest tests/ -v

# Backend - un fichier spécifique
.venv/bin/pytest tests/unit/test_processor.py -v

# Backend - un test spécifique
.venv/bin/pytest tests/unit/test_processor.py::TestQueue::test_empty -v

# Backend - avec couverture
.venv/bin/pytest tests/ --cov=src --cov-report=html

# Backend - tests marqués
.venv/bin/pytest tests/ -m "not slow" -v

# E2E - tous les tests
cd web && npx playwright test

# E2E - un fichier
cd web && npx playwright test e2e/pages/queue.spec.ts

# E2E - mode UI (debug visuel)
cd web && npx playwright test --ui

# E2E - headed (voir le navigateur)
cd web && npx playwright test --headed

# E2E - debug avec pause
cd web && npx playwright test --debug
```

---

## Anti-patterns Tests

| ❌ Ne pas faire | ✅ Faire |
|-----------------|----------|
| Tester uniquement le happy path | Tester erreurs et cas limites |
| Sélecteurs CSS fragiles | `data-testid` ou rôles ARIA |
| `waitUntil: 'networkidle'` | Attentes explicites sur éléments |
| Tests dépendants de l'ordre | Tests isolés et indépendants |
| Données de test hardcodées | Fixtures réutilisables |
| Mock de tout | Mock uniquement les dépendances externes |
| Ignorer les tests flaky | Corriger ou marquer `@pytest.mark.skip` |

---

## Checklist Test

```
□ Test couvre le cas nominal (happy path)
□ Test couvre les cas d'erreur
□ Test couvre les cas limites (null, vide, max)
□ Fixtures isolées (pas d'état partagé entre tests)
□ Assertions claires et spécifiques
□ Pas de sleep() arbitraire (attentes explicites)
□ data-testid pour les sélecteurs E2E
□ Test peut tourner en parallèle
```
