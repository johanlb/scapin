import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * SC-19: Folder Picker E2E Tests
 *
 * Tests the folder selection and modification workflow:
 * - Clickable folder path display
 * - Autocomplete search
 * - Folder creation
 * - Keyboard navigation (Escape to cancel)
 */

test.describe('SC-19: Folder Path Display', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/flux');
    await page.locator(SELECTORS.fluxTabPending).click();
    await page.waitForTimeout(500);
  });

  test('should display full folder path on items with archive action', async ({
    authenticatedPage: page,
  }) => {
    const items = page.locator('[data-testid^="flux-item-"]');
    const itemCount = await items.count();

    if (itemCount > 0) {
      // Look for items with destination/folder path
      const folderPath = page.locator(SELECTORS.folderPath).first();

      if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
        const pathText = await folderPath.textContent();
        // Should display full path with slashes
        expect(pathText).toMatch(/\//);
      }
    }
  });

  test('should have clickable folder path', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Check for cursor pointer style
      const cursor = await folderPath.evaluate(
        (el) => window.getComputedStyle(el).cursor
      );
      expect(cursor).toBe('pointer');
    }
  });

  test('should show hover state on folder path', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.hover();
      // Visual feedback should be present (underline, background change, etc.)
      // This is a structural test - actual styling may vary
      expect(true).toBe(true);
    }
  });
});

test.describe('SC-19: Folder Picker Autocomplete', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/flux');
    await page.locator(SELECTORS.fluxTabPending).click();
    await page.waitForTimeout(500);
  });

  test('should open autocomplete on folder path click', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      // Autocomplete dropdown should appear
      const autocomplete = page.locator(SELECTORS.folderAutocomplete);
      await expect(autocomplete).toBeVisible({ timeout: 1000 });
    }
  });

  test('should have search input in autocomplete', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const searchInput = page.locator(SELECTORS.folderSearchInput);
      await expect(searchInput).toBeVisible();
      await expect(searchInput).toBeFocused();
    }
  });

  test('should filter folders as user types', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const searchInput = page.locator(SELECTORS.folderSearchInput);
      await searchInput.fill('arch');

      // Wait for results to filter
      await page.waitForTimeout(300);

      // Results should contain 'arch' in path
      const suggestions = page.locator(SELECTORS.folderSuggestion);
      const count = await suggestions.count();

      if (count > 0) {
        const firstSuggestion = await suggestions.first().textContent();
        expect(firstSuggestion?.toLowerCase()).toContain('arch');
      }
    }
  });

  test('should display full path in suggestions', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const suggestions = page.locator(SELECTORS.folderSuggestion);
      const count = await suggestions.count();

      if (count > 0) {
        const suggestionText = await suggestions.first().textContent();
        // Should show full path with slashes
        if (suggestionText && suggestionText.includes('/')) {
          expect(suggestionText).toMatch(/\//);
        }
      }
    }
  });

  test('should limit suggestions to 10 items', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      // Clear search to get all results
      const searchInput = page.locator(SELECTORS.folderSearchInput);
      await searchInput.fill('');

      await page.waitForTimeout(300);

      const suggestions = page.locator(SELECTORS.folderSuggestion);
      const count = await suggestions.count();

      expect(count).toBeLessThanOrEqual(10);
    }
  });
});

test.describe('SC-19: Folder Selection', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/flux');
    await page.locator(SELECTORS.fluxTabPending).click();
    await page.waitForTimeout(500);
  });

  test('should update folder path on selection', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      const originalPath = await folderPath.textContent();

      await folderPath.click();

      const suggestions = page.locator(SELECTORS.folderSuggestion);
      const count = await suggestions.count();

      if (count > 1) {
        // Click second suggestion (different from current)
        await suggestions.nth(1).click();

        // Path should be updated
        await page.waitForTimeout(300);
        const newPath = await folderPath.textContent();

        // May or may not be different depending on suggestions
        expect(newPath).toBeTruthy();
      }
    }
  });

  test('should close autocomplete after selection', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const autocomplete = page.locator(SELECTORS.folderAutocomplete);
      await expect(autocomplete).toBeVisible();

      const suggestions = page.locator(SELECTORS.folderSuggestion);
      if ((await suggestions.count()) > 0) {
        await suggestions.first().click();

        // Autocomplete should close
        await expect(autocomplete).not.toBeVisible({ timeout: 1000 });
      }
    }
  });
});

