import { test, expect } from '@playwright/test';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Login Page E2E Tests
 *
 * Tests the PIN-based authentication flow.
 */

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display the login page with PIN pad', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/Scapin/);

    // Check PIN pad is visible
    await expect(page.locator(SELECTORS.pinPad)).toBeVisible();

    // Check all digit buttons are present
    for (let i = 0; i <= 9; i++) {
      await expect(page.locator(SELECTORS.pinDigit(String(i)))).toBeVisible();
    }
  });

  test('should show PIN dots as user enters digits', async ({ page }) => {
    // Enter first digit
    await page.click(SELECTORS.pinDigit('1'));
    await expect(page.locator('[data-testid="pin-dot-filled"]')).toHaveCount(1);

    // Enter second digit
    await page.click(SELECTORS.pinDigit('2'));
    await expect(page.locator('[data-testid="pin-dot-filled"]')).toHaveCount(2);
  });

  test('should login successfully with correct PIN', async ({ page }) => {
    // Enter correct PIN (1234)
    await page.click(SELECTORS.pinDigit('1'));
    await page.click(SELECTORS.pinDigit('2'));
    await page.click(SELECTORS.pinDigit('3'));
    await page.click(SELECTORS.pinDigit('4'));

    // Should redirect to home
    await expect(page).toHaveURL('/');
  });

  test('should show error with incorrect PIN', async ({ page }) => {
    // Enter incorrect PIN
    await page.click(SELECTORS.pinDigit('0'));
    await page.click(SELECTORS.pinDigit('0'));
    await page.click(SELECTORS.pinDigit('0'));
    await page.click(SELECTORS.pinDigit('0'));

    // Should show error message
    await expect(page.locator('[data-testid="login-error"]')).toBeVisible();

    // Should stay on login page
    await expect(page).toHaveURL('/login');
  });

  test('should clear PIN on backspace', async ({ page }) => {
    // Enter two digits
    await page.click(SELECTORS.pinDigit('1'));
    await page.click(SELECTORS.pinDigit('2'));
    await expect(page.locator('[data-testid="pin-dot-filled"]')).toHaveCount(2);

    // Click backspace
    await page.click('[data-testid="pin-backspace"]');
    await expect(page.locator('[data-testid="pin-dot-filled"]')).toHaveCount(1);
  });

  test('should support keyboard input for PIN', async ({ page }) => {
    // Focus the PIN input area
    await page.locator(SELECTORS.pinPad).focus();

    // Type PIN using keyboard
    await page.keyboard.type('1234');

    // Should redirect to home
    await expect(page).toHaveURL('/');
  });

  test('should redirect to login when accessing protected page without auth', async ({
    page,
  }) => {
    // Clear any existing auth
    await page.evaluate(() => localStorage.clear());

    // Try to access protected page
    await page.goto('/flux');

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});
