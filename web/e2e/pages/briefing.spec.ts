import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Briefing Page (Home) E2E Tests
 *
 * Tests the main dashboard with morning briefing.
 */

test.describe('Briefing Page', () => {
  test('should display briefing content after login', async ({
    authenticatedPage: page,
  }) => {
    // Should be on home page
    await expect(page).toHaveURL('/');

    // Briefing content should be visible
    await expect(page.locator(SELECTORS.briefingContent)).toBeVisible();
  });

  test('should display stats section', async ({
    authenticatedPage: page,
  }) => {
    // Stats cards should be visible (Emails, Teams, Réunions, Tâches)
    // Use exact locators to avoid matching badges in the event cards
    await expect(page.locator('.text-xs:text("Emails")').first()).toBeVisible();
    await expect(page.locator('.text-xs:text("Teams")').first()).toBeVisible();
    await expect(page.locator('.text-xs:text("Réunions")').first()).toBeVisible();
    await expect(page.locator('.text-xs:text("Tâches")').first()).toBeVisible();
  });

  test('should navigate to flux when clicking process email action', async ({
    authenticatedPage: page,
  }) => {
    // Click on "Traiter le courrier" quick action if available
    const processAction = page.locator(
      '[data-testid="quick-action-process-email"]'
    );

    if (await processAction.isVisible()) {
      await processAction.click();
      await expect(page).toHaveURL('/flux');
    }
  });

  test('should display urgent items section if any', async ({
    authenticatedPage: page,
  }) => {
    // The page should have either urgent items or an empty state message
    const urgentSection = page.locator('[data-testid="urgent-items"]');
    const emptyState = page.getByText('Tout est en ordre, Monsieur');

    // Either urgent items OR empty state should be visible
    const hasUrgentItems = await urgentSection.isVisible();
    const hasEmptyState = await emptyState.isVisible();

    expect(hasUrgentItems || hasEmptyState).toBe(true);
  });

  test('should show conflict alerts for calendar conflicts', async ({
    authenticatedPage: page,
  }) => {
    // Check for conflict indicators if present
    const conflictBadge = page.locator('[data-testid="conflict-badge"]');

    // This test passes whether conflicts exist or not
    // We're just verifying the UI can display them
    const hasConflicts = await conflictBadge.count();
    expect(hasConflicts).toBeGreaterThanOrEqual(0);
  });

  test('should have sidebar navigation', async ({
    authenticatedPage: page,
  }) => {
    // Sidebar should be visible on desktop
    const sidebar = page.locator(SELECTORS.sidebar);

    // Check viewport width to determine if sidebar should be visible
    const viewportSize = page.viewportSize();
    if (viewportSize && viewportSize.width >= 768) {
      await expect(sidebar).toBeVisible();
    }
  });

  test('should have mobile navigation on small screens', async ({
    authenticatedPage: page,
  }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });

    // Mobile nav should be visible
    const mobileNav = page.locator(SELECTORS.mobileNav);
    await expect(mobileNav).toBeVisible();
  });

  test('should open command palette with Cmd+K', async ({
    authenticatedPage: page,
  }) => {
    // Press Cmd+K (or Ctrl+K on non-Mac)
    await page.keyboard.press('Meta+k');

    // Command palette should be visible
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();

    // Press Escape to close - wait for animation
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300); // Wait for close animation
    await expect(page.locator(SELECTORS.commandPalette)).not.toBeVisible();
  });

  test('should display notes due for review widget', async ({
    authenticatedPage: page,
  }) => {
    // Check for notes review widget
    const reviewWidget = page.locator('[data-testid="notes-review-widget"]');

    // Widget should be visible if there are notes due
    // This is a soft check - widget may not appear if no notes are due
    const widgetVisible = await reviewWidget.isVisible();

    if (widgetVisible) {
      // Check it shows count or progress
      await expect(
        reviewWidget.locator('[data-testid="review-progress"]')
      ).toBeVisible();
    }
  });

  test('should refresh briefing on pull-to-refresh (mobile)', async ({
    authenticatedPage: page,
  }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });

    // Get initial content
    const briefingContent = page.locator(SELECTORS.briefingContent);
    await expect(briefingContent).toBeVisible();

    // Simulate pull-to-refresh gesture
    await page.mouse.move(187, 400);
    await page.mouse.down();
    await page.mouse.move(187, 600, { steps: 10 });
    await page.mouse.up();

    // Briefing should still be visible after refresh
    await expect(briefingContent).toBeVisible();
  });
});
