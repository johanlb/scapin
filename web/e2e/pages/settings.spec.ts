import { test, expect } from '../fixtures/auth';

/**
 * Settings Page E2E Tests
 *
 * Tests basic settings page functionality.
 */

test.describe('Settings Page', () => {
  test('should load settings page', async ({ authenticatedPage: page }) => {
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/settings', { timeout: 45000 });
  });

  test('should display settings content', async ({ authenticatedPage: page }) => {
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/settings', { timeout: 45000 });

    await page.waitForTimeout(2000);

    const body = page.locator('body');
    const hasContent = await body.textContent();
    expect(hasContent?.length).toBeGreaterThan(0);
  });
});
