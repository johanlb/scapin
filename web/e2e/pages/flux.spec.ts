import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Flux Page E2E Tests
 *
 * Tests the email/message queue and processing workflow.
 */

test.describe('Flux Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/flux');
  });

  test('should display flux list', async ({ authenticatedPage: page }) => {
    // Flux list should be visible
    await expect(page.locator(SELECTORS.fluxList)).toBeVisible();
  });

  test('should show pending items tab by default', async ({
    authenticatedPage: page,
  }) => {
    // Check that pending tab is active
    const pendingTab = page.locator('[data-testid="flux-tab-pending"]');
    await expect(pendingTab).toHaveClass(/active|selected/);
  });

  test('should switch between tabs', async ({ authenticatedPage: page }) => {
    // Click on approved tab
    await page.click('[data-testid="flux-tab-approved"]');
    await expect(page).toHaveURL(/status=approved/);

    // Click on rejected tab
    await page.click('[data-testid="flux-tab-rejected"]');
    await expect(page).toHaveURL(/status=rejected/);

    // Click back to pending
    await page.click('[data-testid="flux-tab-pending"]');
    await expect(page).toHaveURL(/status=pending/);
  });

  test('should display flux items with action buttons', async ({
    authenticatedPage: page,
  }) => {
    // Wait for items to load
    const fluxList = page.locator(SELECTORS.fluxList);
    await expect(fluxList).toBeVisible();

    // Check if there are any items
    const items = page.locator('[data-testid^="flux-item-"]');
    const itemCount = await items.count();

    if (itemCount > 0) {
      // First item should have action buttons
      const firstItem = items.first();
      await expect(
        firstItem.locator(SELECTORS.approveButton)
      ).toBeVisible();
      await expect(
        firstItem.locator(SELECTORS.rejectButton)
      ).toBeVisible();
    }
  });

  test('should approve an item and show undo toast', async ({
    authenticatedPage: page,
  }) => {
    // Wait for items
    const items = page.locator('[data-testid^="flux-item-"]');
    const itemCount = await items.count();

    if (itemCount > 0) {
      // Click approve on first item
      const approveBtn = items.first().locator(SELECTORS.approveButton);
      await approveBtn.click();

      // Undo toast should appear
      await expect(page.locator(SELECTORS.undoToast)).toBeVisible();
    }
  });

  test('should reject an item', async ({ authenticatedPage: page }) => {
    const items = page.locator('[data-testid^="flux-item-"]');
    const itemCount = await items.count();

    if (itemCount > 0) {
      // Click reject on first item
      const rejectBtn = items.first().locator(SELECTORS.rejectButton);
      await rejectBtn.click();

      // Item should be removed or marked as rejected
      // Undo toast should appear
      await expect(page.locator(SELECTORS.undoToast)).toBeVisible();
    }
  });

  test('should snooze an item', async ({ authenticatedPage: page }) => {
    const items = page.locator('[data-testid^="flux-item-"]');
    const itemCount = await items.count();

    if (itemCount > 0) {
      // Click snooze on first item
      const snoozeBtn = items.first().locator(SELECTORS.snoozeButton);

      if (await snoozeBtn.isVisible()) {
        await snoozeBtn.click();

        // Snooze modal or toast should appear
        await expect(
          page.locator('[data-testid="snooze-modal"], [data-testid^="undo-toast-"]')
        ).toBeVisible();
      }
    }
  });

  test('should navigate to item detail', async ({
    authenticatedPage: page,
  }) => {
    const items = page.locator('[data-testid^="flux-item-"]');
    const itemCount = await items.count();

    if (itemCount > 0) {
      // Click on item to view detail
      await items.first().click();

      // Should navigate to detail page
      await expect(page).toHaveURL(/\/flux\/[^/]+/);
    }
  });

  test('should filter items by source', async ({
    authenticatedPage: page,
  }) => {
    // Check for source filter dropdown
    const sourceFilter = page.locator('[data-testid="source-filter"]');

    if (await sourceFilter.isVisible()) {
      await sourceFilter.click();

      // Select email source
      await page.click('[data-testid="source-filter-email"]');

      // URL should have source param
      await expect(page).toHaveURL(/source=email/);
    }
  });

  test('should support keyboard navigation (j/k)', async ({
    authenticatedPage: page,
  }) => {
    const items = page.locator('[data-testid^="flux-item-"]');
    const itemCount = await items.count();

    if (itemCount > 1) {
      // Press j to move to next item
      await page.keyboard.press('j');

      // Second item should be focused
      const secondItem = items.nth(1);
      await expect(secondItem).toHaveClass(/focused|selected|active/);

      // Press k to move back
      await page.keyboard.press('k');

      // First item should be focused
      const firstItem = items.first();
      await expect(firstItem).toHaveClass(/focused|selected|active/);
    }
  });

  test('should approve with keyboard shortcut (a)', async ({
    authenticatedPage: page,
  }) => {
    const items = page.locator('[data-testid^="flux-item-"]');
    const itemCount = await items.count();

    if (itemCount > 0) {
      // Focus first item
      await items.first().focus();

      // Press 'a' to approve
      await page.keyboard.press('a');

      // Undo toast should appear
      await expect(page.locator(SELECTORS.undoToast)).toBeVisible();
    }
  });

  test('should display virtualized list for many items', async ({
    authenticatedPage: page,
  }) => {
    // Navigate to test performance page with many items
    await page.goto('/flux/test-performance');

    // Virtual list container should exist
    const virtualList = page.locator('[data-testid="virtual-list"]');
    await expect(virtualList).toBeVisible();
  });

  test('should open focus mode', async ({ authenticatedPage: page }) => {
    // Click focus mode button
    const focusBtn = page.locator('[data-testid="focus-mode-btn"]');

    if (await focusBtn.isVisible()) {
      await focusBtn.click();

      // Should navigate to focus page
      await expect(page).toHaveURL(/\/flux\/focus/);
    }
  });
});
