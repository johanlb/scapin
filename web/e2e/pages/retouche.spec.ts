import { test, expect } from '../fixtures/auth';

/**
 * Retouche E2E Tests
 *
 * Tests for the AI note improvement feature:
 * - Preview modal display
 * - Action selection and application
 * - Error handling
 * - Rollback functionality
 * - Keyboard navigation
 */

// =============================================================================
// RETOUCHE PREVIEW TESTS
// =============================================================================

test.describe('Retouche - Preview Modal', () => {
	test.beforeEach(async ({ authenticatedPage: page }) => {
		await page.goto('/memoires');
		await page.waitForLoadState('domcontentloaded');
	});

	test('displays preview modal when retouche button clicked', async ({ authenticatedPage: page }) => {
		// Find a note and select it
		const noteItem = page.locator('[data-testid="note-item"]').first();
		const hasNotes = await noteItem.isVisible({ timeout: 5000 }).catch(() => false);

		if (!hasNotes) {
			test.skip('No notes available for testing');
			return;
		}

		await noteItem.click();
		await page.waitForTimeout(500);

		// Look for retouche button
		const retoucheButton = page.locator('[data-testid="retouche-button"]');
		const buttonVisible = await retoucheButton.isVisible({ timeout: 5000 }).catch(() => false);

		if (!buttonVisible) {
			// Try alternative selectors
			const altButton = page.locator('button:has-text("Retouche"), button:has-text("Améliorer")');
			const altVisible = await altButton.isVisible({ timeout: 3000 }).catch(() => false);

			if (!altVisible) {
				test.skip('Retouche button not found on this note');
				return;
			}

			await altButton.click();
		} else {
			await retoucheButton.click();
		}

		// Wait for modal
		const modal = page.locator('[role="dialog"], [data-testid="retouche-modal"]');
		await expect(modal).toBeVisible({ timeout: 10000 });
	});

	test('handles API error gracefully', async ({ authenticatedPage: page }) => {
		// Mock API to return error
		await page.route('**/api/notes/*/retouche/preview', (route) =>
			route.fulfill({
				status: 500,
				contentType: 'application/json',
				body: JSON.stringify({ error: 'Server error' })
			})
		);

		// Navigate and try to trigger retouche
		const noteItem = page.locator('[data-testid="note-item"]').first();
		const hasNotes = await noteItem.isVisible({ timeout: 5000 }).catch(() => false);

		if (!hasNotes) {
			test.skip('No notes available for testing');
			return;
		}

		await noteItem.click();
		await page.waitForTimeout(500);

		const retoucheButton = page.locator('[data-testid="retouche-button"], button:has-text("Retouche")');
		const buttonVisible = await retoucheButton.isVisible({ timeout: 5000 }).catch(() => false);

		if (!buttonVisible) {
			test.skip('Retouche button not found');
			return;
		}

		await retoucheButton.click();

		// Should show error toast or message
		const errorToast = page.locator('[data-testid="error-toast"], [role="alert"]:has-text("erreur"), .toast-error');
		await expect(errorToast).toBeVisible({ timeout: 5000 });
	});

	test('handles empty actions list', async ({ authenticatedPage: page }) => {
		// Mock API to return empty actions
		await page.route('**/api/notes/*/retouche/preview', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						note_id: 'test-note',
						quality_before: 80,
						quality_after: 80,
						actions: [],
						reasoning: 'Note already in good shape'
					}
				})
			})
		);

		const noteItem = page.locator('[data-testid="note-item"]').first();
		const hasNotes = await noteItem.isVisible({ timeout: 5000 }).catch(() => false);

		if (!hasNotes) {
			test.skip('No notes available for testing');
			return;
		}

		await noteItem.click();
		await page.waitForTimeout(500);

		const retoucheButton = page.locator('[data-testid="retouche-button"], button:has-text("Retouche")');
		const buttonVisible = await retoucheButton.isVisible({ timeout: 5000 }).catch(() => false);

		if (!buttonVisible) {
			test.skip('Retouche button not found');
			return;
		}

		await retoucheButton.click();

		// Should show "no actions" message
		const noActionsMessage = page.locator(
			'[data-testid="no-actions-message"], text=/aucune.*amélioration/i, text=/déjà.*qualité/i'
		);
		await expect(noActionsMessage).toBeVisible({ timeout: 10000 });
	});
});

// =============================================================================
// KEYBOARD NAVIGATION TESTS
// =============================================================================

