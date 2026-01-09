import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Notes Page E2E Tests
 *
 * Tests the notes page functionality.
 * Simplified tests that work with current UI structure.
 */

test.describe('Notes Page', () => {
  test('should load notes page', async ({ authenticatedPage: page }) => {
    await page.goto('/notes');

    // Page should load without errors
    await expect(page).toHaveURL('/notes');

    // Main content area should be visible
    await expect(page.locator('main')).toBeVisible();
  });

  test('should display page content', async ({ authenticatedPage: page }) => {
    await page.goto('/notes');

    // Wait for page to load
    await page.waitForTimeout(500);

    // Should have some content loaded
    const content = page.locator('main');
    await expect(content).toBeVisible();
  });

  test('should have sidebar navigation on desktop', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes');
    await page.setViewportSize({ width: 1280, height: 720 });

    // Sidebar should be visible
    const sidebar = page.locator(SELECTORS.sidebar);
    await expect(sidebar).toBeVisible();
  });

  test('should have mobile navigation on mobile', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes');
    await page.setViewportSize({ width: 375, height: 812 });

    // Mobile nav should be visible
    const mobileNav = page.locator(SELECTORS.mobileNav);
    await expect(mobileNav).toBeVisible();
  });

  test('should open command palette from notes page', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes');
    await page.waitForTimeout(500);

    // Press Cmd+K
    await page.keyboard.press('Meta+k');

    // Command palette should open
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();

    // Close it
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await expect(page.locator(SELECTORS.commandPalette)).not.toBeVisible();
  });
});

test.describe('Notes Review Page', () => {
  test('should load review page', async ({ authenticatedPage: page }) => {
    await page.goto('/notes/review');

    // Page should load
    await expect(page.locator('main, body')).toBeVisible();
  });
});
