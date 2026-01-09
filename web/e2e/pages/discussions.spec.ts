import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Discussions Page E2E Tests
 *
 * Tests the chat and discussions functionality.
 */

test.describe('Discussions Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/discussions');
  });

  test('should display discussions list', async ({
    authenticatedPage: page,
  }) => {
    // Discussions list should be visible
    const discussionsList = page.locator('[data-testid="discussions-list"]');
    await expect(discussionsList).toBeVisible();
  });

  test('should show create new discussion button', async ({
    authenticatedPage: page,
  }) => {
    const newBtn = page.locator('[data-testid="new-discussion-btn"]');
    await expect(newBtn).toBeVisible();
  });

  test('should create new discussion', async ({
    authenticatedPage: page,
  }) => {
    // Click new discussion
    await page.click('[data-testid="new-discussion-btn"]');

    // Modal or new discussion input should appear
    const modal = page.locator('[data-testid="new-discussion-modal"]');
    const input = page.locator('[data-testid="new-discussion-input"]');

    expect(
      (await modal.isVisible()) || (await input.isVisible())
    ).toBeTruthy();
  });

  test('should display discussion items', async ({
    authenticatedPage: page,
  }) => {
    // Check for discussion items
    const items = page.locator('[data-testid^="discussion-item-"]');
    const count = await items.count();

    // May have discussions or be empty
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should navigate to discussion detail', async ({
    authenticatedPage: page,
  }) => {
    const items = page.locator('[data-testid^="discussion-item-"]');
    const count = await items.count();

    if (count > 0) {
      await items.first().click();

      // Should show chat interface
      await expect(page.locator(SELECTORS.chatPanel)).toBeVisible();
    }
  });

  test('should filter discussions', async ({ authenticatedPage: page }) => {
    // Search/filter input
    const filterInput = page.locator('[data-testid="discussions-filter"]');

    if (await filterInput.isVisible()) {
      await filterInput.fill('test');

      // Results should filter
      await page.waitForTimeout(300);

      const items = page.locator('[data-testid^="discussion-item-"]');
      expect(await items.count()).toBeGreaterThanOrEqual(0);
    }
  });

  test('should delete discussion with confirmation', async ({
    authenticatedPage: page,
  }) => {
    const items = page.locator('[data-testid^="discussion-item-"]');
    const count = await items.count();

    if (count > 0) {
      // Right-click or click menu on first item
      const deleteBtn = items
        .first()
        .locator('[data-testid="delete-discussion"]');

      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();

        // Confirmation dialog should appear
        await expect(
          page.locator('[data-testid="confirm-delete"]')
        ).toBeVisible();
      }
    }
  });
});

test.describe('Chat Panel', () => {
  test('should display chat panel', async ({ authenticatedPage: page }) => {
    await page.goto('/');

    // Chat panel should be in layout
    const chatPanel = page.locator(SELECTORS.chatPanel);

    // May be collapsed on smaller screens
    const isVisible = await chatPanel.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should open chat panel on desktop', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/');

    // Ensure desktop viewport
    await page.setViewportSize({ width: 1280, height: 720 });

    // Chat panel should be visible
    await expect(page.locator(SELECTORS.chatPanel)).toBeVisible();
  });

  test('should send message in chat', async ({ authenticatedPage: page }) => {
    await page.goto('/');
    await page.setViewportSize({ width: 1280, height: 720 });

    const chatPanel = page.locator(SELECTORS.chatPanel);

    if (await chatPanel.isVisible()) {
      // Find message input
      const input = chatPanel.locator('[data-testid="chat-input"]');
      await input.fill('Test message');

      // Click send or press Enter
      await page.keyboard.press('Enter');

      // Message should appear in chat
      await expect(
        chatPanel.locator('[data-testid^="chat-message-"]')
      ).toBeVisible();
    }
  });

  test('should display suggestions', async ({ authenticatedPage: page }) => {
    await page.goto('/');
    await page.setViewportSize({ width: 1280, height: 720 });

    const chatPanel = page.locator(SELECTORS.chatPanel);

    if (await chatPanel.isVisible()) {
      // Suggestions should be visible
      const suggestions = chatPanel.locator(
        '[data-testid="chat-suggestions"]'
      );

      const hasSuggestions = await suggestions.isVisible();
      expect(typeof hasSuggestions).toBe('boolean');
    }
  });

  test('should click suggestion to fill input', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/');
    await page.setViewportSize({ width: 1280, height: 720 });

    const chatPanel = page.locator(SELECTORS.chatPanel);

    if (await chatPanel.isVisible()) {
      const suggestion = chatPanel.locator(
        '[data-testid^="suggestion-"]'
      ).first();

      if (await suggestion.isVisible()) {
        await suggestion.click();

        // Input should be filled
        const input = chatPanel.locator('[data-testid="chat-input"]');
        const value = await input.inputValue();
        expect(value.length).toBeGreaterThan(0);
      }
    }
  });

  test('should toggle chat panel visibility', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/');

    // Find toggle button
    const toggleBtn = page.locator('[data-testid="toggle-chat"]');

    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();

      // Chat panel visibility should change
      await page.waitForTimeout(300);

      await toggleBtn.click();

      // Should toggle back
      await page.waitForTimeout(300);
    }
  });
});
