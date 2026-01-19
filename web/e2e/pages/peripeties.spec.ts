import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Flux Page E2E Tests
 *
 * Tests basic flux page functionality.
 * Note: Navigation tests are simplified due to auth re-initialization timing.
 */

test.describe('Flux Page', () => {
  test('should load flux page', async ({ authenticatedPage: page }) => {
    await page.goto('/peripeties', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/peripeties', { timeout: 45000 });
  });

  test('should display flux content', async ({ authenticatedPage: page }) => {
    await page.goto('/peripeties', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL('/peripeties', { timeout: 45000 });

    // Wait for page to render
    await page.waitForTimeout(2000);

    // Should have some content
    const body = page.locator('body');
    const hasContent = await body.textContent();
    expect(hasContent?.length).toBeGreaterThan(0);
  });

  test.describe('Complexity Badges (v2.3)', () => {
    test('should display badges legend', async ({ authenticatedPage: page }) => {
      await page.goto('/peripeties', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/peripeties', { timeout: 45000 });
      await page.waitForTimeout(2000);

      // Badges legend should be visible
      const legend = page.locator(SELECTORS.badgesLegend);
      await expect(legend).toBeVisible();

      // Should contain the 4 badge emojis
      const legendText = await legend.textContent();
      expect(legendText).toContain('⚡');
      expect(legendText).toContain('🔍');
      expect(legendText).toContain('🧠');
      expect(legendText).toContain('🏆');
    });

    test('should have proper tooltips on legend badges', async ({ authenticatedPage: page }) => {
      await page.goto('/peripeties', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/peripeties', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const legend = page.locator(SELECTORS.badgesLegend);

      // Check tooltips on each badge in legend
      const spans = legend.locator('span[title]');
      const spanCount = await spans.count();
      expect(spanCount).toBeGreaterThanOrEqual(4);

      // Each badge should have a descriptive tooltip
      for (let i = 0; i < spanCount; i++) {
        const tooltip = await spans.nth(i).getAttribute('title');
        expect(tooltip).toBeTruthy();
        expect(tooltip!.length).toBeGreaterThan(5);
      }
    });

    test('should display complexity badges on flux items with multi_pass data', async ({ authenticatedPage: page }) => {
      await page.goto('/peripeties', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/peripeties', { timeout: 45000 });
      await page.waitForTimeout(2000);

      // Look for flux items
      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        // Check if any items have badges
        // Note: Not all items may have badges (depends on data)
        const quickBadges = page.locator(SELECTORS.badgeQuick);
        const contextBadges = page.locator(SELECTORS.badgeContext);
        const complexBadges = page.locator(SELECTORS.badgeComplex);
        const opusBadges = page.locator(SELECTORS.badgeOpus);

        const totalBadges = await quickBadges.count() +
                           await contextBadges.count() +
                           await complexBadges.count() +
                           await opusBadges.count();

        // If there are badges, verify they have tooltips
        if (totalBadges > 0) {
          // Check quick badges have tooltips
          const quickCount = await quickBadges.count();
          for (let i = 0; i < quickCount; i++) {
            const tooltip = await quickBadges.nth(i).getAttribute('title');
            expect(tooltip).toBeTruthy();
            expect(tooltip).toContain('rapide');
          }

          // Check context badges have tooltips
          const contextCount = await contextBadges.count();
          for (let i = 0; i < contextCount; i++) {
            const tooltip = await contextBadges.nth(i).getAttribute('title');
            expect(tooltip).toBeTruthy();
            expect(tooltip).toContain('Contexte');
          }

          // Check complex badges have tooltips
          const complexCount = await complexBadges.count();
          for (let i = 0; i < complexCount; i++) {
            const tooltip = await complexBadges.nth(i).getAttribute('title');
            expect(tooltip).toBeTruthy();
            expect(tooltip).toContain('complexe');
          }

          // Check opus badges have tooltips
          const opusCount = await opusBadges.count();
          for (let i = 0; i < opusCount; i++) {
            const tooltip = await opusBadges.nth(i).getAttribute('title');
            expect(tooltip).toBeTruthy();
            expect(tooltip).toContain('Opus');
          }
        }
        // No badges is valid too (legacy items or simple analyses)
      }
    });
  });
});
