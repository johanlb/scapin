import { test as base, Page } from '@playwright/test';

/**
 * Authentication Fixture for Scapin E2E Tests
 *
 * Provides an authenticated page for tests that require login.
 * Uses PIN-based authentication (default: 1234 for test environment).
 */

export interface AuthFixtures {
  authenticatedPage: Page;
}

/**
 * Extended test with authentication fixture
 */
export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Navigate to login page
    await page.goto('/login');

    // Wait for the PIN pad to be visible
    await page.waitForSelector('[data-testid="pin-pad"]', { timeout: 10000 });

    // Enter PIN (default test PIN: 1234)
    const testPin = process.env.TEST_PIN || '1234';
    for (const digit of testPin) {
      await page.click(`[data-testid="pin-${digit}"]`);
      // Small delay between digits for stability
      await page.waitForTimeout(100);
    }

    // Wait for redirect to home page after successful login
    await page.waitForURL('/', { timeout: 10000 });

    // Wait for briefing content to be loaded
    await page.waitForSelector('[data-testid="briefing-content"]', {
      timeout: 10000,
      state: 'visible',
    });

    // Provide the authenticated page to the test
    await use(page);
  },
});

/**
 * Re-export expect for convenience
 */
export { expect } from '@playwright/test';

/**
 * Login helper function for custom login scenarios
 */
export async function login(page: Page, pin: string = '1234'): Promise<void> {
  await page.goto('/login');
  await page.waitForSelector('[data-testid="pin-pad"]');

  for (const digit of pin) {
    await page.click(`[data-testid="pin-${digit}"]`);
    await page.waitForTimeout(100);
  }

  await page.waitForURL('/');
}

/**
 * Logout helper function
 */
export async function logout(page: Page): Promise<void> {
  // Click user menu or logout button
  const logoutButton = page.locator('[data-testid="logout-button"]');
  if (await logoutButton.isVisible()) {
    await logoutButton.click();
  } else {
    // Try sidebar user menu
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-option"]');
  }

  // Wait for redirect to login
  await page.waitForURL('/login');
}
