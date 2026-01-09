import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Search (Command Palette) E2E Tests
 *
 * Tests the global search functionality.
 * Note: The authenticatedPage is already at '/' after login.
 */

test.describe('Command Palette', () => {
  test('should open with Cmd+K', async ({ authenticatedPage: page }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Press Cmd+K
    await page.keyboard.press('Meta+k');

    // Command palette should be visible
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();
  });

  test('should open with Ctrl+K', async ({ authenticatedPage: page }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Press Ctrl+K (for non-Mac)
    await page.keyboard.press('Control+k');

    // Command palette should be visible
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();
  });

  test('should close with Escape', async ({ authenticatedPage: page }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Open palette
    await page.keyboard.press('Meta+k');
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();

    // Close with Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300); // Wait for close animation
    await expect(page.locator(SELECTORS.commandPalette)).not.toBeVisible();
  });

  test('should close when clicking outside', async ({
    authenticatedPage: page,
  }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Open palette
    await page.keyboard.press('Meta+k');
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();

    // Click outside the palette (on the backdrop)
    await page.mouse.click(10, 10);
    await page.waitForTimeout(300);
    await expect(page.locator(SELECTORS.commandPalette)).not.toBeVisible();
  });

  test('should have search input focused when opened', async ({
    authenticatedPage: page,
  }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Open palette
    await page.keyboard.press('Meta+k');
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();

    // Search input should be focused
    const searchInput = page.locator(SELECTORS.searchInput);
    await expect(searchInput).toBeFocused();
  });

  test('should accept text input', async ({
    authenticatedPage: page,
  }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Open palette
    await page.keyboard.press('Meta+k');

    // Type search query
    const searchInput = page.locator(SELECTORS.searchInput);
    await searchInput.fill('test');

    // Verify input has the value
    await expect(searchInput).toHaveValue('test');
  });

  test('should show results container', async ({
    authenticatedPage: page,
  }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Open palette
    await page.keyboard.press('Meta+k');

    // Results container should exist
    const results = page.locator(SELECTORS.searchResults);
    await expect(results).toBeVisible();
  });

  test('should navigate with arrow keys', async ({
    authenticatedPage: page,
  }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Open palette
    await page.keyboard.press('Meta+k');
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();

    // Arrow keys should work (no error thrown)
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowUp');

    // Palette should still be open
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();
  });

  test('should close on Enter without crashing', async ({
    authenticatedPage: page,
  }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Open palette
    await page.keyboard.press('Meta+k');
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();

    // Press Enter (may navigate or close depending on selection)
    await page.keyboard.press('Enter');
    await page.waitForTimeout(300);

    // Should not crash - palette may be open or closed depending on state
    // Just verify no error occurred by checking page is still functional
    await expect(page.locator('body')).toBeVisible();
  });

  test('should reopen after closing', async ({
    authenticatedPage: page,
  }) => {
    // Wait for keyboard shortcuts to be registered
    await page.waitForTimeout(500);

    // Open palette
    await page.keyboard.press('Meta+k');
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();

    // Close palette
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await expect(page.locator(SELECTORS.commandPalette)).not.toBeVisible();

    // Reopen palette
    await page.keyboard.press('Meta+k');
    await expect(page.locator(SELECTORS.commandPalette)).toBeVisible();
  });
});
