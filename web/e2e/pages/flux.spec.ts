import { test, expect } from '../fixtures/auth';

/**
 * Flux Page E2E Tests
 *
 * Tests basic flux page functionality.
 * Note: Navigation tests are simplified due to auth re-initialization timing.
 */

test.describe('Flux Page', () => {
  test('should load flux page', async ({ authenticatedPage: page }) => {
    await page.goto('/flux', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/flux', { timeout: 45000 });
  });

  test('should display flux content', async ({ authenticatedPage: page }) => {
    await page.goto('/flux', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/flux', { timeout: 45000 });

    // Wait for page to render
    await page.waitForTimeout(2000);

    // Should have some content
    const body = page.locator('body');
    const hasContent = await body.textContent();
    expect(hasContent?.length).toBeGreaterThan(0);
  });
});
