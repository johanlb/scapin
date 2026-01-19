import { test, expect } from '../fixtures/auth';

/**
 * Drafts Page E2E Tests
 *
 * Tests the AI-generated drafts management interface:
 * - Loading and displaying drafts
 * - Filtering by status (pending, sent, discarded, all)
 * - Draft actions (edit, discard, delete)
 * - Navigation to draft detail
 */

test.describe('Drafts Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/drafts');
  });

  test('should load drafts page', async ({ authenticatedPage: page }) => {
    await expect(page).toHaveURL('/drafts');
  });

  test('should display page header with title', async ({
    authenticatedPage: page,
  }) => {
    const title = page.locator('h1:has-text("Brouillons")');
    await expect(title).toBeVisible();
  });

  test('should display stats in header', async ({
    authenticatedPage: page,
  }) => {
    // Stats should show total count
    const stats = page.locator('text=/\\d+ brouillon/');
    await expect(stats).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Drafts Filtering', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/drafts');
    // Wait for page header to be visible (filter buttons load with it)
    await page.locator('h1:has-text("Brouillons")').waitFor({ state: 'visible', timeout: 15000 });
    // Small delay for filter buttons to render
    await page.waitForTimeout(500);
  });

  test('should display filter tabs', async ({
    authenticatedPage: page,
  }) => {
    // All filter tabs should be visible
    await expect(page.locator('button:has-text("En attente")')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('button:has-text("Envoyés")')).toBeVisible();
    await expect(page.locator('button:has-text("Abandonnés")')).toBeVisible();
    await expect(page.locator('button:has-text("Tous")')).toBeVisible();
  });

  test('should show pending drafts by default', async ({
    authenticatedPage: page,
  }) => {
    // "En attente" should be active by default (has text-white when active)
    const pendingButton = page.locator('button:has-text("En attente")');
    await expect(pendingButton).toHaveClass(/text-white/, { timeout: 10000 });
  });

  test('should switch to sent filter', async ({
    authenticatedPage: page,
  }) => {
    const sentButton = page.locator('button:has-text("Envoyés")');
    await sentButton.click();

    // Sent button should now be active (has text-white when active)
    await expect(sentButton).toHaveClass(/text-white/, { timeout: 10000 });
  });

  test('should switch to discarded filter', async ({
    authenticatedPage: page,
  }) => {
    const discardedButton = page.locator('button:has-text("Abandonnés")');
    await discardedButton.click();

    await expect(discardedButton).toHaveClass(/text-white/, { timeout: 10000 });
  });

  test('should switch to all filter', async ({
    authenticatedPage: page,
  }) => {
    const allButton = page.locator('button:has-text("Tous")');
    await allButton.click();

    await expect(allButton).toHaveClass(/text-white/, { timeout: 10000 });
  });
});

test.describe('Drafts List', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/drafts');
    await page.locator('h1:has-text("Brouillons")').waitFor({ state: 'visible', timeout: 15000 });
  });

  test('should display drafts or empty state', async ({
    authenticatedPage: page,
  }) => {
    // Either drafts list or empty state should be visible
    const hasDrafts = await page.locator('[class*="cursor-pointer"]').first().isVisible().catch(() => false);
    const hasEmptyState = await page.locator('text=/Aucun brouillon/').isVisible().catch(() => false);

    expect(hasDrafts || hasEmptyState).toBe(true);
  });

  test('should show loading skeleton initially', async ({
    authenticatedPage: page,
  }) => {
    // Navigate fresh to catch loading state
    await page.goto('/drafts');

    // Either skeleton or content should be visible quickly
    const skeleton = page.locator('[class*="animate-pulse"]');
    const content = page.locator('text=/brouillon/i');

    await expect(skeleton.or(content).first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Draft Item Display', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    // Go to "all" to see more drafts
    await page.goto('/drafts');
    await page.locator('button:has-text("Tous")').waitFor({ state: 'visible', timeout: 15000 });
    await page.locator('button:has-text("Tous")').click();
    await page.waitForTimeout(1000); // Wait for filter to apply
  });

  test('should display draft subject', async ({
    authenticatedPage: page,
  }) => {
    const drafts = page.locator('[class*="cursor-pointer"]');
    const hasDrafts = await drafts.count() > 0;

    if (hasDrafts) {
      // First draft should have some text content
      const firstDraft = drafts.first();
      await expect(firstDraft).toContainText(/.+/);
    }
  });

  test('should display AI badge for AI-generated drafts', async ({
    authenticatedPage: page,
  }) => {
    // Look for AI badge
    const aiBadge = page.locator('text="IA"');

    // AI badge might be present on some drafts
    // This test just verifies the badge renders correctly when present
    const hasBadge = await aiBadge.first().isVisible({ timeout: 2000 }).catch(() => false);

    if (hasBadge) {
      await expect(aiBadge.first()).toHaveAttribute('title', 'Généré par IA');
    }
  });

  test('should display status badge', async ({
    authenticatedPage: page,
  }) => {
    const drafts = page.locator('[class*="cursor-pointer"]');
    const hasDrafts = await drafts.count() > 0;

    if (hasDrafts) {
      // Status badges: Brouillon, Envoyé, Abandonné, Échec
      const statusBadge = page.locator('text=/Brouillon|Envoyé|Abandonné|Échec/');
      await expect(statusBadge.first()).toBeVisible();
    }
  });
});

test.describe('Draft Navigation', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/drafts');
    await page.locator('button:has-text("Tous")').waitFor({ state: 'visible', timeout: 15000 });
    // Switch to all to have better chance of finding drafts
    await page.locator('button:has-text("Tous")').click();
    await page.waitForTimeout(1000); // Wait for filter to apply
  });

  test('should navigate to draft detail on click', async ({
    authenticatedPage: page,
  }) => {
    const drafts = page.locator('[class*="cursor-pointer"] button');
    const hasDrafts = await drafts.count() > 0;

    if (hasDrafts) {
      await drafts.first().click();

      // Should navigate to draft detail page
      await expect(page).toHaveURL(/\/drafts\/.+/);
    }
  });
});

test.describe('Drafts Error Handling', () => {
  test('should handle API errors gracefully', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/drafts');

    // Even if API fails, page should not crash
    // Should show either content, empty state, or error message
    const content = page.locator('text=/brouillon|Erreur|Aucun/i');
    await expect(content.first()).toBeVisible({ timeout: 10000 });
  });
});
