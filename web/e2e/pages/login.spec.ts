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
    // Clear any existing auth
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.goto('/login');
  });

  test('should display the login page', async ({ page }) => {
    // Wait for loading to finish
    await page.waitForTimeout(1000);

    // Check page title
    await expect(page).toHaveTitle(/Scapin/);

    // Check PIN input is visible
    await expect(page.locator(SELECTORS.pinInput)).toBeVisible();
  });

  test('should have submit button', async ({ page }) => {
    // Wait for loading to finish
    await page.waitForTimeout(1000);

    // Submit button should exist
    await expect(page.locator(SELECTORS.loginSubmit)).toBeVisible();
  });

  test('should login successfully with correct PIN', async ({ page }) => {
    // Wait for loading to finish
    await page.waitForTimeout(1000);

    // Enter correct PIN (1234)
    await page.fill(SELECTORS.pinInput, '1234');

    // Click submit
    await page.click(SELECTORS.loginSubmit);

    // Should redirect to home (with increased timeout for API)
    await expect(page).toHaveURL('/', { timeout: 30000 });
  });

  test('should show error with incorrect PIN', async ({ page }) => {
    // Wait for loading to finish
    await page.waitForTimeout(1000);

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
    await page.goto('/flux');

    // Wait for redirect
    await page.waitForTimeout(2000);

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});
