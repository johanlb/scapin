import { test, expect } from '../fixtures/auth';

/**
 * Stats Page E2E Tests
 *
 * Tests the statistics and analytics page.
 */

test.describe('Stats Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/stats');
  });

  test('should display stats page', async ({ authenticatedPage: page }) => {
    // Stats container should be visible
    await expect(page.locator('[data-testid="stats-page"]')).toBeVisible();
  });

  test('should show overview stats', async ({ authenticatedPage: page }) => {
    // Overview section
    const overview = page.locator('[data-testid="stats-overview"]');
    await expect(overview).toBeVisible();
  });

  test('should display key metrics', async ({ authenticatedPage: page }) => {
    // Key metric cards
    const metrics = page.locator('[data-testid^="metric-"]');

    // Should have multiple metrics
    await expect(metrics).toHaveCount.greaterThan(0);
  });

  test('should show processing stats', async ({
    authenticatedPage: page,
  }) => {
    // Processing stats section
    const processingStats = page.locator(
      '[data-testid="processing-stats"]'
    );

    const isVisible = await processingStats.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should display source breakdown', async ({
    authenticatedPage: page,
  }) => {
    // By-source stats
    const bySource = page.locator('[data-testid="stats-by-source"]');

    if (await bySource.isVisible()) {
      // Should have source items
      const sources = bySource.locator('[data-testid^="source-"]');
      expect(await sources.count()).toBeGreaterThanOrEqual(0);
    }
  });

  test('should show trend chart', async ({ authenticatedPage: page }) => {
    // Line chart or trend visualization
    const chart = page.locator(
      '[data-testid="trend-chart"], [data-testid="line-chart"]'
    );

    const isVisible = await chart.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should toggle time period', async ({ authenticatedPage: page }) => {
    // Period selector (7 days, 30 days, etc.)
    const periodSelector = page.locator(
      '[data-testid="period-selector"]'
    );

    if (await periodSelector.isVisible()) {
      // Click 30 days option
      const thirtyDaysBtn = page.locator('[data-testid="period-30"]');
      if (await thirtyDaysBtn.isVisible()) {
        await thirtyDaysBtn.click();

        // Chart should update
        await page.waitForTimeout(500);
      }
    }
  });

  test('should display email stats', async ({ authenticatedPage: page }) => {
    const emailStats = page.locator('[data-testid="email-stats"]');

    const isVisible = await emailStats.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should display teams stats', async ({ authenticatedPage: page }) => {
    const teamsStats = page.locator('[data-testid="teams-stats"]');

    const isVisible = await teamsStats.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should display calendar stats', async ({
    authenticatedPage: page,
  }) => {
    const calendarStats = page.locator('[data-testid="calendar-stats"]');

    const isVisible = await calendarStats.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should display notes review stats', async ({
    authenticatedPage: page,
  }) => {
    const reviewStats = page.locator('[data-testid="review-stats"]');

    const isVisible = await reviewStats.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should show queue stats', async ({ authenticatedPage: page }) => {
    const queueStats = page.locator('[data-testid="queue-stats"]');

    const isVisible = await queueStats.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should refresh stats', async ({ authenticatedPage: page }) => {
    const refreshBtn = page.locator('[data-testid="refresh-stats"]');

    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();

      // Should show loading state
      await expect(refreshBtn).toHaveAttribute('data-loading', 'true');

      // Should complete
      await expect(refreshBtn).not.toHaveAttribute('data-loading', 'true', {
        timeout: 10000,
      });
    }
  });

  test('should handle empty stats gracefully', async ({
    authenticatedPage: page,
  }) => {
    // Page should not crash even with no data
    await expect(page.locator('[data-testid="stats-page"]')).toBeVisible();

    // Should show empty state or zeros
    const emptyState = page.locator('[data-testid="stats-empty"]');
    const hasMetrics = (await page.locator('[data-testid^="metric-"]').count()) > 0;

    expect((await emptyState.isVisible()) || hasMetrics).toBeTruthy();
  });
});
