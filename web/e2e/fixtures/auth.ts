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
  authenticatedPage: async ({ page, context }, use) => {
    // Clear local storage to ensure clean state
    await context.clearCookies();
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Navigate to login page
    await page.goto('/login', { waitUntil: 'domcontentloaded' });

    // Wait for either the PIN input OR backend unavailable message
    // This handles both normal and error states
    const pinInput = page.locator('[data-testid="pin-input"]');
    const backendUnavailable = page.locator('[data-testid="backend-unavailable"]');

    // Wait for one of these to appear (increased timeout for slow initialization)
    await Promise.race([
      pinInput.waitFor({ state: 'visible', timeout: 30000 }),
      backendUnavailable.waitFor({ state: 'visible', timeout: 30000 }),
    ]);

    // If backend is unavailable, skip the test
    if (await backendUnavailable.isVisible()) {
      throw new Error(
        'Backend is unavailable. Please start the server with: ./scripts/dev.sh'
      );
    }

    // Enter PIN (default test PIN: 1234)
    const testPin = process.env.TEST_PIN || '1234';

    // Fill the PIN input directly (works on all screen sizes)
    await page.fill('[data-testid="pin-input"]', testPin);

    // Wait for submit button to be enabled before clicking
    const submitButton = page.locator('[data-testid="login-submit"]');
    await submitButton.waitFor({ state: 'visible' });

    // Click submit button
    await submitButton.click();

    // Wait for either success (redirect to /) or error message
    // Give more time for login API to respond
    await Promise.race([
      page.waitForURL('/', { timeout: 45000 }),
      page.locator('[data-testid="login-error"]').waitFor({ state: 'visible', timeout: 45000 }),
    ]);

    // Check if we got an error
    if (await page.locator('[data-testid="login-error"]').isVisible()) {
      const errorText = await page.locator('[data-testid="login-error"]').textContent();
      throw new Error(`Login failed: ${errorText}`);
    }

    // Wait for briefing content to be loaded
    await page.waitForSelector('[data-testid="briefing-content"]', {
      timeout: 15000,
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

  // Wait for loading to finish
  await page.waitForFunction(
    () => !document.body.textContent?.includes('Chargement...'),
    { timeout: 15000 }
  );

  await page.waitForSelector('[data-testid="pin-input"]', {
    timeout: 10000,
    state: 'visible',
  });

  // Fill the PIN input directly
  await page.fill('[data-testid="pin-input"]', pin);

  // Click submit button
  await page.click('[data-testid="login-submit"]');

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
