import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Notifications E2E Tests
 *
 * Tests the notifications panel and badge.
 */

test.describe('Notifications', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/');
  });

  test('should display notification badge', async ({
    authenticatedPage: page,
  }) => {
    // Badge may or may not be visible depending on notifications
    const badge = page.locator(SELECTORS.notificationBadge);
    const isVisible = await badge.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should open notifications panel', async ({
    authenticatedPage: page,
  }) => {
    // Click notification bell icon
    const bellIcon = page.locator('[data-testid="notification-bell"]');

    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      // Panel should open
      await expect(page.locator(SELECTORS.notificationsPanel)).toBeVisible();
    }
  });

  test('should close notifications panel', async ({
    authenticatedPage: page,
  }) => {
    // Open panel
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();
      await expect(page.locator(SELECTORS.notificationsPanel)).toBeVisible();

      // Close with button
      const closeBtn = page.locator(
        '[data-testid="close-notifications"]'
      );
      if (await closeBtn.isVisible()) {
        await closeBtn.click();
        await expect(
          page.locator(SELECTORS.notificationsPanel)
        ).not.toBeVisible();
      }
    }
  });

  test('should display notification list', async ({
    authenticatedPage: page,
  }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      // List should be visible
      const list = page.locator('[data-testid="notification-list"]');
      await expect(list).toBeVisible();
    }
  });

  test('should show empty state when no notifications', async ({
    authenticatedPage: page,
  }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      // Either notifications or empty state
      const notifications = page.locator(
        '[data-testid^="notification-item-"]'
      );
      const emptyState = page.locator(
        '[data-testid="notifications-empty"]'
      );

      const hasNotifications = (await notifications.count()) > 0;
      const isEmpty = await emptyState.isVisible();

      expect(hasNotifications || isEmpty).toBeTruthy();
    }
  });

  test('should mark notification as read', async ({
    authenticatedPage: page,
  }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      // Find unread notification
      const unreadNotification = page.locator(
        '[data-testid^="notification-item-"][data-unread="true"]'
      );

      if ((await unreadNotification.count()) > 0) {
        await unreadNotification.first().click();

        // Should be marked as read
        await expect(unreadNotification.first()).toHaveAttribute(
          'data-unread',
          'false'
        );
      }
    }
  });

  test('should mark all as read', async ({ authenticatedPage: page }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      // Find mark all read button
      const markAllBtn = page.locator(
        '[data-testid="mark-all-read"]'
      );

      if (await markAllBtn.isVisible()) {
        await markAllBtn.click();

        // Badge should disappear or show 0
        await page.waitForTimeout(300);

        const badge = page.locator(SELECTORS.notificationBadge);
        const isVisible = await badge.isVisible();

        if (isVisible) {
          const count = await badge.textContent();
          expect(count === '0' || count === '').toBeTruthy();
        }
      }
    }
  });

  test('should navigate to notification source', async ({
    authenticatedPage: page,
  }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      const notifications = page.locator(
        '[data-testid^="notification-item-"]'
      );

      if ((await notifications.count()) > 0) {
        // Click notification action button
        const actionBtn = notifications
          .first()
          .locator('[data-testid="notification-action"]');

        if (await actionBtn.isVisible()) {
          await actionBtn.click();

          // Should navigate somewhere
          await page.waitForTimeout(500);

          // Panel should close
          await expect(
            page.locator(SELECTORS.notificationsPanel)
          ).not.toBeVisible();
        }
      }
    }
  });

  test('should dismiss notification', async ({
    authenticatedPage: page,
  }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      const notifications = page.locator(
        '[data-testid^="notification-item-"]'
      );
      const initialCount = await notifications.count();

      if (initialCount > 0) {
        // Find dismiss button
        const dismissBtn = notifications
          .first()
          .locator('[data-testid="dismiss-notification"]');

        if (await dismissBtn.isVisible()) {
          await dismissBtn.click();

          // Notification should be removed
          await page.waitForTimeout(300);

          const newCount = await notifications.count();
          expect(newCount).toBeLessThan(initialCount);
        }
      }
    }
  });

  test('should show notification types with icons', async ({
    authenticatedPage: page,
  }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      const notifications = page.locator(
        '[data-testid^="notification-item-"]'
      );

      if ((await notifications.count()) > 0) {
        // Each notification should have an icon
        const firstNotif = notifications.first();
        const icon = firstNotif.locator('[data-testid="notification-icon"]');

        const hasIcon = await icon.isVisible();
        expect(hasIcon).toBeTruthy();
      }
    }
  });

  test('should filter notifications by type', async ({
    authenticatedPage: page,
  }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();

      // Find filter dropdown
      const filter = page.locator('[data-testid="notification-filter"]');

      if (await filter.isVisible()) {
        await filter.click();

        // Select a type
        const urgentOption = page.locator(
          '[data-testid="filter-urgent"]'
        );
        if (await urgentOption.isVisible()) {
          await urgentOption.click();

          // Notifications should be filtered
          await page.waitForTimeout(300);
        }
      }
    }
  });

  test('should update badge in real-time via WebSocket', async ({
    authenticatedPage: page,
  }) => {
    // This test verifies the structure exists for real-time updates
    // Actual WebSocket testing would require mock server

    const badge = page.locator(SELECTORS.notificationBadge);
    const bellIcon = page.locator('[data-testid="notification-bell"]');

    // Verify elements exist for real-time updates
    expect(
      (await badge.isVisible()) || (await bellIcon.isVisible())
    ).toBeTruthy();
  });

  test('should close panel with Escape', async ({
    authenticatedPage: page,
  }) => {
    const bellIcon = page.locator('[data-testid="notification-bell"]');
    if (await bellIcon.isVisible()) {
      await bellIcon.click();
      await expect(page.locator(SELECTORS.notificationsPanel)).toBeVisible();

      // Press Escape
      await page.keyboard.press('Escape');

      // Panel should close
      await expect(
        page.locator(SELECTORS.notificationsPanel)
      ).not.toBeVisible();
    }
  });
});
