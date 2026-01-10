import { test, expect } from '../fixtures/auth';

/**
 * Journal Page E2E Tests
 *
 * Tests basic journal page functionality.
 */

test.describe('Journal Page', () => {
  test('should load journal page', async ({ authenticatedPage: page }) => {
    await page.goto('/journal', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/journal', { timeout: 45000 });
  });

  test('should display journal content', async ({ authenticatedPage: page }) => {
    await page.goto('/journal', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/journal', { timeout: 45000 });

    await page.waitForTimeout(2000);

    const body = page.locator('body');
    const hasContent = await body.textContent();
    expect(hasContent?.length).toBeGreaterThan(0);
  });
});
