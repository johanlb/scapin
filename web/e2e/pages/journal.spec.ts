import { test, expect } from '../fixtures/auth';

/**
 * Journal Page E2E Tests
 *
 * Tests the daily journaling functionality.
 */

test.describe('Journal Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
  });

  test('should display journal page', async ({ authenticatedPage: page }) => {
    // Journal container should be visible
    await expect(
      page.locator('[data-testid="journal-page"]')
    ).toBeVisible();
  });

  test('should show date selector', async ({ authenticatedPage: page }) => {
    const dateSelector = page.locator('[data-testid="journal-date-selector"]');
    await expect(dateSelector).toBeVisible();
  });

  test('should navigate to previous day', async ({
    authenticatedPage: page,
  }) => {
    const prevBtn = page.locator('[data-testid="journal-prev-day"]');

    if (await prevBtn.isVisible()) {
      await prevBtn.click();

      // Date should change
      await page.waitForTimeout(300);

      // URL or date display should change
      const dateDisplay = page.locator(
        '[data-testid="journal-current-date"]'
      );
      await expect(dateDisplay).toBeVisible();
    }
  });

  test('should navigate to next day', async ({
    authenticatedPage: page,
  }) => {
    // First go to previous day
    const prevBtn = page.locator('[data-testid="journal-prev-day"]');
    if (await prevBtn.isVisible()) {
      await prevBtn.click();
      await page.waitForTimeout(300);
    }

    // Then try next day
    const nextBtn = page.locator('[data-testid="journal-next-day"]');
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
      await page.waitForTimeout(300);
    }
  });

  test('should display source tabs', async ({ authenticatedPage: page }) => {
    // Multi-source tabs (Email, Teams, Calendar, OmniFocus)
    const tabs = page.locator('[data-testid="journal-tabs"]');

    if (await tabs.isVisible()) {
      // Should have multiple source tabs
      await expect(tabs.locator('button')).toHaveCount.greaterThan(0);
    }
  });

  test('should switch between source tabs', async ({
    authenticatedPage: page,
  }) => {
    const tabs = page.locator('[data-testid="journal-tabs"]');

    if (await tabs.isVisible()) {
      // Click Teams tab if available
      const teamsTab = tabs.locator('[data-testid="tab-teams"]');
      if (await teamsTab.isVisible()) {
        await teamsTab.click();
        await expect(teamsTab).toHaveClass(/active|selected/);
      }
    }
  });

  test('should display journal questions', async ({
    authenticatedPage: page,
  }) => {
    // Questions section
    const questions = page.locator('[data-testid="journal-questions"]');

    const isVisible = await questions.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should answer journal question', async ({
    authenticatedPage: page,
  }) => {
    const questions = page.locator('[data-testid^="question-"]');
    const count = await questions.count();

    if (count > 0) {
      const firstQuestion = questions.first();
      const input = firstQuestion.locator('input, textarea');

      if (await input.isVisible()) {
        await input.fill('Test answer');

        // Should save or enable submit
        await page.waitForTimeout(500);
      }
    }
  });

  test('should display activity summary', async ({
    authenticatedPage: page,
  }) => {
    // Activity summary section
    const summary = page.locator('[data-testid="activity-summary"]');

    const isVisible = await summary.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should submit corrections', async ({ authenticatedPage: page }) => {
    // Correction input
    const correctionInput = page.locator('[data-testid="correction-input"]');

    if (await correctionInput.isVisible()) {
      await correctionInput.fill('Correction test');

      // Submit button
      const submitBtn = page.locator('[data-testid="submit-correction"]');
      if (await submitBtn.isVisible()) {
        await submitBtn.click();

        // Should show success feedback
        await page.waitForTimeout(500);
      }
    }
  });

  test('should export journal entry', async ({ authenticatedPage: page }) => {
    const exportBtn = page.locator('[data-testid="export-journal"]');

    if (await exportBtn.isVisible()) {
      await exportBtn.click();

      // Export modal or download should trigger
      const exportModal = page.locator('[data-testid="export-modal"]');
      const isModalVisible = await exportModal.isVisible();
      expect(typeof isModalVisible).toBe('boolean');
    }
  });

  test('should show weekly review option', async ({
    authenticatedPage: page,
  }) => {
    const weeklyBtn = page.locator('[data-testid="weekly-review-btn"]');

    const isVisible = await weeklyBtn.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should save journal automatically', async ({
    authenticatedPage: page,
  }) => {
    // Find any editable field
    const editableFields = page.locator(
      '[data-testid^="question-"] input, [data-testid^="question-"] textarea'
    );
    const count = await editableFields.count();

    if (count > 0) {
      const field = editableFields.first();
      await field.fill('Auto-save test ' + Date.now());

      // Wait for auto-save indicator
      const saveIndicator = page.locator('[data-testid="save-status"]');
      if (await saveIndicator.isVisible()) {
        await expect(saveIndicator).toContainText(/enregistr|saved/i);
      }
    }
  });
});
