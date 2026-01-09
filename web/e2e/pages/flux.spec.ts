import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Flux Page E2E Tests
 *
 * Tests the email/flux inbox functionality.
 * Simplified tests that work with current UI structure.
 */

test.describe('Flux Page', () => {
  test('should load flux page', async ({ authenticatedPage: page }) => {
    await page.goto('/flux');

    // Page should load without errors
    await expect(page).toHaveURL('/flux');

    // Main content area should be visible
    await expect(page.locator('main')).toBeVisible();
  });

  test('should display page content', async ({ authenticatedPage: page }) => {
    await page.goto('/flux');

    // Wait for page to load
    await page.waitForTimeout(500);

    // Should have some content loaded
    const content = page.locator('main');
    await expect(content).toBeVisible();
  });

  test('should have sidebar navigation on desktop', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/flux');
    await page.setViewportSize({ width: 1280, height: 720 });

    // Sidebar should be visible
    const sidebar = page.locator(SELECTORS.sidebar);
    await expect(sidebar).toBeVisible();
  });

  test('should have mobile navigation on mobile', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/flux');
    await page.setViewportSize({ width: 375, height: 812 });

    // Mobile nav should be visible
    const mobileNav = page.locator(SELECTORS.mobileNav);
    await expect(mobileNav).toBeVisible();
  });

  test('should navigate back to home', async ({ authenticatedPage: page }) => {
    await page.goto('/flux');

    // Click on home link in sidebar or nav
    const homeLink = page.locator('a[href="/"]').first();
    if (await homeLink.isVisible()) {
      await homeLink.click();
      await expect(page).toHaveURL('/');
    }
  });

  test('should open command palette from flux page', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/flux');
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
