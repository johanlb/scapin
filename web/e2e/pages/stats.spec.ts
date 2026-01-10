import { test, expect } from '../fixtures/auth';

/**
 * Stats Page E2E Tests
 *
 * Tests basic stats page functionality.
 */

test.describe('Stats Page', () => {
  test('should load stats page', async ({ authenticatedPage: page }) => {
    await page.goto('/stats', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/stats', { timeout: 45000 });
  });

  test('should display stats content', async ({ authenticatedPage: page }) => {
    await page.goto('/stats', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/stats', { timeout: 45000 });

    await page.waitForTimeout(2000);

    const body = page.locator('body');
    const hasContent = await body.textContent();
    expect(hasContent?.length).toBeGreaterThan(0);
  });
});
