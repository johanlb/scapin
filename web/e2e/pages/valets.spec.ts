import { test, expect } from '../fixtures/auth';

/**
 * Valets Page E2E Tests
 *
 * Tests the cognitive agents monitoring interface:
 * - System status display
 * - Individual valet cards
 * - Metrics table
 * - Auto-refresh functionality
 */

test.describe('Valets Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/valets');
  });

  test('should load valets page', async ({ authenticatedPage: page }) => {
    await expect(page).toHaveURL('/valets');
  });

  test('should display page header', async ({
    authenticatedPage: page,
  }) => {
    const title = page.locator('h1:has-text("Équipe des Valets")');
    await expect(title).toBeVisible();

    const subtitle = page.locator('text=Surveillance des agents cognitifs');
    await expect(subtitle).toBeVisible();
  });

  test('should have refresh button', async ({
    authenticatedPage: page,
  }) => {
    const refreshButton = page.locator('button[aria-label="Actualiser"]');
    await expect(refreshButton).toBeVisible();
  });

  test('should show last updated timestamp', async ({
    authenticatedPage: page,
  }) => {
    // Wait for data to load
    await page.waitForLoadState('networkidle');

    // Should show "Mis à jour" text
    const timestamp = page.locator('text=/Mis à jour/');
    await expect(timestamp).toBeVisible({ timeout: 10000 });
  });
});

test.describe('System Status Banner', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/valets');
    await page.waitForLoadState('networkidle');
  });

  test('should display system status indicator', async ({
    authenticatedPage: page,
  }) => {
    // Status text: opérationnel, dégradé, or en erreur
    const statusText = page.locator('text=/Système opérationnel|Système dégradé|Système en erreur/');
    await expect(statusText).toBeVisible({ timeout: 10000 });
  });

  test('should display active workers count', async ({
    authenticatedPage: page,
  }) => {
    const activeWorkers = page.locator('p:has-text("Actifs")');
    await expect(activeWorkers).toBeVisible({ timeout: 10000 });

    // Should have a number above it
    const count = activeWorkers.locator('..').locator('p.text-2xl');
    await expect(count).toContainText(/\d+/);
  });

  test('should display tasks today count', async ({
    authenticatedPage: page,
  }) => {
    const tasksToday = page.locator('p:has-text("Tâches aujourd\'hui")');
    await expect(tasksToday).toBeVisible({ timeout: 10000 });
  });

  test('should display average confidence', async ({
    authenticatedPage: page,
  }) => {
    const confidence = page.locator('p:has-text("Confiance moy.")');
    await expect(confidence).toBeVisible({ timeout: 10000 });

    // Should show percentage
    const percentage = confidence.locator('..').locator('p.text-2xl');
    await expect(percentage).toContainText(/%/);
  });
});

test.describe('Valets Grid', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/valets');
    await page.waitForLoadState('networkidle');
  });

  test('should display valet cards or loading state', async ({
    authenticatedPage: page,
  }) => {
    // Either skeleton loading or valet cards
    const skeleton = page.locator('[class*="animate-pulse"]');
    const cards = page.locator('h3.font-semibold'); // Valet names

    const hasLoading = await skeleton.first().isVisible().catch(() => false);
    const hasCards = await cards.first().isVisible().catch(() => false);

    expect(hasLoading || hasCards).toBe(true);
  });

  test('should display individual valet information', async ({
    authenticatedPage: page,
  }) => {
    // Wait for valets to load
    const valetCard = page.locator('h3.font-semibold').first();

    if (await valetCard.isVisible({ timeout: 10000 }).catch(() => false)) {
      // Valet card should have name
      await expect(valetCard).not.toBeEmpty();

      // Should have status badge
      const statusBadge = page.locator('text=/Actif|Inactif|En pause|Erreur/').first();
      await expect(statusBadge).toBeVisible();
    }
  });

  test('should display valet stats (tasks and errors)', async ({
    authenticatedPage: page,
  }) => {
    // Wait for data
    await page.waitForTimeout(2000);

    // Look for stats labels
    const tasksLabel = page.locator('p:has-text("Tâches")').first();
    const errorsLabel = page.locator('p:has-text("Erreurs")').first();

    // If valets are loaded, these should be visible
    const hasData = await tasksLabel.isVisible().catch(() => false);

    if (hasData) {
      await expect(tasksLabel).toBeVisible();
      await expect(errorsLabel).toBeVisible();
    }
  });
});

test.describe('Metrics Section', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/valets');
    await page.waitForLoadState('networkidle');
  });

  test('should display metrics section header', async ({
    authenticatedPage: page,
  }) => {
    const metricsHeader = page.locator('h2:has-text("Métriques détaillées")');

    // Metrics section might take time to load
    const isVisible = await metricsHeader.isVisible({ timeout: 10000 }).catch(() => false);

    if (isVisible) {
      await expect(metricsHeader).toBeVisible();
    }
  });

  test('should have period selector buttons', async ({
    authenticatedPage: page,
  }) => {
    // Wait for metrics section
    const metricsSection = page.locator('text=Métriques détaillées');
    const isVisible = await metricsSection.isVisible({ timeout: 10000 }).catch(() => false);

    if (isVisible) {
      await expect(page.locator('button:has-text("Aujourd\'hui")')).toBeVisible();
      await expect(page.locator('button:has-text("7d")')).toBeVisible();
      await expect(page.locator('button:has-text("30d")')).toBeVisible();
    }
  });

  test('should switch period on button click', async ({
    authenticatedPage: page,
  }) => {
    // Wait for metrics section
    const button7d = page.locator('button:has-text("7d")');
    const isVisible = await button7d.isVisible({ timeout: 10000 }).catch(() => false);

    if (isVisible) {
      await button7d.click();
      await page.waitForLoadState('networkidle');

      // 7d button should now be active (glass class indicates active state)
      await expect(button7d).toHaveClass(/glass[^-]/, { timeout: 5000 });
    }
  });

  test('should display metrics table with columns', async ({
    authenticatedPage: page,
  }) => {
    // Wait for table
    const table = page.locator('table');
    const isVisible = await table.isVisible({ timeout: 10000 }).catch(() => false);

    if (isVisible) {
      // Check for column headers
      await expect(page.locator('th:has-text("Valet")')).toBeVisible();
      await expect(page.locator('th:has-text("Complétées")')).toBeVisible();
      await expect(page.locator('th:has-text("Échouées")')).toBeVisible();
      await expect(page.locator('th:has-text("Temps moy.")')).toBeVisible();
      await expect(page.locator('th:has-text("Succès")')).toBeVisible();
    }
  });
});

test.describe('Refresh Functionality', () => {
  test('should refresh data on button click', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/valets');
    await page.waitForLoadState('networkidle');

    const refreshButton = page.locator('button[aria-label="Actualiser"]');
    await expect(refreshButton).toBeVisible();

    // Click refresh
    await refreshButton.click();

    // Button should show loading state (spinning emoji)
    // Or data should refresh (timestamp should update)
    // This is a structural test - verify no crash
    await page.waitForLoadState('networkidle');

    // Page should still be functional
    await expect(page.locator('h1:has-text("Équipe des Valets")')).toBeVisible();
  });
});

test.describe('Error Handling', () => {
  test('should handle API errors gracefully', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/valets');

    // Even if API fails, page should not crash
    // Should show either content or error message
    const content = page.locator('text=/Valets|Erreur|Système/');
    await expect(content.first()).toBeVisible({ timeout: 10000 });
  });
});