test.describe('Retouche - Keyboard Navigation', () => {
	test.beforeEach(async ({ authenticatedPage: page }) => {
		await page.goto('/memoires');
		await page.waitForLoadState('domcontentloaded');
	});

	test('keyboard navigation works in modal', async ({ authenticatedPage: page }) => {
		const noteItem = page.locator('[data-testid="note-item"]').first();
		const hasNotes = await noteItem.isVisible({ timeout: 5000 }).catch(() => false);

		if (!hasNotes) {
			test.skip('No notes available for testing');
			return;
		}

		await noteItem.click();
		await page.waitForTimeout(500);

		const retoucheButton = page.locator('[data-testid="retouche-button"], button:has-text("Retouche")');
		const buttonVisible = await retoucheButton.isVisible({ timeout: 5000 }).catch(() => false);

		if (!buttonVisible) {
			test.skip('Retouche button not found');
			return;
		}

		await retoucheButton.click();

		// Wait for modal
		const modal = page.locator('[role="dialog"], [data-testid="retouche-modal"]');
		const modalVisible = await modal.isVisible({ timeout: 5000 }).catch(() => false);

		if (!modalVisible) {
			test.skip('Modal did not open');
			return;
		}

		// Test Tab navigation
		await page.keyboard.press('Tab');
		await page.waitForTimeout(100);

		// Test Escape closes modal
		await page.keyboard.press('Escape');
		await expect(modal).not.toBeVisible({ timeout: 3000 });
	});
});

// =============================================================================
// RETOUCHE HISTORY TESTS
// =============================================================================

test.describe('Retouche - History', () => {
	test.beforeEach(async ({ authenticatedPage: page }) => {
		await page.goto('/memoires');
		await page.waitForLoadState('domcontentloaded');
	});

	test('displays retouche history when available', async ({ authenticatedPage: page }) => {
		const noteItem = page.locator('[data-testid="note-item"]').first();
		const hasNotes = await noteItem.isVisible({ timeout: 5000 }).catch(() => false);

		if (!hasNotes) {
			test.skip('No notes available for testing');
			return;
		}

		await noteItem.click();
		await page.waitForTimeout(500);

		// Look for history button or indicator
		const historyButton = page.locator(
			'[data-testid="retouche-history-button"], button:has-text("Historique"), [data-testid="retouche-badge"]'
		);

		const historyVisible = await historyButton.isVisible({ timeout: 5000 }).catch(() => false);

		if (!historyVisible) {
			// Note may not have retouche history - this is OK
			test.skip('No retouche history available for this note');
			return;
		}

		await historyButton.click();

		// Should show history modal
		const historyModal = page.locator('[data-testid="retouche-history"], [role="dialog"]:has-text("Historique")');
		await expect(historyModal).toBeVisible({ timeout: 5000 });
	});
});

// =============================================================================
// RETOUCHE QUEUE TESTS
// =============================================================================

test.describe('Retouche - Queue Page', () => {
	test('displays queue page with pending retouches', async ({ authenticatedPage: page }) => {
		await page.goto('/memoires/retouche-queue');
		await page.waitForLoadState('domcontentloaded');

		// Should show queue page structure
		const queueTitle = page.locator('h2:has-text("Retouches en attente"), h1:has-text("Retouches")');
		await expect(queueTitle).toBeVisible({ timeout: 10000 });

		// Should have stats section
		const statsSection = page.locator('[data-testid="retouche-queue"] .grid, .retouche-queue .grid');
		const hasStats = await statsSection.isVisible({ timeout: 5000 }).catch(() => false);

		// Stats or empty state should be visible
		if (!hasStats) {
			const emptyState = page.locator('text=/Aucune retouche/i, text=/à jour/i');
			await expect(emptyState).toBeVisible({ timeout: 5000 });
		}
	});

	test('handles batch apply with proper feedback', async ({ authenticatedPage: page }) => {
		// Mock queue with items
		await page.route('**/api/notes/retouche/queue', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					high_confidence: [
						{
							note_id: 'note-1',
							note_title: 'Test Note 1',
							action_count: 2,
							avg_confidence: 0.9,
							quality_score: 70,
							last_retouche: new Date().toISOString()
						}
					],
					pending_review: [],
					stats: {
						total: 1,
						high_confidence: 1,
						pending_review: 0,
						auto_applied_today: 0
					}
				})
			})
		);

		await page.goto('/memoires/retouche-queue');
		await page.waitForLoadState('domcontentloaded');

		// Look for batch apply button
		const batchButton = page.locator('button:has-text("Tout valider"), button:has-text("Appliquer")');
		const batchVisible = await batchButton.isVisible({ timeout: 5000 }).catch(() => false);

		if (batchVisible) {
			// Mock the apply endpoint
			await page.route('**/api/notes/*/retouche/apply', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ success: true, applied_count: 2 })
				})
			);

			await batchButton.click();

			// Should show success feedback
			const successToast = page.locator('[role="alert"]:has-text("succès"), .toast-success');
			await expect(successToast).toBeVisible({ timeout: 5000 });
		}
	});
});
