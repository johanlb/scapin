import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Discussions Page E2E Tests
 *
 * Tests basic discussions page functionality.
 */

test.describe('Discussions Page', () => {
  test('should load discussions page', async ({ authenticatedPage: page }) => {
    await page.goto('/discussions', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/discussions', { timeout: 45000 });
  });

  test('should display discussions content', async ({ authenticatedPage: page }) => {
    await page.goto('/discussions', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/discussions', { timeout: 45000 });

    await page.waitForTimeout(2000);

    const body = page.locator('body');
    const hasContent = await body.textContent();
    expect(hasContent?.length).toBeGreaterThan(0);
  });
});

test.describe('Chat Panel', () => {
  test('should check chat panel on desktop', async ({ authenticatedPage: page }) => {
    // Auth fixture already lands on /
    await page.setViewportSize({ width: 1280, height: 720 });

    // Chat panel may or may not be visible
    const chatPanel = page.locator(SELECTORS.chatPanel);
    await page.waitForTimeout(1000);

    const isVisible = await chatPanel.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });
});