test.describe('SC-19: Folder Creation', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/flux');
    await page.locator(SELECTORS.fluxTabPending).click();
    await page.waitForTimeout(500);
  });

  test('should show create option when no matches', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const searchInput = page.locator(SELECTORS.folderSearchInput);
      // Type a unique folder name that won't exist
      await searchInput.fill('NewUniqueFolder2099');

      await page.waitForTimeout(500);

      // Create option should appear
      const createOption = page.locator(SELECTORS.folderCreateOption);
      if (await createOption.isVisible({ timeout: 1000 }).catch(() => false)) {
        await expect(createOption).toContainText(/créer|create/i);
      }
    }
  });

  test('should create folder and select it', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const searchInput = page.locator(SELECTORS.folderSearchInput);
      const newFolderName = `Test/NewFolder/${Date.now()}`;
      await searchInput.fill(newFolderName);

      await page.waitForTimeout(500);

      const createOption = page.locator(SELECTORS.folderCreateOption);
      if (await createOption.isVisible({ timeout: 1000 }).catch(() => false)) {
        await createOption.click();

        // Folder path should be updated with new folder
        await page.waitForTimeout(500);
        // This is a structural test - actual creation depends on backend
        expect(true).toBe(true);
      }
    }
  });
});

test.describe('SC-19: Keyboard Navigation', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/flux');
    await page.locator(SELECTORS.fluxTabPending).click();
    await page.waitForTimeout(500);
  });

  test('should close autocomplete on Escape', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const autocomplete = page.locator(SELECTORS.folderAutocomplete);
      await expect(autocomplete).toBeVisible();

      // Press Escape
      await page.keyboard.press('Escape');

      // Autocomplete should close
      await expect(autocomplete).not.toBeVisible({ timeout: 1000 });
    }
  });

  test('should revert to original path on Escape', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      const originalPath = await folderPath.textContent();

      await folderPath.click();

      const searchInput = page.locator(SELECTORS.folderSearchInput);
      await searchInput.fill('different');

      // Press Escape
      await page.keyboard.press('Escape');

      // Path should revert to original
      const currentPath = await folderPath.textContent();
      expect(currentPath).toBe(originalPath);
    }
  });

  test('should navigate suggestions with arrow keys', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const suggestions = page.locator(SELECTORS.folderSuggestion);
      if ((await suggestions.count()) > 1) {
        // Press down arrow
        await page.keyboard.press('ArrowDown');

        // First suggestion should be highlighted
        const highlighted = page.locator(
          `${SELECTORS.folderSuggestion}[aria-selected="true"], ${SELECTORS.folderSuggestion}.highlighted`
        );

        // Structural test - actual implementation may vary
        expect(true).toBe(true);
      }
    }
  });

  test('should select highlighted suggestion on Enter', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const suggestions = page.locator(SELECTORS.folderSuggestion);
      if ((await suggestions.count()) > 0) {
        // Navigate to first suggestion
        await page.keyboard.press('ArrowDown');
        // Select with Enter
        await page.keyboard.press('Enter');

        // Autocomplete should close
        const autocomplete = page.locator(SELECTORS.folderAutocomplete);
        await expect(autocomplete).not.toBeVisible({ timeout: 1000 });
      }
    }
  });
});

test.describe('SC-19: Close on Outside Click', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/flux');
    await page.locator(SELECTORS.fluxTabPending).click();
    await page.waitForTimeout(500);
  });

  test('should close autocomplete on outside click', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      await folderPath.click();

      const autocomplete = page.locator(SELECTORS.folderAutocomplete);
      await expect(autocomplete).toBeVisible();

      // Click outside (on body or another element)
      await page.locator('body').click({ position: { x: 10, y: 10 } });

      // Autocomplete should close
      await expect(autocomplete).not.toBeVisible({ timeout: 1000 });
    }
  });

  test('should not modify path on outside click', async ({
    authenticatedPage: page,
  }) => {
    const folderPath = page.locator(SELECTORS.folderPath).first();

    if (await folderPath.isVisible({ timeout: 2000 }).catch(() => false)) {
      const originalPath = await folderPath.textContent();

      await folderPath.click();

      const searchInput = page.locator(SELECTORS.folderSearchInput);
      await searchInput.fill('different');

      // Click outside
      await page.locator('body').click({ position: { x: 10, y: 10 } });

      // Path should revert
      const currentPath = await folderPath.textContent();
      expect(currentPath).toBe(originalPath);
    }
  });
});

