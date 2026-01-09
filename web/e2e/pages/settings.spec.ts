import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Settings Page E2E Tests
 *
 * Tests the settings page functionality.
 * Simplified tests that work with current UI structure.
 */

test.describe('Settings Page', () => {
  test('should load settings page', async ({ authenticatedPage: page }) => {
    await page.goto('/settings');

    // Page should load without errors
    await expect(page).toHaveURL('/settings');

    // Main content area should be visible
    await expect(page.locator('main')).toBeVisible();
  });

  test('should display page content', async ({ authenticatedPage: page }) => {
    await page.goto('/settings');

    // Wait for page to load
    await page.waitForTimeout(500);

    // Should have some content loaded
    const content = page.locator('main');
    await expect(content).toBeVisible();
  });

  test('should have sidebar navigation on desktop', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/settings');
    await page.setViewportSize({ width: 1280, height: 720 });

    // Sidebar should be visible
    const sidebar = page.locator(SELECTORS.sidebar);
    await expect(sidebar).toBeVisible();
  });

  test('should open command palette from settings page', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/settings');
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
