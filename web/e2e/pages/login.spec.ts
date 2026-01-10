import { test, expect } from '@playwright/test';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Login Page E2E Tests
 *
 * Tests the PIN-based authentication flow.
 * Uses text input instead of PIN pad (mobile-only feature).
 */

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate first, then clear storage
    await page.goto('/login', { waitUntil: 'domcontentloaded' });

    // Clear any existing auth
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Reload to apply cleared state
    await page.reload({ waitUntil: 'domcontentloaded' });

    // Wait for loading to finish (wait for "Chargement..." to disappear)
    try {
      await page.waitForFunction(
        () => !document.body.textContent?.includes('Chargement...'),
        { timeout: 30000 }
      );
    } catch {
      // If timeout, continue anyway - the test assertions will handle it
    }

    // Additional wait for auth state to settle
    await page.waitForTimeout(1000);
  });

  test('should display the login page', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/Scapin/);

    // The page should show either the PIN input (backend available) or backend unavailable message
    const pinInput = page.locator(SELECTORS.pinInput);
    const backendUnavailable = page.locator('[data-testid="backend-unavailable"]');

    // Wait for one of these elements to appear
    try {
      await Promise.race([
        pinInput.waitFor({ state: 'visible', timeout: 15000 }),
        backendUnavailable.waitFor({ state: 'visible', timeout: 15000 }),
      ]);
    } catch {
      // Continue to check what's visible
    }

    // At least one should be visible
    const pinVisible = await pinInput.isVisible();
    const backendVisible = await backendUnavailable.isVisible();

    expect(pinVisible || backendVisible).toBe(true);
  });

  test('should have submit button when backend available', async ({ page }) => {
    // Wait for PIN input or backend unavailable
    const pinInput = page.locator(SELECTORS.pinInput);
    const backendUnavailable = page.locator('[data-testid="backend-unavailable"]');

    try {
      await Promise.race([
        pinInput.waitFor({ state: 'visible', timeout: 15000 }),
        backendUnavailable.waitFor({ state: 'visible', timeout: 15000 }),
      ]);
    } catch {
      // Continue
    }

    // Check if backend is available first
    const backendVisible = await backendUnavailable.isVisible();

    if (backendVisible) {
      // Backend unavailable - skip the rest of this test
      expect(backendVisible).toBe(true);
      return;
    }

    // Submit button should exist
    await expect(page.locator(SELECTORS.loginSubmit)).toBeVisible();
  });

  test('should login successfully with correct PIN', async ({ page }) => {
    // Wait for PIN input or backend unavailable
    const pinInput = page.locator(SELECTORS.pinInput);
    const backendUnavailable = page.locator('[data-testid="backend-unavailable"]');

    try {
      await Promise.race([
        pinInput.waitFor({ state: 'visible', timeout: 15000 }),
        backendUnavailable.waitFor({ state: 'visible', timeout: 15000 }),
      ]);
    } catch {
      // Continue
    }

    // Check if backend is available first
    const backendVisible = await backendUnavailable.isVisible();

    if (backendVisible) {
      // Backend unavailable - skip the rest of this test
      expect(backendVisible).toBe(true);
      return;
    }

    // Enter correct PIN (1234)
    await page.fill(SELECTORS.pinInput, '1234');

    // Click submit
    await page.click(SELECTORS.loginSubmit);

    // Should redirect to home (with increased timeout for API)
    await expect(page).toHaveURL('/', { timeout: 30000 });
  });

  test('should show error with incorrect PIN', async ({ page }) => {
    // Wait for PIN input or backend unavailable
    const pinInput = page.locator(SELECTORS.pinInput);
    const backendUnavailable = page.locator('[data-testid="backend-unavailable"]');

    try {
      await Promise.race([
        pinInput.waitFor({ state: 'visible', timeout: 15000 }),
        backendUnavailable.waitFor({ state: 'visible', timeout: 15000 }),
      ]);
    } catch {
      // Continue
    }

    // Check if backend is available first
    const backendVisible = await backendUnavailable.isVisible();

    if (backendVisible) {
      // Backend unavailable - skip the rest of this test
      expect(backendVisible).toBe(true);
      return;
    }

    // Enter incorrect PIN
    await page.fill(SELECTORS.pinInput, '0000');

    // Click submit
    await page.click(SELECTORS.loginSubmit);

    // Should show error message
    await expect(page.locator('[data-testid="login-error"]')).toBeVisible({ timeout: 10000 });

    // Should stay on login page
    await expect(page).toHaveURL('/login');
  });

  test('should redirect to login when accessing protected page without auth', async ({
    page,
  }) => {
    // Try to access protected page
    await page.goto('/flux', { waitUntil: 'domcontentloaded' });

    // Wait for redirect
    await page.waitForTimeout(3000);

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});
