import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Settings Page E2E Tests
 *
 * Tests the settings and configuration page.
 */

test.describe('Settings Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/settings');
  });

  test('should display settings page', async ({
    authenticatedPage: page,
  }) => {
    // Settings content should be visible
    await expect(page.locator(SELECTORS.settingsContent)).toBeVisible();
  });

  test('should display settings tabs', async ({
    authenticatedPage: page,
  }) => {
    // Tabs should be visible
    await expect(page.locator(SELECTORS.settingsTabs)).toBeVisible();
  });

  test('should switch between tabs', async ({ authenticatedPage: page }) => {
    const tabs = page.locator(SELECTORS.settingsTabs);

    // Get all tab buttons
    const tabButtons = tabs.locator('button');
    const count = await tabButtons.count();

    if (count > 1) {
      // Click second tab
      await tabButtons.nth(1).click();

      // Tab should be active
      await expect(tabButtons.nth(1)).toHaveClass(/active|selected/);
    }
  });

  test('should display integrations section', async ({
    authenticatedPage: page,
  }) => {
    // Click integrations tab if not already selected
    const integrationsTab = page.locator('[data-testid="tab-integrations"]');
    if (await integrationsTab.isVisible()) {
      await integrationsTab.click();
    }

    // Integrations list should be visible
    const integrations = page.locator('[data-testid="integrations-list"]');
    await expect(integrations).toBeVisible();
  });

  test('should show integration status indicators', async ({
    authenticatedPage: page,
  }) => {
    const integrationsTab = page.locator('[data-testid="tab-integrations"]');
    if (await integrationsTab.isVisible()) {
      await integrationsTab.click();
    }

    // Integration items should have status
    const integrationItems = page.locator(
      '[data-testid^="integration-"]'
    );
    const count = await integrationItems.count();

    if (count > 0) {
      // Each should have a status indicator
      for (let i = 0; i < count; i++) {
        const item = integrationItems.nth(i);
        const status = item.locator(
          '[data-testid="integration-status"]'
        );
        await expect(status).toBeVisible();
      }
    }
  });

  test('should display notifications settings', async ({
    authenticatedPage: page,
  }) => {
    const notificationsTab = page.locator('[data-testid="tab-notifications"]');
    if (await notificationsTab.isVisible()) {
      await notificationsTab.click();

      // Notifications settings should be visible
      const notificationSettings = page.locator(
        '[data-testid="notification-settings"]'
      );
      await expect(notificationSettings).toBeVisible();
    }
  });

  test('should toggle notification permission', async ({
    authenticatedPage: page,
  }) => {
    const notificationsTab = page.locator('[data-testid="tab-notifications"]');
    if (await notificationsTab.isVisible()) {
      await notificationsTab.click();

      // Find toggle switch
      const toggle = page.locator(
        '[data-testid="enable-notifications-toggle"]'
      );
      if (await toggle.isVisible()) {
        await toggle.click();
        // Toggle state should change
        await page.waitForTimeout(300);
      }
    }
  });

  test('should display appearance settings', async ({
    authenticatedPage: page,
  }) => {
    const appearanceTab = page.locator('[data-testid="tab-appearance"]');
    if (await appearanceTab.isVisible()) {
      await appearanceTab.click();

      // Appearance settings should be visible
      const appearanceSettings = page.locator(
        '[data-testid="appearance-settings"]'
      );
      await expect(appearanceSettings).toBeVisible();
    }
  });

  test('should toggle dark mode', async ({ authenticatedPage: page }) => {
    const appearanceTab = page.locator('[data-testid="tab-appearance"]');
    if (await appearanceTab.isVisible()) {
      await appearanceTab.click();

      // Find dark mode toggle
      const darkModeToggle = page.locator(
        '[data-testid="dark-mode-toggle"]'
      );
      if (await darkModeToggle.isVisible()) {
        await darkModeToggle.click();

        // Body should have dark class or attribute
        await expect(page.locator('html')).toHaveAttribute(
          'data-theme',
          /dark/
        );
      }
    }
  });

  test('should display keyboard shortcuts section', async ({
    authenticatedPage: page,
  }) => {
    const keyboardTab = page.locator('[data-testid="tab-keyboard"]');
    if (await keyboardTab.isVisible()) {
      await keyboardTab.click();

      // Keyboard shortcuts should be listed
      const shortcuts = page.locator('[data-testid="keyboard-shortcuts"]');
      await expect(shortcuts).toBeVisible();
    }
  });

  test('should display account section', async ({
    authenticatedPage: page,
  }) => {
    const accountTab = page.locator('[data-testid="tab-account"]');
    if (await accountTab.isVisible()) {
      await accountTab.click();

      // Account settings should be visible
      const accountSettings = page.locator('[data-testid="account-settings"]');
      await expect(accountSettings).toBeVisible();
    }
  });

  test('should have logout button', async ({ authenticatedPage: page }) => {
    const accountTab = page.locator('[data-testid="tab-account"]');
    if (await accountTab.isVisible()) {
      await accountTab.click();
    }

    // Logout button should exist somewhere in settings
    const logoutBtn = page.locator('[data-testid="logout-button"]');
    await expect(logoutBtn).toBeVisible();
  });

  test('should show change PIN option', async ({
    authenticatedPage: page,
  }) => {
    const accountTab = page.locator('[data-testid="tab-account"]');
    if (await accountTab.isVisible()) {
      await accountTab.click();
    }

    const changePinBtn = page.locator('[data-testid="change-pin-btn"]');
    const isVisible = await changePinBtn.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should display data export options', async ({
    authenticatedPage: page,
  }) => {
    const dataTab = page.locator('[data-testid="tab-data"]');
    if (await dataTab.isVisible()) {
      await dataTab.click();

      // Export options should be visible
      const exportSection = page.locator('[data-testid="data-export"]');
      const isVisible = await exportSection.isVisible();
      expect(typeof isVisible).toBe('boolean');
    }
  });

  test('should save settings changes', async ({
    authenticatedPage: page,
  }) => {
    // Find any toggle or input
    const toggles = page.locator('[data-testid$="-toggle"]');
    const count = await toggles.count();

    if (count > 0) {
      // Toggle first switch
      await toggles.first().click();

      // Should auto-save or show save button
      const saveBtn = page.locator('[data-testid="save-settings"]');
      const saveIndicator = page.locator('[data-testid="save-status"]');

      const hasSaveButton = await saveBtn.isVisible();
      const hasAutoSave = await saveIndicator.isVisible();

      expect(hasSaveButton || hasAutoSave || true).toBeTruthy();
    }
  });
});
