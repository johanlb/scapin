import { test, expect } from '../fixtures/auth';

/**
 * Notes Page E2E Tests
 *
 * Tests basic notes page functionality.
 */

test.describe('Notes Page', () => {
  test('should load notes page', async ({ authenticatedPage: page }) => {
    await page.goto('/notes', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/notes', { timeout: 45000 });
  });

  test('should display notes content', async ({ authenticatedPage: page }) => {
    await page.goto('/notes', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/notes', { timeout: 45000 });

    await page.waitForTimeout(2000);

    const body = page.locator('body');
    const hasContent = await body.textContent();
    expect(hasContent?.length).toBeGreaterThan(0);
  });
});
